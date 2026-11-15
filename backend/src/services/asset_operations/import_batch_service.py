"""Import batch orchestration for the V4-0 three-sheet workbook.

The service persists the parsed workbook, resolves references against the
database within the actor's scope, builds per-field diff rows, and drives the
atomic commit (reusing the formal contract commands with ``auto_commit=False``
so one outer transaction owns the whole batch) and the seven-day revert.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any, cast
from uuid import uuid4

from fastapi import status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exception_handler import BaseBusinessError
from ...crud.asset_contract import asset_contract_repository
from ...crud.asset_unit import AssetUnitRepository
from ...crud.attachment import attachment_crud
from ...crud.import_batch import ImportBatchRepository
from ...models.asset_contract import (
    ContractRentSchedule,
    TerminalContract,
    TerminalContractAssetUnit,
    UpstreamContract,
    UpstreamContractAssetUnit,
)
from ...models.asset_unit import AssetUnit
from ...models.attachment import Attachment
from ...models.import_batch import ImportBatch, ImportBatchChange
from ...models.party import Party
from ...models.project import Project
from ...schemas.asset_operations import (
    AssetUnitCreate,
    AssetUnitUpdate,
    ContractRentScheduleInput,
    TerminalContractCreate,
    TerminalContractMode,
    TerminalContractUpdate,
    UpstreamContractCreate,
    UpstreamContractUpdate,
)
from ...services.party_scope_resolver import EffectivePartyScope
from .asset_unit_command_service import AssetUnitCommandService, record_unit_audit
from .contract_command_service import AssetContractCommandService
from .import_workbook_parser import (
    TERMINAL_SHEET,
    UNIT_SHEET,
    ContractRow,
    ParsedWorkbook,
    UnitRow,
    WorkbookFormatError,
    parse_import_workbook,
)

_PREVIEW_TTL = timedelta(minutes=30)
_STAGING_PREFIX = "import-staging-"


class ImportBatchFormatError(BaseBusinessError):
    def __init__(self, *, message: str) -> None:
        super().__init__(
            message=message,
            code="IMPORT_FILE_INVALID",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


class ImportBatchNotFoundError(BaseBusinessError):
    def __init__(self, *, batch_id: str) -> None:
        super().__init__(
            message=f"导入批次不存在: {batch_id}",
            code="IMPORT_BATCH_NOT_FOUND",
            details={"batch_id": batch_id},
            status_code=status.HTTP_404_NOT_FOUND,
        )


class ImportHasErrorsError(BaseBusinessError):
    def __init__(self, *, error_count: int) -> None:
        super().__init__(
            message=f"批次存在 {error_count} 个错误，须修正后重新上传",
            code="IMPORT_HAS_ERRORS",
            details={"error_count": error_count},
            status_code=status.HTTP_409_CONFLICT,
        )


class ImportProposalChangedError(BaseBusinessError):
    def __init__(self) -> None:
        super().__init__(
            message="批次内容已变化，请重新预览",
            code="IMPORT_PROPOSAL_CHANGED",
            status_code=status.HTTP_409_CONFLICT,
        )


class ImportTokenInvalidError(BaseBusinessError):
    def __init__(self) -> None:
        super().__init__(
            message="预览已过期或 token 无效，请重新预览",
            code="IMPORT_PREVIEW_EXPIRED",
            status_code=status.HTTP_409_CONFLICT,
        )


class ImportBatchStateError(BaseBusinessError):
    def __init__(self, *, message: str) -> None:
        super().__init__(
            message=message,
            code="IMPORT_BATCH_STATE_INVALID",
            status_code=status.HTTP_409_CONFLICT,
        )


class ImportRevertWindowExpiredError(BaseBusinessError):
    def __init__(self, *, deadline: str) -> None:
        super().__init__(
            message=f"撤销窗口已过（截止 {deadline}）",
            code="IMPORT_REVERT_WINDOW_EXPIRED",
            details={"deadline": deadline},
            status_code=status.HTTP_409_CONFLICT,
        )


class ImportRevertDependencyConflictError(BaseBusinessError):
    def __init__(self, *, blockers: list[dict[str, str]]) -> None:
        super().__init__(
            message="批次对象存在后继依赖，拒绝撤销",
            code="IMPORT_REVERT_DEPENDENCY_CONFLICT",
            details={"blockers": blockers},
            status_code=status.HTTP_409_CONFLICT,
        )


@dataclass
class _CommitToken:
    token: str
    proposal_hash: str
    expires_at: datetime


def _now() -> datetime:
    return datetime.now(UTC)


def staging_owner_id(actor_id: str) -> str:
    return _STAGING_PREFIX + actor_id


class ImportBatchService:
    """Upload → validate → diff → atomic commit → windowed revert."""

    def __init__(
        self,
        *,
        contract_commands: AssetContractCommandService | None = None,
        unit_commands: AssetUnitCommandService | None = None,
        repository: ImportBatchRepository | None = None,
        unit_repository: AssetUnitRepository | None = None,
    ) -> None:
        self._contract_commands = contract_commands
        self._unit_commands = unit_commands
        self._repository = repository
        self._unit_repository = unit_repository
        self._tokens: dict[str, _CommitToken] = {}

    async def stage_scan_files(
        self,
        db: AsyncSession,
        *,
        actor_id: str,
        uploads: list[Any],
    ) -> list[dict[str, object]]:
        """Stage contract scan files for import under the actor's own pool."""
        from pathlib import Path

        from ..file_upload import StagedFileService, UploadPurpose

        lifecycle = StagedFileService(Path("uploads"))
        owner_id = staging_owner_id(actor_id)
        staged_files: list[dict[str, object]] = []
        for upload in uploads:
            staged = await lifecycle.stage_upload(
                upload, UploadPurpose.CONTRACT_EXTRACTION
            )
            try:
                stored = lifecycle.promote(
                    staged, owner_type="contract", owner_id=owner_id
                )
                attachment_id = str(uuid4())
                await attachment_crud.create(
                    db,
                    data={
                        "id": attachment_id,
                        "owner_type": "contract",
                        "owner_id": owner_id,
                        "file_name": staged.original_filename,
                        "file_type": staged.canonical_extension.lstrip("."),
                        "file_size": staged.size_bytes,
                        "file_hash": staged.sha256,
                        "storage_key": stored.storage_key,
                        "created_by": actor_id,
                    },
                    commit=False,
                )
                staged_files.append(
                    {
                        "id": attachment_id,
                        "file_name": staged.original_filename,
                        "file_size": staged.size_bytes,
                    }
                )
            except Exception:
                lifecycle.discard_staged(staged)
                raise
        await db.commit()
        return staged_files

    async def get_batch(
        self, db: AsyncSession, *, actor_id: str, batch_id: str
    ) -> ImportBatch:
        return await self._own_batch(db, actor_id=actor_id, batch_id=batch_id)

    # ------------------------------------------------------------------ upload

    async def upload_batch(
        self,
        db: AsyncSession,
        *,
        actor_id: str,
        scope: EffectivePartyScope,
        mode: str,
        filename: str,
        content: bytes,
    ) -> ImportBatch:
        try:
            parsed = parse_import_workbook(content, mode=mode)
        except WorkbookFormatError as exc:
            raise ImportBatchFormatError(message=str(exc)) from exc

        batch_id = str(uuid4())
        file_attachment = await attachment_crud.create(
            db,
            data={
                "id": str(uuid4()),
                "owner_type": "import_batch",
                "owner_id": batch_id,
                "file_name": filename or "import.xlsx",
                "file_type": "xlsx",
                "file_size": len(content),
                "storage_key": f"imports/{batch_id}/{uuid4()}.xlsx",
                "created_by": actor_id,
            },
            commit=False,
        )
        batch = ImportBatch(  # type: ignore[call-arg]
            id=batch_id,
            mode=mode,
            status="validating",
            file_document_id=file_attachment.id,
            template_version=parsed.template_version,
            created_by=actor_id,
        )
        db.add(batch)
        await db.flush()

        await self._persist_validation(
            db, batch, parsed, actor_id=actor_id, scope=scope
        )
        await db.commit()
        await db.refresh(batch)
        return batch

    async def _persist_validation(
        self,
        db: AsyncSession,
        batch: ImportBatch,
        parsed: ParsedWorkbook,
        *,
        actor_id: str,
        scope: EffectivePartyScope,
    ) -> None:
        changes: list[ImportBatchChange] = []
        for issue in parsed.issues:
            changes.append(
                ImportBatchChange(  # type: ignore[call-arg]
                    batch_id=batch.id,
                    sheet_name=issue.sheet,
                    row_number=issue.row_number,
                    target_type="asset_unit",
                    target_key=issue.sheet,
                    field_name=issue.code,
                    severity="error" if issue.code.endswith("_ERROR") else "warning",
                    effect_summary=issue.message,
                )
            )

        resolution = await self._resolve_references(
            db, parsed, batch_id=batch.id, scope=scope
        )
        changes.extend(resolution.changes)

        if batch.mode == "create":
            changes.extend(
                _create_mode_changes(parsed, resolution),
            )
        else:
            changes.extend(
                await self._update_mode_changes(
                    db, parsed, resolution, batch_id=batch.id, scope=scope
                ),
            )

        for change in changes:
            change.batch_id = batch.id
            db.add(change)
        await db.flush()

        batch.error_count = sum(1 for c in changes if c.severity == "error")
        batch.warning_count = sum(1 for c in changes if c.severity == "warning")
        batch.valid_count = max(
            0, parsed.row_count - sum(1 for c in changes if c.severity == "error")
        )
        batch.row_count = parsed.row_count
        batch.status = "invalid" if batch.error_count > 0 else "ready"
        if batch.status == "ready":
            batch.proposal_hash = _proposal_hash([c for c in changes if c.selected])
        await db.flush()

    # ------------------------------------------------------------- resolution

    async def _resolve_references(
        self,
        db: AsyncSession,
        parsed: ParsedWorkbook,
        *,
        batch_id: str,
        scope: EffectivePartyScope,
    ) -> _Resolution:
        changes: list[ImportBatchChange] = []
        party_names = {
            name
            for unit in parsed.units
            if unit.owner_party_name
            for name in (unit.owner_party_name,)
        }
        for contract in (*parsed.upstreams, *parsed.terminals):
            for name in (
                contract.owner_party_name,
                contract.operator_party_name,
                contract.tenant_party_name,
                contract.lessor_party_name,
            ):
                if name:
                    party_names.add(name)

        parties = (
            (
                await db.execute(
                    select(Party).where(
                        Party.name.in_(party_names),
                        Party.review_status == "approved",
                        Party.status == "active",
                        Party.deleted_at.is_(None),
                    )
                )
            )
            .scalars()
            .all()
            if party_names
            else ()
        )
        by_name: dict[str, list[Party]] = {}
        for party in parties:
            by_name.setdefault(party.name, []).append(party)
        party_ids: dict[str, str] = {}
        for name in sorted(party_names):
            matches = by_name.get(name, [])
            if len(matches) == 1:
                party_ids[name] = matches[0].id
            else:
                code = (
                    "PARTY_NAME_AMBIGUOUS_ERROR"
                    if len(matches) > 1
                    else "PARTY_NAME_NOT_FOUND_ERROR"
                )
                message = (
                    f"主体全称匹配到 {len(matches)} 个已审核启用主体，不允许歧义"
                    if len(matches) > 1
                    else "主体全称未匹配到已审核启用主体（不自动创建）"
                )
                changes.append(
                    _error_change(
                        batch_id=batch_id,
                        batch_sheet=UNIT_SHEET,
                        row_number=0,
                        target_key=name,
                        code=code,
                        message=message,
                    )
                )

        project_codes = {
            unit.project_code for unit in parsed.units if unit.project_code
        }
        projects: dict[str, Project] = {}
        for code_value in sorted(project_codes):
            project = (
                await db.execute(
                    select(Project).where(Project.project_code == code_value)
                )
            ).scalar_one_or_none()
            if project is None:
                changes.append(
                    _error_change(
                        batch_id=batch_id,
                        batch_sheet=UNIT_SHEET,
                        row_number=0,
                        target_key=code_value,
                        code="PROJECT_NOT_FOUND_ERROR",
                        message=f"项目编号不存在: {code_value}",
                    )
                )
            else:
                projects[code_value] = project

        unit_codes = {
            code
            for contract in (*parsed.upstreams, *parsed.terminals)
            for code in contract.unit_codes
        }
        db_units: dict[str, AssetUnit] = {}
        if unit_codes:
            rows = (
                (
                    await db.execute(
                        select(AssetUnit).where(AssetUnit.unit_code.in_(unit_codes))
                    )
                )
                .scalars()
                .all()
            )
            for unit in rows:
                db_units[unit.unit_code] = unit

        contract_numbers = {
            contract.contract_number
            for contract in parsed.terminals
            if contract.upstream_contract_number
        }
        db_contracts: dict[str, tuple[str, str]] = {}
        if contract_numbers:
            in_scope = await asset_contract_repository.contract_numbers_in_scope(
                db, scope=scope
            )
            for kind, cid, number, _name in in_scope:
                if number in contract_numbers:
                    db_contracts[number] = (kind, cid)

        return _Resolution(
            party_ids=party_ids,
            projects=projects,
            db_units=db_units,
            db_contracts=db_contracts,
            changes=changes,
        )

    # ------------------------------------------------------------ diff builders

    async def _update_mode_changes(
        self,
        db: AsyncSession,
        parsed: ParsedWorkbook,
        resolution: _Resolution,
        *,
        batch_id: str,
        scope: EffectivePartyScope,
    ) -> list[ImportBatchChange]:
        changes: list[ImportBatchChange] = []
        scope_units = {unit.id: unit for unit in await self._scoped_units(db, scope)}
        unit_by_code = {unit.unit_code: unit for unit in scope_units.values()}
        contracts_in_scope = {
            number: (kind, cid)
            for kind, cid, number, _n in (
                await asset_contract_repository.contract_numbers_in_scope(
                    db, scope=scope
                )
            )
        }

        for unit in parsed.units:
            existing = unit_by_code.get(unit.unit_code)
            if existing is None:
                changes.append(
                    _error_change(
                        batch_id=batch_id,
                        batch_sheet=UNIT_SHEET,
                        row_number=unit.source_row,
                        target_key=unit.unit_code,
                        code="UNIT_NOT_FOUND_ERROR",
                        message=f"更新模式拒绝未知单元编号: {unit.unit_code}",
                    )
                )
                continue
            changes.extend(
                _unit_diff(unit, existing),
            )

        for contract in (*parsed.upstreams, *parsed.terminals):
            sheet = "承租合同" if contract in parsed.upstreams else TERMINAL_SHEET
            found = contracts_in_scope.get(contract.contract_number)
            if found is None or found[0] != (
                "upstream_contract"
                if contract in parsed.upstreams
                else "terminal_contract"
            ):
                changes.append(
                    _error_change(
                        batch_id=batch_id,
                        batch_sheet=sheet,
                        row_number=contract.source_rows[0],
                        target_key=contract.contract_number,
                        code="CONTRACT_NOT_FOUND_ERROR",
                        message=f"更新模式拒绝未知合同编号: {contract.contract_number}",
                    )
                )
                continue
            _kind, cid = found
            existing_contract = await self._contract_by_id(db, _kind, cid)
            if existing_contract is not None:
                changes.extend(_contract_diff(contract, existing_contract, sheet))
        return changes

    async def _scoped_units(
        self, db: AsyncSession, scope: EffectivePartyScope
    ) -> list[AssetUnit]:
        from ...crud.asset_unit import asset_unit_repository

        units, _total = await asset_unit_repository.list(
            db, scope=scope, limit=100000, offset=0
        )
        return list(units)

    async def _contract_by_id(
        self, db: AsyncSession, kind: str, contract_id: str
    ) -> UpstreamContract | TerminalContract | None:
        # 动态 Base 下 select(变量模型) 会退化成 Base，按具体模型分支查询
        if kind == "upstream_contract":
            return (
                await db.execute(
                    select(UpstreamContract).where(UpstreamContract.id == contract_id)
                )
            ).scalar_one_or_none()
        return (
            await db.execute(
                select(TerminalContract).where(TerminalContract.id == contract_id)
            )
        ).scalar_one_or_none()

    # --------------------------------------------------------------- previews

    async def commit_preview(
        self, db: AsyncSession, *, actor_id: str, batch_id: str
    ) -> dict[str, Any]:
        batch = await self._own_batch(db, actor_id=actor_id, batch_id=batch_id)
        if batch.error_count > 0:
            raise ImportHasErrorsError(error_count=batch.error_count)
        if batch.status != "ready":
            raise ImportBatchStateError(message="批次不在可提交状态")
        current_hash = await self._recompute_hash(db, batch)
        if current_hash != batch.proposal_hash:
            batch.proposal_hash = current_hash
            await db.commit()
            raise ImportProposalChangedError()
        token = str(uuid4())
        self._tokens[batch_id] = _CommitToken(
            token=token,
            proposal_hash=current_hash,
            expires_at=_now() + _PREVIEW_TTL,
        )
        changes = await self._changes(db, batch_id)
        selected = [c for c in changes if c.selected]
        return {
            "batch_id": batch_id,
            "change_count": len(selected),
            "warning_count": batch.warning_count,
            "proposal_hash": current_hash,
            "commit_token": token,
            "expires_at": self._tokens[batch_id].expires_at.isoformat(),
        }

    async def update_selection(
        self,
        db: AsyncSession,
        *,
        actor_id: str,
        batch_id: str,
        selections: dict[str, bool],
    ) -> ImportBatch:
        batch = await self._own_batch(db, actor_id=actor_id, batch_id=batch_id)
        if batch.status != "ready":
            raise ImportBatchStateError(message="批次不在可提交状态")
        if batch.mode != "update":
            raise ImportBatchStateError(message="新增模式不支持逐项选择")
        changes = {
            c.id: c for c in await self._changes(db, batch_id) if c.severity == "change"
        }
        for change_id, selected in selections.items():
            change = changes.get(change_id)
            if change is None:
                raise ImportBatchNotFoundError(batch_id=change_id)
            change.selected = selected
        batch.version += 1
        batch.proposal_hash = await self._recompute_hash(db, batch)
        self._tokens.pop(batch_id, None)
        await db.commit()
        await db.refresh(batch)
        return batch

    async def _recompute_hash(self, db: AsyncSession, batch: ImportBatch) -> str:
        changes = [c for c in await self._changes(db, batch.id) if c.selected]
        return _proposal_hash(changes)

    async def _changes(
        self, db: AsyncSession, batch_id: str
    ) -> list[ImportBatchChange]:
        return list(
            (
                await db.execute(
                    select(ImportBatchChange)
                    .where(ImportBatchChange.batch_id == batch_id)
                    .order_by(
                        ImportBatchChange.row_number, ImportBatchChange.field_name
                    )
                )
            )
            .scalars()
            .all()
        )

    async def _own_batch(
        self, db: AsyncSession, *, actor_id: str, batch_id: str
    ) -> ImportBatch:
        batch = (
            await db.execute(select(ImportBatch).where(ImportBatch.id == batch_id))
        ).scalar_one_or_none()
        if batch is None or batch.created_by != actor_id:
            raise ImportBatchNotFoundError(batch_id=batch_id)
        return batch

    # ---------------------------------------------------------------------- helpers

    async def build_update_base(
        self, db: AsyncSession, *, scope: EffectivePartyScope
    ) -> bytes:
        """Export current scoped facts as an update-mode base workbook."""
        from ...crud.asset_unit import asset_unit_repository
        from .import_template_service import build_update_workbook

        units, _total = await asset_unit_repository.list(
            db, scope=scope, limit=100000, offset=0
        )
        unit_rows: list[dict[str, object]] = []
        for unit in units:
            unit_rows.append(
                {
                    "unit_code": unit.unit_code,
                    "name": unit.name,
                    "owner_party_name": await _party_name(db, unit.owner_party_id),
                    "project_code": await _project_code(db, unit.project_id),
                    "address": unit.address,
                    "usage_type": unit.usage_type,
                    "acquisition_mode": unit.acquisition_mode,
                    "managed_from": unit.managed_from.isoformat()
                    if unit.managed_from
                    else "",
                    "managed_to": unit.managed_to.isoformat()
                    if unit.managed_to
                    else "",
                    "land_area": str(unit.land_area),
                    "building_area": str(unit.building_area),
                    "rentable_area": str(unit.rentable_area),
                }
            )
        in_scope = await asset_contract_repository.contract_numbers_in_scope(
            db, scope=scope
        )
        upstream_rows: list[dict[str, object]] = []
        terminal_rows: list[dict[str, object]] = []
        for kind, contract_id, number, _n in in_scope:
            if kind == "upstream_contract":
                upstream_contract = (
                    await db.execute(
                        select(UpstreamContract).where(
                            UpstreamContract.id == contract_id
                        )
                    )
                ).scalar_one_or_none()
                if upstream_contract is None:
                    continue
                coverages = (
                    (
                        await db.execute(
                            select(UpstreamContractAssetUnit.asset_unit_id).where(
                                UpstreamContractAssetUnit.upstream_contract_id
                                == contract_id
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
                upstream_rows.append(
                    {
                        "contract_number": number,
                        "contract_type": upstream_contract.contract_type,
                        "name": upstream_contract.name,
                        "owner_party_name": await _party_name(
                            db, upstream_contract.owner_party_id
                        ),
                        "operator_party_name": await _party_name(
                            db, upstream_contract.operator_party_id
                        ),
                        "unit_codes": await _unit_codes_for(db, coverages),
                        "start_date": upstream_contract.start_date.isoformat(),
                        "end_date": upstream_contract.end_date.isoformat(),
                        "deposit_amount": str(upstream_contract.deposit_amount),
                        "management_fee_rate": str(
                            upstream_contract.management_fee_rate
                        )
                        if upstream_contract.management_fee_rate is not None
                        else "",
                    }
                )
            elif kind == "terminal_contract":
                terminal_contract = (
                    await db.execute(
                        select(TerminalContract).where(
                            TerminalContract.id == contract_id
                        )
                    )
                ).scalar_one_or_none()
                if terminal_contract is None:
                    continue
                coverages = (
                    (
                        await db.execute(
                            select(TerminalContractAssetUnit.asset_unit_id).where(
                                TerminalContractAssetUnit.terminal_contract_id
                                == contract_id
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
                upstream_number = ""
                if terminal_contract.upstream_contract_id is not None:
                    upstream_number = (
                        await db.execute(
                            select(UpstreamContract.contract_number).where(
                                UpstreamContract.id
                                == terminal_contract.upstream_contract_id
                            )
                        )
                    ).scalar_one_or_none() or ""
                terminal_rows.append(
                    {
                        "contract_number": number,
                        "contract_mode": terminal_contract.contract_mode,
                        "tenant_party_name": await _party_name(
                            db, terminal_contract.tenant_party_id
                        ),
                        "lessor_party_name": await _party_name(
                            db, terminal_contract.lessor_party_id
                        ),
                        "unit_codes": await _unit_codes_for(db, coverages),
                        "upstream_contract_number": upstream_number,
                        "start_date": terminal_contract.start_date.isoformat(),
                        "end_date": terminal_contract.end_date.isoformat(),
                        "deposit_amount": str(terminal_contract.deposit_amount),
                    }
                )
        return build_update_workbook(
            units=unit_rows, upstreams=upstream_rows, terminals=terminal_rows
        )

    # ----------------------------------------------------------------- commit

    async def commit(
        self,
        db: AsyncSession,
        *,
        actor_id: str,
        scope: EffectivePartyScope,
        batch_id: str,
        token: str,
        expected_version: int,
        proposal_hash: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        batch = await self._own_batch(db, actor_id=actor_id, batch_id=batch_id)
        if batch.status == "committed" and batch.idempotency_key == idempotency_key:
            return {
                "batch_id": batch.id,
                "status": batch.status,
                "idempotent": True,
                "committed_at": batch.committed_at.isoformat()
                if batch.committed_at
                else None,
            }
        if batch.error_count > 0:
            raise ImportHasErrorsError(error_count=batch.error_count)
        if batch.status != "ready":
            raise ImportBatchStateError(message="批次不在可提交状态")
        if batch.version != expected_version:
            raise _version_conflict(
                batch_id=batch_id, expected=expected_version, actual=batch.version
            )
        pending = self._tokens.get(batch_id)
        if (
            pending is None
            or pending.token != token
            or pending.proposal_hash != proposal_hash
            or pending.expires_at < _now()
        ):
            raise ImportTokenInvalidError()
        current_hash = await self._recompute_hash(db, batch)
        if current_hash != proposal_hash:
            raise ImportProposalChangedError()
        if scope.scope_mode != "unrestricted" and scope.error_code is not None:
            raise ImportBatchStateError(message="数据范围无效")

        changes = [c for c in await self._changes(db, batch_id) if c.selected]
        staging_owner = staging_owner_id(actor_id)
        staged_files = {
            attachment.file_name: attachment
            for attachment in (
                await db.execute(
                    select(Attachment).where(
                        Attachment.owner_type == "contract",
                        Attachment.owner_id == staging_owner,
                    )
                )
            )
            .scalars()
            .all()
        }

        try:
            await self._execute_commit(
                db,
                batch=batch,
                changes=changes,
                actor_id=actor_id,
                scope=scope,
                staging_owner=staging_owner,
                staged_files=staged_files,
            )
        except Exception:
            await db.rollback()
            raise

        batch.status = "committed"
        batch.committed_at = _now()
        batch.committed_by = actor_id
        batch.idempotency_key = idempotency_key
        batch.version += 1
        self._tokens.pop(batch_id, None)
        await db.commit()
        return {
            "batch_id": batch.id,
            "status": batch.status,
            "idempotent": False,
            "committed_at": batch.committed_at.isoformat(),
        }

    async def _execute_commit(
        self,
        db: AsyncSession,
        *,
        batch: ImportBatch,
        changes: list[ImportBatchChange],
        actor_id: str,
        scope: EffectivePartyScope,
        staging_owner: str,
        staged_files: dict[str, Attachment],
    ) -> None:
        created_unit_ids: dict[str, str] = {}
        created_upstream_ids: dict[str, str] = {}
        batch_id = batch.id
        correlation = str(uuid4())
        if batch.mode == "create":
            for change in sorted(
                (c for c in changes if c.target_type == "asset_unit"),
                key=lambda c: c.target_key,
            ):
                created_unit_ids[change.target_key] = await self._create_unit(
                    db,
                    change=change,
                    actor_id=actor_id,
                    scope=scope,
                    correlation=correlation,
                )
            for change in sorted(
                (c for c in changes if c.target_type == "upstream_contract"),
                key=lambda c: c.target_key,
            ):
                created_upstream_ids[change.target_key] = await self._create_contract(
                    db,
                    change=change,
                    actor_id=actor_id,
                    scope=scope,
                    staged_files=staged_files,
                    staging_owner=staging_owner,
                    unit_ids=created_unit_ids,
                    upstream_ids={},
                    correlation=correlation,
                    batch_id=batch_id,
                )
            for change in sorted(
                (c for c in changes if c.target_type == "terminal_contract"),
                key=lambda c: c.target_key,
            ):
                await self._create_contract(
                    db,
                    change=change,
                    actor_id=actor_id,
                    scope=scope,
                    staged_files=staged_files,
                    staging_owner=staging_owner,
                    unit_ids=created_unit_ids,
                    upstream_ids=created_upstream_ids,
                    correlation=correlation,
                    batch_id=batch_id,
                )
        else:
            await self._apply_updates(
                db,
                changes=changes,
                actor_id=actor_id,
                scope=scope,
                correlation=correlation,
            )

    async def _create_unit(
        self,
        db: AsyncSession,
        *,
        change: ImportBatchChange,
        actor_id: str,
        scope: EffectivePartyScope,
        correlation: str,
    ) -> str:
        from ...crud.asset_unit import asset_unit_repository

        payload: dict[str, Any] = dict(change.new_value or {})
        party_name = payload.get("owner_party_name")
        project_code = payload.get("project_code")

        party = (
            await db.execute(
                select(Party).where(
                    Party.name == party_name,
                    Party.review_status == "approved",
                    Party.status == "active",
                    Party.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        project = (
            await db.execute(
                select(Project).where(Project.project_code == project_code)
            )
        ).scalar_one_or_none()
        if party is None or project is None:
            raise ImportBatchStateError(
                message=f"单元 {change.target_key} 的主体或项目解析失败，请重新上传"
            )
        unit_id = str(uuid4())
        create = AssetUnitCreate(
            unit_code=change.target_key,
            name=payload.get("name") or change.target_key,
            project_id=project.id,
            owner_party_id=party.id,
            address=payload.get("address") or "",
            usage_type=payload.get("usage_type") or "commercial",
            acquisition_mode=payload.get("acquisition_mode") or "owned",
            land_area=Decimal(str(payload.get("land_area") or "0")),
            building_area=Decimal(str(payload.get("building_area") or "0")),
            rentable_area=Decimal(str(payload.get("rentable_area") or "0")),
            managed_from=_parse_iso_date(payload.get("managed_from")),
            managed_to=_parse_iso_date(payload["managed_to"])
            if payload.get("managed_to")
            else None,
        )
        unit = AssetUnit(  # type: ignore[call-arg]
            id=unit_id,
            unit_code=create.unit_code,
            name=create.name,
            project_id=create.project_id,
            owner_party_id=create.owner_party_id,
            address=create.address,
            usage_type=create.usage_type,
            acquisition_mode=create.acquisition_mode,
            land_area=create.land_area,
            building_area=create.building_area,
            rentable_area=create.rentable_area,
            managed_from=create.managed_from,
            managed_to=create.managed_to,
        )
        await asset_unit_repository.add(db, unit=unit)
        await record_unit_audit(
            db,
            unit=unit,
            action="create",
            actor_id=actor_id,
            before={},
            after={"unit_code": unit.unit_code, "correlation_id": correlation},
        )
        return unit_id

    async def _create_contract(
        self,
        db: AsyncSession,
        *,
        change: ImportBatchChange,
        actor_id: str,
        scope: EffectivePartyScope,
        staged_files: dict[str, Attachment],
        staging_owner: str,
        unit_ids: dict[str, str],
        upstream_ids: dict[str, str],
        correlation: str,
        batch_id: str,
    ) -> str:
        payload: dict[str, Any] = dict(change.new_value or {})
        scan_name = payload.get("scan_file_name")
        scan = staged_files.get(scan_name) if scan_name else None
        if scan is None:
            raise ImportBatchStateError(
                message=f"合同 {change.target_key} 扫描件未在上传暂存中找到: {scan_name}"
            )
        resolved_unit_ids = []
        for code in payload.get("unit_codes", []):
            unit_id = unit_ids.get(code)
            if unit_id is None:
                found = (
                    await db.execute(
                        select(AssetUnit.id).where(AssetUnit.unit_code == code)
                    )
                ).scalar_one_or_none()
                if found is None:
                    raise ImportBatchStateError(
                        message=f"合同 {change.target_key} 引用未知单元: {code}"
                    )
                unit_id = found
            resolved_unit_ids.append(unit_id)
        stages = [
            ContractRentScheduleInput(
                stage_start=_parse_iso_date(s["stage_start"]),
                stage_end=_parse_iso_date(s["stage_end"]),
                base_monthly_rent=Decimal(s["base_monthly_rent"]),
                increase_rate=Decimal(s["increase_rate"]),
                free_rent_months=Decimal(s["free_rent_months"]),
                discount_amount=Decimal(s["discount_amount"]),
                actual_monthly_rent=Decimal(s["actual_monthly_rent"]),
                payment_cycle=s["payment_cycle"],
                due_day=int(s["due_day"]),
            )
            for s in payload.get("stages", [])
        ]
        commands = self._require_contract_commands()
        if change.target_type == "upstream_contract":
            contract_type = str(payload.get("contract_type") or "lease")
            upstream_request = UpstreamContractCreate(
                contract_number=change.target_key,
                contract_type=contract_type,  # type: ignore[arg-type]
                name=payload.get("name") or change.target_key,
                owner_party_id=await _resolve_party_id(db, payload, "owner_party_id"),
                operator_party_id=await _resolve_party_id(
                    db, payload, "operator_party_id"
                ),
                start_date=_parse_iso_date(payload.get("start_date")),
                end_date=_parse_iso_date(payload.get("end_date")),
                payment_cycle=payload.get("payment_cycle"),
                payment_day=int(payload["payment_day"])
                if payload.get("payment_day")
                else None,
                deposit_amount=Decimal(str(payload.get("deposit_amount") or "0")),
                management_fee_rate=Decimal(str(payload["management_fee_rate"]))
                if payload.get("management_fee_rate")
                else None,
                rent_schedules=stages,
                scan_document_id=scan.id,
                asset_unit_ids=resolved_unit_ids,
                oa_reference=None,
                renewed_from_id=None,
            )
            upstream_response = await commands.create_upstream(
                db,
                request=upstream_request,
                actor_id=actor_id,
                scope=scope,
                idempotency_key=f"{batch_id}:up:{change.target_key}",
                attachment_owner_id=staging_owner,
                auto_commit=False,
            )
            return upstream_response.id
        upstream_number = payload.get("upstream_contract_number")
        upstream_id = upstream_ids.get(upstream_number) if upstream_number else None
        if upstream_id is None and upstream_number:
            in_scope = await asset_contract_repository.contract_numbers_in_scope(
                db, scope=scope
            )
            for kind, cid, number, _n in in_scope:
                if number == upstream_number and kind == "upstream_contract":
                    upstream_id = cid
                    break
        mode = payload.get("contract_mode") or "sublease"
        terminal_request = TerminalContractCreate(
            contract_number=change.target_key,
            contract_mode=cast(
                TerminalContractMode,
                mode,
            ),
            tenant_party_id=await _resolve_party_id(db, payload, "tenant_party_id"),
            lessor_party_id=await _resolve_party_id(db, payload, "lessor_party_id"),
            upstream_contract_id=upstream_id,
            start_date=_parse_iso_date(payload.get("start_date")),
            end_date=_parse_iso_date(payload.get("end_date")),
            deposit_amount=Decimal(str(payload.get("deposit_amount") or "0")),
            rent_collector="operator" if mode == "sublease" else "owner",
            rent_schedules=stages,
            scan_document_id=scan.id,
            asset_unit_ids=resolved_unit_ids,
            deposit_months=None,
            renewed_from_id=None,
        )
        terminal_response = await commands.create_terminal(
            db,
            request=terminal_request,
            actor_id=actor_id,
            scope=scope,
            idempotency_key=f"{batch_id}:tm:{change.target_key}",
            attachment_owner_id=staging_owner,
            auto_commit=False,
        )
        return terminal_response.id

    async def _apply_updates(
        self,
        db: AsyncSession,
        *,
        changes: list[ImportBatchChange],
        actor_id: str,
        scope: EffectivePartyScope,
        correlation: str,
    ) -> None:
        unit_commands = self._require_unit_commands()
        contract_commands = self._require_contract_commands()
        by_target: dict[tuple[str, str], dict[str, ImportBatchChange]] = {}
        for change in changes:
            if change.severity != "change":
                continue
            by_target.setdefault((change.target_type, change.target_key), {})[
                change.field_name
            ] = change

        for (target_type, target_key), fields in sorted(by_target.items()):
            if target_type == "asset_unit":
                unit = (
                    await db.execute(
                        select(AssetUnit).where(AssetUnit.unit_code == target_key)
                    )
                ).scalar_one_or_none()
                if unit is None:
                    raise ImportBatchStateError(message=f"单元不存在: {target_key}")
                request = AssetUnitUpdate(
                    expected_version=unit.version,
                    **{
                        field: _coerce_update_value(field, change.new_value)
                        for field, change in fields.items()
                    },
                )
                await unit_commands.update_asset_unit(
                    db,
                    unit_id=unit.id,
                    request=request,
                    actor_id=actor_id,
                    scope=scope,
                    auto_commit=False,
                )
            else:
                model = (
                    UpstreamContract
                    if target_type == "upstream_contract"
                    else TerminalContract
                )
                contract = cast(
                    "UpstreamContract | TerminalContract | None",
                    (
                        await db.execute(
                            select(model).where(model.contract_number == target_key)
                        )
                    ).scalar_one_or_none(),
                )
                if contract is None:
                    raise ImportBatchStateError(message=f"合同不存在: {target_key}")
                values = {
                    field: _coerce_update_value(field, change.new_value)
                    for field, change in fields.items()
                }
                if "upstream_contract_number" in values:
                    number = values.pop("upstream_contract_number")
                    resolved_upstream: str | None = None
                    if number:
                        for (
                            kind,
                            cid,
                            num,
                            _n,
                        ) in await asset_contract_repository.contract_numbers_in_scope(
                            db, scope=scope
                        ):
                            if num == number and kind == "upstream_contract":
                                resolved_upstream = cid
                                break
                        if resolved_upstream is None:
                            raise ImportBatchStateError(
                                message=f"终端合同上游编号解析失败: {number}"
                            )
                    values["upstream_contract_id"] = resolved_upstream
                if target_type == "upstream_contract":
                    upstream_request = UpstreamContractUpdate(
                        expected_version=contract.version, **values
                    )
                    await contract_commands.update_upstream(
                        db,
                        contract_id=contract.id,
                        request=upstream_request,
                        actor_id=actor_id,
                        scope=scope,
                        auto_commit=False,
                    )
                else:
                    terminal_request = TerminalContractUpdate(
                        expected_version=contract.version, **values
                    )
                    await contract_commands.update_terminal(
                        db,
                        contract_id=contract.id,
                        request=terminal_request,
                        actor_id=actor_id,
                        scope=scope,
                        auto_commit=False,
                    )

    def _require_contract_commands(self) -> AssetContractCommandService:
        if self._contract_commands is None:
            from .contract_command_service import asset_contract_command_service

            self._contract_commands = asset_contract_command_service
        return self._contract_commands

    def _require_unit_commands(self) -> AssetUnitCommandService:
        if self._unit_commands is None:
            from .asset_unit_command_service import asset_unit_command_service

            self._unit_commands = asset_unit_command_service
        return self._unit_commands

    # ----------------------------------------------------------------- revert

    async def revert_preview(
        self, db: AsyncSession, *, actor_id: str, batch_id: str
    ) -> dict[str, Any]:
        batch = await self._own_batch(db, actor_id=actor_id, batch_id=batch_id)
        if batch.status == "reverted":
            raise ImportBatchStateError(message="批次已撤销")
        if batch.status != "committed":
            raise ImportBatchStateError(message="仅已提交批次可撤销")
        deadline = _revert_deadline(batch.committed_at)
        if _now() >= deadline:
            raise ImportRevertWindowExpiredError(deadline=deadline.isoformat())
        blockers = await self._revert_blockers(db, batch)
        token = str(uuid4())
        self._tokens[f"revert:{batch_id}"] = _CommitToken(
            token=token,
            proposal_hash=batch.proposal_hash or "",
            expires_at=_now() + _PREVIEW_TTL,
        )
        return {
            "batch_id": batch_id,
            "deadline": deadline.isoformat(),
            "blockers": blockers,
            "revert_token": token,
        }

    async def revert(
        self,
        db: AsyncSession,
        *,
        actor_id: str,
        scope: EffectivePartyScope,
        batch_id: str,
        token: str,
        reason: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        batch = await self._own_batch(db, actor_id=actor_id, batch_id=batch_id)
        if batch.status == "reverted" and batch.idempotency_key == idempotency_key:
            return {"batch_id": batch_id, "status": "reverted", "idempotent": True}
        if batch.status != "committed":
            raise ImportBatchStateError(message="仅已提交批次可撤销")
        if not reason.strip():
            raise ImportBatchStateError(message="撤销原因必填")
        pending = self._tokens.get(f"revert:{batch_id}")
        if pending is None or pending.token != token or pending.expires_at < _now():
            raise ImportTokenInvalidError()
        deadline = _revert_deadline(batch.committed_at)
        if _now() >= deadline:
            raise ImportRevertWindowExpiredError(deadline=deadline.isoformat())
        blockers = await self._revert_blockers(db, batch)
        if blockers:
            raise ImportRevertDependencyConflictError(blockers=blockers)

        changes = await self._changes(db, batch_id)
        created_targets = [
            c for c in changes if batch.mode == "create" and c.field_name == "*"
        ]
        terminal_rows = [
            c for c in created_targets if c.target_type == "terminal_contract"
        ]
        upstream_rows = [
            c for c in created_targets if c.target_type == "upstream_contract"
        ]
        unit_rows = [c for c in created_targets if c.target_type == "asset_unit"]

        for change in sorted(terminal_rows, key=lambda c: c.target_key):
            terminal_contract = (
                await db.execute(
                    select(TerminalContract).where(
                        TerminalContract.contract_number == change.target_key
                    )
                )
            ).scalar_one_or_none()
            if terminal_contract is None:
                continue
            await db.execute(
                delete(ContractRentSchedule).where(
                    ContractRentSchedule.contract_kind == "terminal",
                    ContractRentSchedule.contract_id == terminal_contract.id,
                )
            )
            await _delete_derived_rows(
                db, kind="terminal", contract_id=terminal_contract.id
            )
            await db.execute(
                delete(TerminalContractAssetUnit).where(
                    TerminalContractAssetUnit.terminal_contract_id
                    == terminal_contract.id
                )
            )
            await db.delete(terminal_contract)
        for change in sorted(upstream_rows, key=lambda c: c.target_key):
            upstream_contract = (
                await db.execute(
                    select(UpstreamContract).where(
                        UpstreamContract.contract_number == change.target_key
                    )
                )
            ).scalar_one_or_none()
            if upstream_contract is None:
                continue
            await db.execute(
                delete(ContractRentSchedule).where(
                    ContractRentSchedule.contract_kind == "upstream",
                    ContractRentSchedule.contract_id == upstream_contract.id,
                )
            )
            await _delete_derived_rows(
                db, kind="upstream", contract_id=upstream_contract.id
            )
            await db.execute(
                delete(UpstreamContractAssetUnit).where(
                    UpstreamContractAssetUnit.upstream_contract_id
                    == upstream_contract.id
                )
            )
            await db.delete(upstream_contract)
        for change in sorted(unit_rows, key=lambda c: c.target_key):
            unit = (
                await db.execute(
                    select(AssetUnit).where(AssetUnit.unit_code == change.target_key)
                )
            ).scalar_one_or_none()
            if unit is not None:
                await db.delete(unit)

        if batch.mode == "update":
            await self._apply_revert_updates(
                db, changes=changes, actor_id=actor_id, scope=scope
            )

        batch.status = "reverted"
        batch.reverted_at = _now()
        batch.reverted_by = actor_id
        batch.revert_reason = reason.strip()
        batch.idempotency_key = idempotency_key
        batch.version += 1
        self._tokens.pop(f"revert:{batch_id}", None)
        await db.commit()
        return {"batch_id": batch_id, "status": "reverted", "idempotent": False}

    async def _apply_revert_updates(
        self,
        db: AsyncSession,
        *,
        changes: list[ImportBatchChange],
        actor_id: str,
        scope: EffectivePartyScope,
    ) -> None:
        reverse = [c for c in changes if c.severity == "change" and c.selected]
        await self._apply_updates_with_values(
            db, changes=reverse, use_old=True, actor_id=actor_id, scope=scope
        )

    async def _apply_updates_with_values(
        self,
        db: AsyncSession,
        *,
        changes: list[ImportBatchChange],
        use_old: bool,
        actor_id: str,
        scope: EffectivePartyScope,
    ) -> None:
        unit_commands = self._require_unit_commands()
        contract_commands = self._require_contract_commands()
        by_target: dict[tuple[str, str], dict[str, ImportBatchChange]] = {}
        for change in changes:
            by_target.setdefault((change.target_type, change.target_key), {})[
                change.field_name
            ] = change
        for (target_type, target_key), fields in sorted(by_target.items()):
            values = {
                field: _coerce_update_value(
                    field, change.old_value if use_old else change.new_value
                )
                for field, change in fields.items()
            }
            if "upstream_contract_number" in values:
                number = values.pop("upstream_contract_number")
                resolved_upstream_id: str | None = None
                if number:
                    for (
                        kind,
                        cid,
                        num,
                        _n,
                    ) in await asset_contract_repository.contract_numbers_in_scope(
                        db, scope=scope
                    ):
                        if num == number and kind == "upstream_contract":
                            resolved_upstream_id = cid
                            break
                values["upstream_contract_id"] = resolved_upstream_id
            if target_type == "asset_unit":
                unit = (
                    await db.execute(
                        select(AssetUnit).where(AssetUnit.unit_code == target_key)
                    )
                ).scalar_one_or_none()
                if unit is None:
                    continue
                await unit_commands.update_asset_unit(
                    db,
                    unit_id=unit.id,
                    request=AssetUnitUpdate(expected_version=unit.version, **values),
                    actor_id=actor_id,
                    scope=scope,
                    auto_commit=False,
                )
                continue
            model = (
                UpstreamContract
                if target_type == "upstream_contract"
                else TerminalContract
            )
            contract = cast(
                "UpstreamContract | TerminalContract | None",
                (
                    await db.execute(
                        select(model).where(model.contract_number == target_key)
                    )
                ).scalar_one_or_none(),
            )
            if contract is None:
                continue
            if target_type == "upstream_contract":
                await contract_commands.update_upstream(
                    db,
                    contract_id=contract.id,
                    request=UpstreamContractUpdate(
                        expected_version=contract.version, **values
                    ),
                    actor_id=actor_id,
                    scope=scope,
                    auto_commit=False,
                )
            else:
                await contract_commands.update_terminal(
                    db,
                    contract_id=contract.id,
                    request=TerminalContractUpdate(
                        expected_version=contract.version, **values
                    ),
                    actor_id=actor_id,
                    scope=scope,
                    auto_commit=False,
                )

    async def _revert_blockers(
        self, db: AsyncSession, batch: ImportBatch
    ) -> list[dict[str, str]]:
        from ...models.archive_document import ArchiveDocument
        from ...models.asset_ledger import RentLedgerEntry, RentPaymentRecord
        from ...models.contract_supplement import ContractSupplement
        from ...models.deposit_ledger import DepositLedgerEntry
        from ...models.management_fee_statement import ManagementFeeStatement

        changes = await self._changes(db, batch.id)
        if batch.mode == "create":
            numbers = [
                c.target_key
                for c in changes
                if c.field_name == "*"
                and c.target_type in ("upstream_contract", "terminal_contract")
            ]
            unit_codes = [
                c.target_key
                for c in changes
                if c.field_name == "*" and c.target_type == "asset_unit"
            ]
        else:
            numbers = sorted({c.target_key for c in changes})
            unit_codes = sorted(
                {c.target_key for c in changes if c.target_type == "asset_unit"}
            )
        blockers: list[dict[str, str]] = []
        contracts: list[UpstreamContract | TerminalContract]
        if numbers:
            upstream_matches = (
                (
                    await db.execute(
                        select(UpstreamContract).where(
                            UpstreamContract.contract_number.in_(numbers)
                        )
                    )
                )
                .scalars()
                .all()
            )
            terminal_matches = (
                (
                    await db.execute(
                        select(TerminalContract).where(
                            TerminalContract.contract_number.in_(numbers)
                        )
                    )
                )
                .scalars()
                .all()
            )
            contracts = [*upstream_matches, *terminal_matches]
        else:
            contracts = []
        contract_ids = [c.id for c in contracts]
        if contract_ids:
            ledger_count = (
                await db.execute(
                    select(func.count())
                    .select_from(RentLedgerEntry)
                    .where(
                        RentLedgerEntry.contract_id.in_(contract_ids),
                        RentLedgerEntry.origin.in_(("manual", "clawback")),
                    )
                )
            ).scalar_one()
            if ledger_count:
                blockers.append({"type": "rent_ledger", "count": str(ledger_count)})
            payment_count = (
                await db.execute(
                    select(func.count())
                    .select_from(RentPaymentRecord)
                    .join(
                        RentLedgerEntry,
                        RentLedgerEntry.id == RentPaymentRecord.ledger_entry_id,
                    )
                    .where(RentLedgerEntry.contract_id.in_(contract_ids))
                )
            ).scalar_one()
            if payment_count:
                blockers.append({"type": "rent_payment", "count": str(payment_count)})
            supplement_count = (
                await db.execute(
                    select(func.count())
                    .select_from(ContractSupplement)
                    .where(ContractSupplement.contract_id.in_(contract_ids))
                )
            ).scalar_one()
            if supplement_count:
                blockers.append(
                    {"type": "contract_supplement", "count": str(supplement_count)}
                )
            archive_count = (
                await db.execute(
                    select(func.count())
                    .select_from(ArchiveDocument)
                    .where(ArchiveDocument.target_id.in_(contract_ids))
                )
            ).scalar_one()
            if archive_count:
                blockers.append(
                    {"type": "archive_document", "count": str(archive_count)}
                )
            from ...models.deposit_ledger import DepositRecord

            deposit_count = (
                await db.execute(
                    select(func.count())
                    .select_from(DepositRecord)
                    .join(
                        DepositLedgerEntry,
                        DepositLedgerEntry.id == DepositRecord.deposit_entry_id,
                    )
                    .where(DepositLedgerEntry.contract_id.in_(contract_ids))
                )
            ).scalar_one()
            if deposit_count:
                blockers.append({"type": "deposit_record", "count": str(deposit_count)})
            statement_rows = (
                (
                    await db.execute(
                        select(ManagementFeeStatement.upstream_contract_ids).where(
                            ManagementFeeStatement.upstream_contract_ids.is_not(None)
                        )
                    )
                )
                .scalars()
                .all()
            )
            statement_count = sum(
                1 for ids in statement_rows if ids and set(ids) & set(contract_ids)
            )
            if statement_count:
                blockers.append(
                    {"type": "management_fee_statement", "count": str(statement_count)}
                )
        if unit_codes and batch.mode == "create":
            units = (
                (
                    await db.execute(
                        select(AssetUnit).where(AssetUnit.unit_code.in_(unit_codes))
                    )
                )
                .scalars()
                .all()
            )
            unit_ids = [u.id for u in units]
            if unit_ids:
                own_contract_ids = {
                    c.id for c in contracts if isinstance(c, UpstreamContract)
                }
                boundary_rows = (
                    (
                        await db.execute(
                            select(
                                UpstreamContractAssetUnit.upstream_contract_id
                            ).where(
                                UpstreamContractAssetUnit.asset_unit_id.in_(unit_ids)
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
                boundary_count = sum(
                    1 for cid in boundary_rows if cid not in own_contract_ids
                )
                if boundary_count:
                    blockers.append(
                        {"type": "upstream_coverage", "count": str(boundary_count)}
                    )
        return blockers


@dataclass
class _Resolution:
    party_ids: dict[str, str]
    projects: dict[str, Project]
    db_units: dict[str, AssetUnit]
    db_contracts: dict[str, tuple[str, str]]
    changes: list[ImportBatchChange]


def _error_change(
    *,
    batch_id: str,
    batch_sheet: str,
    row_number: int,
    target_key: str,
    code: str,
    message: str,
) -> ImportBatchChange:
    return ImportBatchChange(  # type: ignore[call-arg]
        batch_id=batch_id,
        sheet_name=batch_sheet,
        row_number=row_number,
        target_type="asset_unit",
        target_key=target_key,
        field_name=code,
        severity="error",
        effect_summary=message,
    )


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(f"not serializable: {type(value)!r}")


def _proposal_hash(changes: list[ImportBatchChange]) -> str:
    canonical = sorted(
        json.dumps(
            {
                "target_key": c.target_key,
                "target_type": c.target_type,
                "field_name": c.field_name,
                "row_number": c.row_number,
                "sheet_name": c.sheet_name,
                "new_value": c.new_value,
            },
            sort_keys=True,
            default=_json_default,
        )
        for c in changes
    )
    return hashlib.sha256("\n".join(canonical).encode()).hexdigest()


def _stage_dicts(contract: ContractRow) -> list[dict[str, object]]:
    return [
        {
            "stage_start": s.stage_start.isoformat(),
            "stage_end": s.stage_end.isoformat(),
            "base_monthly_rent": str(s.base_monthly_rent),
            "increase_rate": str(s.increase_rate),
            "free_rent_months": str(s.free_rent_months),
            "discount_amount": str(s.discount_amount),
            "actual_monthly_rent": str(s.actual_monthly_rent),
            "payment_cycle": s.payment_cycle,
            "due_day": s.due_day,
            "source_row": s.source_row,
        }
        for s in contract.stages
    ]


def _create_mode_changes(
    parsed: ParsedWorkbook, resolution: _Resolution
) -> list[ImportBatchChange]:
    changes: list[ImportBatchChange] = []
    for unit in parsed.units:
        changes.append(
            ImportBatchChange(  # type: ignore[call-arg]
                sheet_name=UNIT_SHEET,
                row_number=unit.source_row,
                target_type="asset_unit",
                target_key=unit.unit_code,
                field_name="*",
                severity="change",
                effect_summary=f"新增物业单元 {unit.unit_code}",
                new_value={
                    "name": unit.name,
                    "owner_party_name": unit.owner_party_name,
                    "project_code": unit.project_code,
                    "address": unit.address,
                    "usage_type": unit.usage_type,
                    "acquisition_mode": unit.acquisition_mode,
                    "managed_from": unit.managed_from.isoformat()
                    if unit.managed_from
                    else None,
                    "managed_to": unit.managed_to.isoformat()
                    if unit.managed_to
                    else None,
                    "land_area": str(unit.land_area or Decimal("0")),
                    "building_area": str(unit.building_area or Decimal("0")),
                    "rentable_area": str(unit.rentable_area or Decimal("0")),
                },
            )
        )
    for contract in (*parsed.upstreams, *parsed.terminals):
        sheet = "承租合同" if contract in parsed.upstreams else TERMINAL_SHEET
        target_type = (
            "upstream_contract" if contract in parsed.upstreams else "terminal_contract"
        )
        changes.append(
            ImportBatchChange(  # type: ignore[call-arg]
                sheet_name=sheet,
                row_number=contract.source_rows[0],
                target_type=target_type,
                target_key=contract.contract_number,
                field_name="*",
                severity="change",
                effect_summary=f"新增{'承租' if target_type == 'upstream_contract' else '终端'}合同 "
                f"{contract.contract_number}",
                new_value={
                    "contract_number": contract.contract_number,
                    "name": contract.name,
                    "contract_type": contract.contract_type,
                    "contract_mode": contract.contract_mode,
                    "owner_party_name": contract.owner_party_name,
                    "operator_party_name": contract.operator_party_name,
                    "tenant_party_name": contract.tenant_party_name,
                    "lessor_party_name": contract.lessor_party_name,
                    "upstream_contract_number": contract.upstream_contract_number,
                    "payment_cycle": contract.payment_cycle,
                    "payment_day": contract.payment_day,
                    "deposit_amount": str(contract.deposit_amount or Decimal("0")),
                    "management_fee_rate": str(contract.management_fee_rate)
                    if contract.management_fee_rate is not None
                    else None,
                    "unit_codes": contract.unit_codes,
                    "start_date": contract.start_date.isoformat()
                    if contract.start_date
                    else None,
                    "end_date": contract.end_date.isoformat()
                    if contract.end_date
                    else None,
                    "scan_file_name": contract.scan_file_name,
                    "stages": _stage_dicts(contract),
                },
            )
        )
    return changes


def _unit_diff(unit: UnitRow, existing: AssetUnit) -> list[ImportBatchChange]:
    label = f"物业单元 {unit.unit_code}"
    rows: list[ImportBatchChange] = []
    field_map = (
        ("name", unit.name, existing.name),
        ("address", unit.address, existing.address),
        ("usage_type", unit.usage_type, existing.usage_type),
        ("acquisition_mode", unit.acquisition_mode, existing.acquisition_mode),
        (
            "managed_to",
            unit.managed_to.isoformat() if unit.managed_to else None,
            existing.managed_to.isoformat() if existing.managed_to else None,
        ),
        (
            "land_area",
            str(unit.land_area) if unit.land_area is not None else None,
            str(existing.land_area),
        ),
        (
            "building_area",
            str(unit.building_area) if unit.building_area is not None else None,
            str(existing.building_area),
        ),
        (
            "rentable_area",
            str(unit.rentable_area) if unit.rentable_area is not None else None,
            str(existing.rentable_area),
        ),
    )
    for field, new, old in field_map:
        if new is None:
            continue
        if str(old) == new:
            continue
        rows.append(
            ImportBatchChange(  # type: ignore[call-arg]
                sheet_name=UNIT_SHEET,
                row_number=unit.source_row,
                target_type="asset_unit",
                target_key=unit.unit_code,
                field_name=field,
                severity="change",
                effect_summary=f"{label}: {field} {old} → {new}",
                old_value={"value": str(old) if old is not None else None},
                new_value={"value": new},
            )
        )
    return rows


def _contract_diff(
    contract: ContractRow,
    existing: UpstreamContract | TerminalContract,
    sheet: str,
) -> list[ImportBatchChange]:
    label = f"合同 {contract.contract_number}"
    target_type = (
        "upstream_contract"
        if isinstance(existing, UpstreamContract)
        else "terminal_contract"
    )
    rows: list[ImportBatchChange] = []
    field_map: tuple[tuple[str, object, object], ...] = (
        ("name", contract.name, getattr(existing, "name", None)),
        (
            "deposit_amount",
            str(contract.deposit_amount)
            if contract.deposit_amount is not None
            else None,
            str(existing.deposit_amount),
        ),
        (
            "end_date",
            contract.end_date.isoformat() if contract.end_date else None,
            existing.end_date.isoformat() if existing.end_date else None,
        ),
    )
    if isinstance(existing, UpstreamContract):
        field_map = field_map + (
            (
                "management_fee_rate",
                str(contract.management_fee_rate)
                if contract.management_fee_rate is not None
                else None,
                str(existing.management_fee_rate)
                if existing.management_fee_rate is not None
                else None,
            ),
        )
    else:
        field_map = field_map + (
            (
                "upstream_contract_number",
                contract.upstream_contract_number,
                None,
            ),
        )
    for field, new, old in field_map:
        if new is None:
            continue
        if old is not None and str(old) == str(new):
            continue
        rows.append(
            ImportBatchChange(  # type: ignore[call-arg]
                sheet_name=sheet,
                row_number=contract.source_rows[0],
                target_type=target_type,
                target_key=contract.contract_number,
                field_name=field,
                severity="change",
                effect_summary=f"{label}: {field} {old} → {new}",
                old_value={"value": str(old) if old is not None else None},
                new_value={"value": str(new)},
            )
        )
    return rows


async def _delete_derived_rows(
    db: AsyncSession, *, kind: str, contract_id: str
) -> None:
    """Remove obligations derived from the contract itself during revert."""
    from ...models.asset_ledger import RentLedgerEntry
    from ...models.deposit_ledger import DepositLedgerEntry

    await db.execute(
        delete(RentLedgerEntry).where(
            RentLedgerEntry.contract_kind == kind,
            RentLedgerEntry.contract_id == contract_id,
            RentLedgerEntry.origin == "generated",
        )
    )
    await db.execute(
        delete(DepositLedgerEntry).where(
            DepositLedgerEntry.contract_kind == kind,
            DepositLedgerEntry.contract_id == contract_id,
        )
    )


async def _party_name(db: AsyncSession, party_id: str) -> str:
    party = (
        await db.execute(select(Party).where(Party.id == party_id))
    ).scalar_one_or_none()
    return party.name if party is not None else ""


async def _project_code(db: AsyncSession, project_id: str) -> str:
    project = (
        await db.execute(select(Project).where(Project.id == project_id))
    ).scalar_one_or_none()
    return project.project_code if project is not None else ""


async def _unit_codes_for(db: AsyncSession, unit_ids: Sequence[str]) -> str:
    if not unit_ids:
        return ""
    rows = (
        (
            await db.execute(
                select(AssetUnit.unit_code).where(AssetUnit.id.in_(unit_ids))
            )
        )
        .scalars()
        .all()
    )
    return ",".join(sorted(rows))


def _version_conflict(
    *, batch_id: str, expected: int, actual: int
) -> BaseBusinessError:
    from .errors import AssetOperationsVersionConflictError

    return AssetOperationsVersionConflictError(
        unit_id=batch_id, expected_version=expected, actual_version=actual
    )


def _parse_iso_date(value: object) -> date:
    return date.fromisoformat(str(value))


def _coerce_update_value(field: str, payload: dict[str, object] | None) -> Any:
    value = (payload or {}).get("value")
    if field in ("deposit_amount", "land_area", "building_area", "rentable_area"):
        return Decimal(str(value)) if value is not None else None
    if field in ("end_date", "managed_to", "managed_from"):
        return _parse_iso_date(value) if value else None
    return value


async def _resolve_party_id(
    db: AsyncSession, payload: dict[str, object], key: str
) -> str:
    name = payload.get(key.replace("_id", "_name")) or payload.get(key)
    party = (
        await db.execute(
            select(Party).where(
                Party.name == name,
                Party.review_status == "approved",
                Party.status == "active",
                Party.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if party is None:
        raise ImportBatchStateError(message=f"主体解析失败: {name}")
    return party.id


def _revert_deadline(committed_at: datetime | None) -> datetime:
    from zoneinfo import ZoneInfo

    shanghai = ZoneInfo("Asia/Shanghai")
    moment = committed_at or _now()
    local_date = moment.astimezone(shanghai).date()
    return datetime(
        local_date.year, local_date.month, local_date.day, tzinfo=shanghai
    ) + timedelta(days=7)


import_batch_service = ImportBatchService()  # noqa: E402 - module-level singleton
