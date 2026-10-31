"""Submission, snapshot and withdrawal commands for monthly occupancy reports."""

from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
import secrets
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Protocol
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.cache_manager import cache_manager
from ...core.exception_handler import (
    ResourceNotFoundError,
    ServiceUnavailableError,
)
from ...crud.assessment_scope import assessment_scope_repository
from ...crud.asset_contract import asset_contract_repository
from ...crud.business_change_event import business_change_repository
from ...crud.occupancy_report import occupancy_report_repository
from ...crud.rent_commands import rent_command_repository
from ...models.assessment_scope import AssessmentScopeItem, AssessmentScopeVersion
from ...models.asset_contract import AssetContractWriteReceipt
from ...models.asset_unit import AssetUnit
from ...models.business_change_event import BusinessChangeEvent
from ...models.occupancy_report import (
    MonthlyOccupancyReport,
    MonthlyOccupancyReportLine,
)
from ...schemas.asset_operations import (
    AssessmentScopeVersionSummary,
    OccupancyReportFieldChange,
    OccupancyReportLineSnapshot,
    OccupancyReportMustHandleItem,
    OccupancyReportProjectCounts,
    OccupancyReportSnapshotResponse,
    OccupancyReportSubmissionPreviewResponse,
    OccupancyReportSubmitResponse,
    OccupancyReportTotals,
    OccupancyReportUnitDiff,
    OccupancyReportWithdrawalPreviewResponse,
    OccupancyReportWithdrawResponse,
    SubmitOccupancyReportRequest,
    WithdrawOccupancyReportRequest,
)
from ..party_scope_resolver import EffectivePartyScope
from .assessment_scope_command_service import (
    require_operator_access,
    summarize_version,
    view_for,
)
from .errors import (
    AssetOperationsIdempotencyConflictError,
    AssetOperationsPreviewStaleError,
    AssetOperationsVersionConflictError,
    OccupancyReportAlreadySubmittedError,
    OccupancyReportAlreadyWithdrawnError,
    OccupancyReportNotSubmittedError,
    OccupancyReportPeriodInvalidError,
    OccupancyReportScopeMissingError,
)
from .occupancy_report_draft_rules import (
    FieldChange,
    ReportAggregates,
    ReportLine,
    ReportLineFact,
    compare_with_baseline,
    month_end,
    project_counts,
)
from .occupancy_report_draft_service import DerivedReportFacts, derive_report_lines
from .occupancy_report_snapshot_rules import (
    CurrentLine,
    SnapshotLine,
    diff_snapshot_against_current,
)
from .rent_command_support import require_scope

_BUSINESS_TIMEZONE = ZoneInfo("Asia/Shanghai")
_PREVIEW_TTL = timedelta(minutes=10)
_SUBMIT_ACTION = "submit_occupancy_report"
_WITHDRAW_ACTION = "withdraw_occupancy_report"


class OccupancyReportPreviewStoreProtocol(Protocol):
    def issue(self, payload: dict[str, object]) -> tuple[str, datetime]: ...

    def peek(self, raw_token: str) -> dict[str, object] | None: ...

    def delete(self, raw_token: str) -> bool: ...


class OccupancyReportPreviewStore:
    """Short-lived tokens deleted only after a successful command."""

    NAMESPACE = "occupancy_report_command"
    TTL = _PREVIEW_TTL

    def __init__(self, *, clock: Callable[[], datetime] | None = None) -> None:
        self._clock = clock or (lambda: datetime.now(UTC).replace(tzinfo=None))

    def issue(self, payload: dict[str, object]) -> tuple[str, datetime]:
        token = secrets.token_urlsafe(32)
        expires_at = self._clock() + self.TTL
        if not cache_manager.set(
            self._token_hash(token),
            {**payload, "expires_at": expires_at.isoformat()},
            ttl=int(self.TTL.total_seconds()),
            namespace=self.NAMESPACE,
        ):
            raise ServiceUnavailableError(
                "无法保存报送命令预览",
                service_name=self.NAMESPACE,
            )
        return token, expires_at

    def peek(self, raw_token: str) -> dict[str, object] | None:
        token = str(raw_token).strip()
        if token == "":  # nosec B105 - empty-token guard
            return None
        payload = cache_manager.get(
            self._token_hash(token), namespace=self.NAMESPACE
        )
        if not isinstance(payload, dict):
            return None
        expires_at_raw = payload.get("expires_at")
        if not isinstance(expires_at_raw, str):
            return None
        try:
            expires_at = datetime.fromisoformat(expires_at_raw)
        except ValueError:
            return None
        if expires_at <= self._clock():
            return None
        return payload

    def delete(self, raw_token: str) -> bool:
        token = str(raw_token).strip()
        if token == "":  # nosec B105 - empty-token guard
            return False
        return cache_manager.delete(
            self._token_hash(token), namespace=self.NAMESPACE
        )

    @staticmethod
    def _token_hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class _ReportFacts:
    """Everything the submission snapshot needs, recomputed under lock."""

    scope_version: AssessmentScopeVersion
    chain: MonthlyOccupancyReport | None
    items: tuple[AssessmentScopeItem, ...]
    candidates: tuple[AssetUnit, ...]
    lines: tuple[ReportLine, ...]
    aggregates: ReportAggregates
    totals: OccupancyReportTotals
    project_counts: OccupancyReportProjectCounts
    state_fingerprint: str


class OccupancyReportSubmissionService:
    """Own locking, recomputation, snapshot persistence and withdrawal."""

    def __init__(
        self,
        *,
        preview_store: OccupancyReportPreviewStoreProtocol | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.repository = occupancy_report_repository
        self._clock = clock or (lambda: datetime.now(UTC).replace(tzinfo=None))
        self.preview_store = preview_store or OccupancyReportPreviewStore(
            clock=self._clock
        )

    async def submission_preview(
        self,
        db: AsyncSession,
        *,
        operator_party_id: str,
        period: str,
        actor_id: str,
        scope: EffectivePartyScope,
    ) -> OccupancyReportSubmissionPreviewResponse:
        """Gate the submission and bind a token when nothing blocks it."""
        require_scope(scope, actor_id)
        require_operator_access(scope, operator_party_id=operator_party_id)
        await self._require_party(db, operator_party_id)
        self._validate_period(period)
        chain = await self.repository.get_active_chain_report(
            db,
            operator_party_id=operator_party_id,
            period=period,
        )
        if chain is not None and chain.status == "submitted":
            raise OccupancyReportAlreadySubmittedError(
                report_id=chain.id, period=period
            )
        scope_version = await self._require_scope_version(
            db, operator_party_id=operator_party_id, period=period
        )
        facts = await self._derive(
            db,
            scope_version=scope_version,
            operator_party_id=operator_party_id,
            period=period,
            chain=chain,
        )
        pending = self._pending_units(facts)
        gate_reasons: list[str] = []
        if len(pending) > 0:
            gate_reasons.append("pending_units_unconfirmed")
        change_note = chain.change_note if chain is not None else None
        normalized_note = (
            change_note.strip() if change_note is not None else None
        )
        if normalized_note == "":
            normalized_note = None
        baseline_row = await self._baseline_row(
            db, operator_party_id=operator_party_id, period=period
        )
        changes = self._compare_with_baseline_row(
            baseline_row, aggregates=facts.aggregates
        )
        if len(changes) > 0 and not normalized_note:
            gate_reasons.append("change_note_required")
        can_submit = len(gate_reasons) == 0
        preview_token: str | None = None
        expires_at: datetime | None = None
        if can_submit:
            preview_token, expires_at = self.preview_store.issue(
                {
                    "actor_id": actor_id,
                    "action": _SUBMIT_ACTION,
                    "operator_party_id": operator_party_id,
                    "period": period,
                    "scope_version_id": scope_version.id,
                    "versions": {scope_version.id: scope_version.version},
                    "chain_id": chain.id if chain is not None else None,
                    "state_fingerprint": facts.state_fingerprint,
                }
            )
            expires_at = self._api_datetime(expires_at)
        return OccupancyReportSubmissionPreviewResponse(
            operator_party_id=operator_party_id,
            period=period,
            can_submit=can_submit,
            gate_reasons=gate_reasons,
            must_handle=[
                OccupancyReportMustHandleItem(asset_unit_id=unit_id, reason=reason)  # type: ignore[arg-type]
                for unit_id, reason in pending
            ],
            suggested=[],
            normalized_note=normalized_note,
            totals=facts.totals,
            changes=[
                OccupancyReportFieldChange(
                    field_name=change.field_name,
                    previous=change.previous,
                    current=change.current,
                )
                for change in changes
            ],
            first_report=baseline_row is None,
            scope_version=self._scope_summary(scope_version),  # type: ignore[arg-type]
            preview_token=preview_token,
            expires_at=expires_at,
        )

    async def submit(
        self,
        db: AsyncSession,
        *,
        operator_party_id: str,
        period: str,
        request: SubmitOccupancyReportRequest,
        actor_id: str,
        scope: EffectivePartyScope,
        idempotency_key: str,
    ) -> OccupancyReportSubmitResponse:
        """Atomically lock the snapshot, audit and receipt into one chain row."""
        require_scope(scope, actor_id)
        request_fingerprint = self._request_fingerprint(
            actor_id=actor_id,
            idempotency_key=idempotency_key,
            operator_party_id=operator_party_id,
            period=period,
            request=request,
        )
        existing = await self._get_receipt(
            db, actor_id=actor_id, idempotency_key=idempotency_key
        )
        if existing is not None:
            return self._replay_submit(
                existing, request_fingerprint=request_fingerprint
            )

        require_operator_access(scope, operator_party_id=operator_party_id)
        await self._require_party(db, operator_party_id)
        self._validate_period(period)
        payload = self._peek_token(
            request.preview_token,
            action=_SUBMIT_ACTION,
            actor_id=actor_id,
            operator_party_id=operator_party_id,
            period=period,
        )
        if payload.get("scope_version_id") != request.expected_scope_version_id:
            raise AssetOperationsPreviewStaleError("target_mismatch")
        token_versions = payload.get("versions")
        if not isinstance(token_versions, dict):
            raise AssetOperationsPreviewStaleError("versions_missing")
        if (
            token_versions.get(request.expected_scope_version_id)
            != request.expected_scope_version
        ):
            raise AssetOperationsVersionConflictError(
                unit_id=request.expected_scope_version_id,
                expected_version=request.expected_scope_version,
                actual_version=-1,
            )

        # Serialize against note edits, other submissions and scope commits.
        await self.repository.lock_serialization(
            db, operator_party_id=operator_party_id, period=period
        )
        await assessment_scope_repository.lock_serialization(
            db,
            operator_party_id=operator_party_id,
            year=int(period[:4]),
        )
        scope_version = await assessment_scope_repository.get_active_version(
            db,
            operator_party_id=operator_party_id,
            year=int(period[:4]),
        )
        if (
            scope_version is None
            or scope_version.id != request.expected_scope_version_id
        ):
            raise AssetOperationsPreviewStaleError("scope_changed")
        if scope_version.version != request.expected_scope_version:
            raise AssetOperationsVersionConflictError(
                unit_id=scope_version.id,
                expected_version=request.expected_scope_version,
                actual_version=scope_version.version,
            )
        chain = await self.repository.get_active_chain_report(
            db,
            operator_party_id=operator_party_id,
            period=period,
            for_update=True,
        )
        if chain is not None and chain.status == "submitted":
            raise OccupancyReportAlreadySubmittedError(
                report_id=chain.id, period=period
            )

        facts = await self._derive(
            db,
            scope_version=scope_version,
            operator_party_id=operator_party_id,
            period=period,
            chain=chain,
        )
        if payload.get("state_fingerprint") != facts.state_fingerprint:
            raise AssetOperationsPreviewStaleError("state_changed")
        pending = self._pending_units(facts)
        if len(pending) > 0:
            raise AssetOperationsPreviewStaleError("pending_units_unconfirmed")
        change_note = chain.change_note if chain is not None else None
        normalized_note = (
            change_note.strip() if change_note is not None else None
        )
        baseline_row = await self._baseline_row(
            db, operator_party_id=operator_party_id, period=period
        )
        changes = self._compare_with_baseline_row(
            baseline_row, aggregates=facts.aggregates
        )
        if len(changes) > 0 and not normalized_note:
            raise AssetOperationsPreviewStaleError("change_note_required")

        existing = await self._get_receipt(
            db, actor_id=actor_id, idempotency_key=idempotency_key
        )
        if existing is not None:
            return self._replay_submit(
                existing, request_fingerprint=request_fingerprint
            )

        occurred_at = self._clock()
        if chain is None:
            chain = await self.repository.create_chain_report(
                db,
                operator_party_id=operator_party_id,
                period=period,
                actor_id=actor_id,
                created_at=self._database_datetime(occurred_at),
            )
        chain.status = "submitted"
        chain.scope_version_id = scope_version.id
        chain.project_count = facts.project_counts.project_count
        chain.operating_project_count = (
            facts.project_counts.operating_project_count
        )
        chain.non_operating_project_count = (
            facts.project_counts.non_operating_project_count
        )
        chain.unit_count = facts.totals.unit_count
        chain.rented_unit_count = facts.totals.rented_unit_count
        chain.occupancy_rate = facts.totals.occupancy_rate
        chain.land_area = facts.totals.land_area
        chain.building_area = facts.totals.building_area
        chain.rentable_area = facts.totals.rentable_area
        chain.rented_area = facts.totals.rented_area
        chain.submitted_by = actor_id
        chain.submitted_at = self._database_datetime(occurred_at)
        chain.version = chain.version + 1
        await self.repository.replace_lines(
            db,
            report_id=chain.id,
            lines=[
                MonthlyOccupancyReportLine(  # type: ignore[call-arg]
                    id=str(uuid.uuid4()),
                    report_id=chain.id,
                    asset_unit_id=line.asset_unit_id,
                    owner_name_snapshot=line.owner_name_snapshot,
                    usage_type_snapshot=line.usage_type_snapshot,
                    project_name_snapshot=line.project_name_snapshot,
                    address_snapshot=line.address_snapshot,
                    land_area=line.land_area,
                    building_area=line.building_area,
                    rentable_area=line.rentable_area,
                    rented_area=line.rented_area,
                    unit_count=line.unit_count,
                    rented_unit_count=line.rented_unit_count,
                    rental_status=line.rental_status,
                    terminal_contract_ids=list(line.terminal_contract_ids),
                )
                for line in facts.lines
            ],
        )
        await self._add_audit(
            db,
            target_id=chain.id,
            action="submit",
            actor_id=actor_id,
            before={
                "status": "draft",
                "operator_party_id": operator_party_id,
                "period": period,
            },
            after={
                "status": "submitted",
                "scope_version_id": scope_version.id,
                "unit_count": facts.totals.unit_count,
                "rented_unit_count": facts.totals.rented_unit_count,
                "line_count": len(facts.lines),
            },
            occurred_at=occurred_at,
            correlation_id=chain.id,
        )
        response = OccupancyReportSubmitResponse(
            report_id=chain.id,
            operator_party_id=operator_party_id,
            period=period,
            status="submitted",
            scope_version_id=scope_version.id,
            submitted_at=self._api_datetime(occurred_at),
            totals=facts.totals,
            line_count=len(facts.lines),
            idempotent=False,
        )
        await self._add_receipt(
            db,
            actor_id=actor_id,
            idempotency_key=idempotency_key,
            request_fingerprint=request_fingerprint,
            result=response,
            command_kind="submit_occupancy_report",
        )
        try:
            await db.commit()
        except IntegrityError as exc:
            await db.rollback()
            concurrent = await self._get_receipt(
                db, actor_id=actor_id, idempotency_key=idempotency_key
            )
            if concurrent is not None:
                replay = self._replay_submit(
                    concurrent, request_fingerprint=request_fingerprint
                )
                self.preview_store.delete(request.preview_token)
                return replay
            raise AssetOperationsPreviewStaleError(
                "concurrent_modification"
            ) from exc
        self.preview_store.delete(request.preview_token)
        return response

    async def get_snapshot(
        self,
        db: AsyncSession,
        *,
        report_id: str,
        actor_id: str,
        scope: EffectivePartyScope,
    ) -> OccupancyReportSnapshotResponse:
        """Read-only snapshot with a live diff; nothing is ever rewritten."""
        require_scope(scope, actor_id)
        report = await self.repository.get_any_status(db, report_id=report_id)
        if report is None:
            raise ResourceNotFoundError("MonthlyOccupancyReport", report_id)
        require_operator_access(
            scope, operator_party_id=report.operator_party_id
        )
        if report.status == "draft":
            raise OccupancyReportNotSubmittedError(report_id=report.id)
        lines = await self.repository.list_lines(db, report_id=report.id)
        snapshot_lines = tuple(
            SnapshotLine(
                asset_unit_id=line.asset_unit_id,
                owner_name_snapshot=line.owner_name_snapshot,
                usage_type_snapshot=line.usage_type_snapshot,
                project_name_snapshot=line.project_name_snapshot,
                address_snapshot=line.address_snapshot,
                land_area=line.land_area,
                building_area=line.building_area,
                rentable_area=line.rentable_area,
                rented_area=line.rented_area,
                rented_unit_count=line.rented_unit_count,
                rental_status=line.rental_status,
                terminal_contract_ids=list(line.terminal_contract_ids),
            )
            for line in lines
        )
        current_lines = await self._current_lines(
            db,
            operator_party_id=report.operator_party_id,
            period=report.period,
        )
        differences = diff_snapshot_against_current(
            snapshot_lines, current_lines
        )
        scope_version = None
        if report.scope_version_id is not None:
            scope_version = await assessment_scope_repository.get_version(
                db, version_id=report.scope_version_id
            )
        totals = OccupancyReportTotals(
            unit_count=report.unit_count or 0,
            rented_unit_count=report.rented_unit_count or 0,
            occupancy_rate=report.occupancy_rate,
            land_area=report.land_area or 0,  # type: ignore[arg-type]
            building_area=report.building_area or 0,  # type: ignore[arg-type]
            rentable_area=report.rentable_area or 0,  # type: ignore[arg-type]
            rented_area=report.rented_area or 0,  # type: ignore[arg-type]
        )
        return OccupancyReportSnapshotResponse(
            report_id=report.id,
            operator_party_id=report.operator_party_id,
            period=report.period,
            status=report.status,  # type: ignore[arg-type]
            scope_version=self._scope_summary(scope_version),  # type: ignore[arg-type]
            change_note=report.change_note,
            submitted_at=self._api_datetime(report.submitted_at),  # type: ignore[arg-type]
            withdrawn_at=self._api_datetime(report.withdrawn_at)
            if report.withdrawn_at is not None
            else None,
            withdraw_reason=report.withdraw_reason,
            predecessor_report_id=report.predecessor_report_id,
            totals=totals,
            project_counts=OccupancyReportProjectCounts(
                project_count=report.project_count or 0,
                operating_project_count=report.operating_project_count or 0,
                non_operating_project_count=(
                    report.non_operating_project_count or 0
                ),
            ),
            lines=[
                OccupancyReportLineSnapshot(
                    asset_unit_id=line.asset_unit_id,
                    owner_name_snapshot=line.owner_name_snapshot,
                    usage_type_snapshot=line.usage_type_snapshot,
                    project_name_snapshot=line.project_name_snapshot,
                    address_snapshot=line.address_snapshot,
                    land_area=line.land_area,
                    building_area=line.building_area,
                    rentable_area=line.rentable_area,
                    rented_area=line.rented_area,
                    unit_count=line.unit_count,  # type: ignore[arg-type]
                    rented_unit_count=line.rented_unit_count,  # type: ignore[arg-type]
                    rental_status=line.rental_status,  # type: ignore[arg-type]
                    terminal_contract_ids=list(line.terminal_contract_ids),
                )
                for line in lines
            ],
            differences=[
                OccupancyReportUnitDiff(
                    asset_unit_id=entry.asset_unit_id,
                    kind=entry.kind,  # type: ignore[arg-type]
                    changes=[
                        OccupancyReportFieldChange(
                            field_name=change.field_name,
                            previous=change.snapshot_value,
                            current=change.current_value,
                        )
                        for change in entry.changes
                    ],
                )
                for entry in differences
            ],
        )

    async def withdrawal_preview(
        self,
        db: AsyncSession,
        *,
        report_id: str,
        actor_id: str,
        scope: EffectivePartyScope,
    ) -> OccupancyReportWithdrawalPreviewResponse:
        """Describe the withdrawal impact and bind a withdrawal token."""
        require_scope(scope, actor_id)
        report = await self.repository.get_any_status(db, report_id=report_id)
        if report is None:
            raise ResourceNotFoundError("MonthlyOccupancyReport", report_id)
        require_operator_access(
            scope, operator_party_id=report.operator_party_id
        )
        if report.status == "draft":
            raise OccupancyReportNotSubmittedError(report_id=report.id)
        if report.status == "withdrawn":
            raise OccupancyReportAlreadyWithdrawnError(report_id=report.id)
        token, expires_at = self.preview_store.issue(
            {
                "actor_id": actor_id,
                "action": _WITHDRAW_ACTION,
                "report_id": report.id,
                "operator_party_id": report.operator_party_id,
                "period": report.period,
                "versions": {report.id: report.version},
                "state_fingerprint": self._report_fingerprint(report),
            }
        )
        return OccupancyReportWithdrawalPreviewResponse(
            report_id=report.id,
            operator_party_id=report.operator_party_id,
            period=report.period,
            submitted_at=self._api_datetime(report.submitted_at),  # type: ignore[arg-type]
            successor_draft_rule="fresh_draft_with_predecessor_link",
            preview_token=token,
            expires_at=self._api_datetime(expires_at),
            report_version=report.version,
        )

    async def withdraw(
        self,
        db: AsyncSession,
        *,
        report_id: str,
        request: WithdrawOccupancyReportRequest,
        actor_id: str,
        scope: EffectivePartyScope,
        idempotency_key: str,
    ) -> OccupancyReportWithdrawResponse:
        """Mark the snapshot withdrawn and open a successor draft chain."""
        require_scope(scope, actor_id)
        request_fingerprint = self._withdraw_fingerprint(
            actor_id=actor_id,
            idempotency_key=idempotency_key,
            report_id=report_id,
            request=request,
        )
        existing = await self._get_receipt(
            db, actor_id=actor_id, idempotency_key=idempotency_key
        )
        if existing is not None:
            return self._replay_withdraw(
                existing, request_fingerprint=request_fingerprint
            )

        # Terminal-state checks come before token consumption so repeated
        # withdrawals surface the specific conflict instead of a stale token.
        previewed = await self.repository.get_any_status(db, report_id=report_id)
        if previewed is not None:
            require_operator_access(
                scope, operator_party_id=previewed.operator_party_id
            )
            if previewed.status == "draft":
                raise OccupancyReportNotSubmittedError(report_id=previewed.id)
            if previewed.status == "withdrawn":
                raise OccupancyReportAlreadyWithdrawnError(
                    report_id=previewed.id
                )
        payload = self._peek_token(
            request.preview_token,
            action=_WITHDRAW_ACTION,
            actor_id=actor_id,
            operator_party_id=None,
            period=None,
            report_id=report_id,
        )
        token_versions = payload.get("versions")
        if not isinstance(token_versions, dict):
            raise AssetOperationsPreviewStaleError("versions_missing")
        if token_versions.get(report_id) != request.expected_version:
            raise AssetOperationsVersionConflictError(
                unit_id=report_id,
                expected_version=request.expected_version,
                actual_version=-1,
            )

        await self.repository.lock_serialization(
            db,
            operator_party_id=payload["operator_party_id"],  # type: ignore[arg-type]
            period=payload["period"],  # type: ignore[arg-type]
        )
        report = await self.repository.get_any_status(
            db, report_id=report_id, for_update=True
        )
        if report is None:
            raise ResourceNotFoundError("MonthlyOccupancyReport", report_id)
        require_operator_access(
            scope, operator_party_id=report.operator_party_id
        )
        if report.status == "draft":
            raise OccupancyReportNotSubmittedError(report_id=report.id)
        if report.status == "withdrawn":
            raise OccupancyReportAlreadyWithdrawnError(report_id=report.id)
        if report.version != request.expected_version:
            raise AssetOperationsVersionConflictError(
                unit_id=report.id,
                expected_version=request.expected_version,
                actual_version=report.version,
            )
        if payload.get("state_fingerprint") != self._report_fingerprint(report):
            raise AssetOperationsPreviewStaleError("state_changed")

        existing = await self._get_receipt(
            db, actor_id=actor_id, idempotency_key=idempotency_key
        )
        if existing is not None:
            return self._replay_withdraw(
                existing, request_fingerprint=request_fingerprint
            )

        occurred_at = self._clock()
        report.status = "withdrawn"
        report.withdrawn_by = actor_id
        report.withdrawn_at = self._database_datetime(occurred_at)
        report.withdraw_reason = request.withdraw_reason.strip()
        report.version = report.version + 1
        # Flush the demotion first: two non-withdrawn rows for one
        # operator-period would violate the partial unique chain index.
        await db.flush()
        successor = MonthlyOccupancyReport(  # type: ignore[call-arg]
            id=str(uuid.uuid4()),
            operator_party_id=report.operator_party_id,
            period=report.period,
            status="draft",
            predecessor_report_id=report.id,
            created_by=actor_id,
            created_at=self._database_datetime(occurred_at),
        )
        db.add(successor)
        await db.flush()
        await self._add_audit(
            db,
            target_id=report.id,
            action="withdraw",
            actor_id=actor_id,
            before={
                "status": "submitted",
                "operator_party_id": report.operator_party_id,
                "period": report.period,
            },
            after={
                "status": "withdrawn",
                "successor_draft_id": successor.id,
                "withdraw_reason": report.withdraw_reason,
            },
            occurred_at=occurred_at,
            correlation_id=report.id,
        )
        response = OccupancyReportWithdrawResponse(
            report_id=report.id,
            status="withdrawn",
            withdrawn_at=self._api_datetime(occurred_at),
            successor_draft_id=successor.id,
            idempotent=False,
        )
        await self._add_receipt(
            db,
            actor_id=actor_id,
            idempotency_key=idempotency_key,
            request_fingerprint=request_fingerprint,
            result=response,
            command_kind="withdraw_occupancy_report",
        )
        try:
            await db.commit()
        except IntegrityError as exc:
            await db.rollback()
            concurrent = await self._get_receipt(
                db, actor_id=actor_id, idempotency_key=idempotency_key
            )
            if concurrent is not None:
                replay = self._replay_withdraw(
                    concurrent, request_fingerprint=request_fingerprint
                )
                self.preview_store.delete(request.preview_token)
                return replay
            raise AssetOperationsPreviewStaleError(
                "concurrent_modification"
            ) from exc
        self.preview_store.delete(request.preview_token)
        return response

    async def create_export_task(
        self,
        db: AsyncSession,
        *,
        report_id: str,
        actor_id: str,
        scope: EffectivePartyScope,
    ) -> str:
        """Queue an async export over the immutable snapshot rows."""
        require_scope(scope, actor_id)
        report = await self.repository.get_any_status(db, report_id=report_id)
        if report is None:
            raise ResourceNotFoundError("MonthlyOccupancyReport", report_id)
        require_operator_access(
            scope, operator_party_id=report.operator_party_id
        )
        if report.status == "draft":
            raise OccupancyReportNotSubmittedError(report_id=report.id)
        from ...enums.task import TaskType
        from ...schemas.task import TaskCreate
        from ...services.task.service import task_service

        task = await task_service.create_task(
            db,
            obj_in=TaskCreate(
                task_type=TaskType.EXCEL_EXPORT,
                title="月度出租率报送导出",
                description=f"导出 {report.period} 报送快照",
                parameters={"report_id": report.id, "period": report.period},
                config={},
            ),
            user_id=actor_id,
        )
        await db.commit()
        # No separate worker process exists yet, so the caller renders inside
        # the request and this task row records the completed result; clients
        # poll the standard task endpoint for the payload.
        return str(task.id)

    async def render_export(self, db: AsyncSession, *, task_id: str) -> None:
        """Render the snapshot CSV and finish the queued export task."""
        from ...enums.task import TaskStatus

        task = await self.repository.get_async_task(db, task_id=task_id)
        if task is None:
            raise ResourceNotFoundError("AsyncTask", task_id)
        parameters = task.parameters or {}
        report_id = str(parameters.get("report_id", ""))
        report = await self.repository.get_any_status(db, report_id=report_id)
        if report is None or report.status == "draft":
            await self.repository.finish_task(
                db,
                task=task,
                status=TaskStatus.FAILED,
                error_message="报送快照不存在或未提交",
                completed_at=self._database_datetime(self._clock()),
            )
            return
        lines = await self.repository.list_lines(db, report_id=report.id)
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            [
                "asset_unit_id",
                "owner_name",
                "usage_type",
                "project_name",
                "address",
                "land_area",
                "building_area",
                "rentable_area",
                "rented_area",
                "rented_unit_count",
                "rental_status",
                "terminal_contract_ids",
            ]
        )
        for line in lines:
            writer.writerow(
                [
                    line.asset_unit_id,
                    line.owner_name_snapshot,
                    line.usage_type_snapshot,
                    line.project_name_snapshot,
                    line.address_snapshot,
                    str(line.land_area),
                    str(line.building_area),
                    str(line.rentable_area),
                    str(line.rented_area),
                    str(line.rented_unit_count),
                    line.rental_status,
                    "|".join(line.terminal_contract_ids),
                ]
            )
        content = buffer.getvalue()
        await self.repository.finish_task(
            db,
            task=task,
            status=TaskStatus.COMPLETED,
            completed_at=self._database_datetime(self._clock()),
            result_data={
                "file_name": f"occupancy-report-{report.period}.csv",
                "content_base64": base64.b64encode(
                    content.encode("utf-8")
                ).decode("ascii"),
                "line_count": len(lines),
            },
        )

    # ------------------------------------------------------------------ utils

    async def _derive(
        self,
        db: AsyncSession,
        *,
        scope_version: AssessmentScopeVersion,
        operator_party_id: str,
        period: str,
        chain: MonthlyOccupancyReport | None,
    ) -> _ReportFacts:
        items = tuple(
            await assessment_scope_repository.list_items(
                db, version_id=scope_version.id
            )
        )
        candidates = await assessment_scope_repository.list_managed_units(
            db,
            operator_party_id=operator_party_id,
            as_of=_business_today(),
            year=int(period[:4]),
        )
        derived = await derive_report_lines(
            db,
            scope_version=scope_version,
            items=items,
            candidates=candidates,
            period=period,
        )
        end_of_month = month_end(period)
        full_set_units = [
            unit
            for unit in candidates
            if unit.managed_from <= end_of_month
            and (unit.managed_to is None or unit.managed_to >= end_of_month)
        ]
        counts = project_counts(
            self._full_set_facts(full_set_units)
        )
        return _ReportFacts(
            scope_version=scope_version,
            chain=chain,
            items=items,
            candidates=tuple(candidates),
            lines=derived.lines,
            aggregates=derived.aggregates,
            totals=OccupancyReportTotals(
                unit_count=derived.aggregates.unit_count,
                rented_unit_count=derived.aggregates.rented_unit_count,
                occupancy_rate=derived.aggregates.occupancy_rate,
                land_area=derived.aggregates.land_area,
                building_area=derived.aggregates.building_area,
                rentable_area=derived.aggregates.rentable_area,
                rented_area=derived.aggregates.rented_area,
            ),
            project_counts=OccupancyReportProjectCounts(
                project_count=counts[0],
                operating_project_count=counts[1],
                non_operating_project_count=counts[2],
            ),
            state_fingerprint=self._state_fingerprint(
                scope_version=scope_version,
                chain=chain,
                candidates=tuple(candidates),
                derived=derived,
            ),
        )

    @staticmethod
    def _full_set_facts(units: list[AssetUnit]) -> list[ReportLineFact]:
        return [
            ReportLineFact(
                unit_id=unit.id,
                managed_from=unit.managed_from,
                managed_to=unit.managed_to,
                is_operating=unit.is_operating,
                included=False,
                rented=False,
                land_area=unit.land_area,
                building_area=unit.building_area,
                rentable_area=unit.rentable_area,
                owner_name="",
                usage_type=unit.usage_type,
                project_name=unit.project_id,
                address="",
            )
            for unit in units
        ]

    @staticmethod
    def _pending_units(facts: _ReportFacts) -> list[tuple[str, str]]:
        view = view_for(facts.scope_version, facts.items, facts.candidates)
        return list(view.pending)

    @staticmethod
    def _compare_with_baseline_row(
        baseline: MonthlyOccupancyReport | None,
        *,
        aggregates: ReportAggregates,
    ) -> list[FieldChange]:
        if baseline is None:
            return []
        return list(
            compare_with_baseline(
                aggregates,
                ReportAggregates(
                    unit_count=baseline.unit_count or 0,
                    rented_unit_count=baseline.rented_unit_count or 0,
                    occupancy_rate=baseline.occupancy_rate,
                    land_area=baseline.land_area or Decimal("0"),
                    building_area=baseline.building_area or Decimal("0"),
                    rentable_area=baseline.rentable_area or Decimal("0"),
                    rented_area=baseline.rented_area or Decimal("0"),
                    scope_version_id=baseline.scope_version_id,
                ),
            )
        )

    async def _baseline_row(
        self,
        db: AsyncSession,
        *,
        operator_party_id: str,
        period: str,
    ) -> MonthlyOccupancyReport | None:
        year, month = int(period[:4]), int(period[5:7])
        previous_period = (
            f"{year - 1}-12" if month == 1 else f"{year}-{month - 1:02d}"
        )
        return await self.repository.get_submitted_report(
            db,
            operator_party_id=operator_party_id,
            period=previous_period,
        )

    async def _current_lines(
        self,
        db: AsyncSession,
        *,
        operator_party_id: str,
        period: str,
    ) -> tuple[CurrentLine, ...]:
        scope_version = await assessment_scope_repository.get_active_version(
            db,
            operator_party_id=operator_party_id,
            year=int(period[:4]),
        )
        if scope_version is None:
            return ()
        items = tuple(
            await assessment_scope_repository.list_items(
                db, version_id=scope_version.id
            )
        )
        candidates = await assessment_scope_repository.list_managed_units(
            db,
            operator_party_id=operator_party_id,
            as_of=_business_today(),
            year=int(period[:4]),
        )
        derived = await derive_report_lines(
            db,
            scope_version=scope_version,
            items=items,
            candidates=candidates,
            period=period,
        )
        return tuple(
            CurrentLine(
                asset_unit_id=line.asset_unit_id,
                owner_name=line.owner_name_snapshot,
                usage_type=line.usage_type_snapshot,
                project_name=line.project_name_snapshot,
                address=line.address_snapshot,
                land_area=line.land_area,
                building_area=line.building_area,
                rentable_area=line.rentable_area,
                rented_area=line.rented_area,
                rented_unit_count=line.rented_unit_count,
                rental_status=line.rental_status,
                terminal_contract_ids=list(line.terminal_contract_ids),
            )
            for line in derived.lines
        )

    async def _require_party(
        self, db: AsyncSession, operator_party_id: str
    ) -> None:
        if not await assessment_scope_repository.party_exists(
            db, party_id=operator_party_id
        ):
            raise ResourceNotFoundError("Party", operator_party_id)

    async def _require_scope_version(
        self,
        db: AsyncSession,
        *,
        operator_party_id: str,
        period: str,
    ) -> AssessmentScopeVersion:
        version = await assessment_scope_repository.get_active_version(
            db,
            operator_party_id=operator_party_id,
            year=int(period[:4]),
        )
        if version is None:
            raise OccupancyReportScopeMissingError(
                operator_party_id=operator_party_id,
                year=int(period[:4]),
            )
        return version

    @staticmethod
    def _validate_period(period: str) -> None:
        import re

        from .occupancy_report_draft_rules import month_end as _month_end

        if re.fullmatch(r"^[0-9]{4}-(0[1-9]|1[0-2])$", period) is None:
            raise OccupancyReportPeriodInvalidError(
                period=period, reason="format"
            )
        if _month_end(period) > _business_today():
            raise OccupancyReportPeriodInvalidError(
                period=period, reason="future"
            )

    def _peek_token(
        self,
        raw_token: str,
        *,
        action: str,
        actor_id: str,
        operator_party_id: str | None,
        period: str | None,
        report_id: str | None = None,
    ) -> dict[str, object]:
        payload = self.preview_store.peek(raw_token)
        if payload is None:
            raise AssetOperationsPreviewStaleError("missing_or_expired")
        if payload.get("actor_id") != actor_id:
            raise AssetOperationsPreviewStaleError("actor_mismatch")
        if payload.get("action") != action:
            raise AssetOperationsPreviewStaleError("action_mismatch")
        if report_id is not None and payload.get("report_id") != report_id:
            raise AssetOperationsPreviewStaleError("target_mismatch")
        if (
            operator_party_id is not None
            and payload.get("operator_party_id") != operator_party_id
        ):
            raise AssetOperationsPreviewStaleError("target_mismatch")
        if period is not None and payload.get("period") != period:
            raise AssetOperationsPreviewStaleError("target_mismatch")
        return payload

    @staticmethod
    def _state_fingerprint(
        *,
        scope_version: AssessmentScopeVersion,
        chain: MonthlyOccupancyReport | None,
        candidates: tuple[AssetUnit, ...],
        derived: DerivedReportFacts,
    ) -> str:
        payload = {
            "scope_version": {
                "id": scope_version.id,
                "version": scope_version.version,
                "status": scope_version.status,
                "version_number": scope_version.version_number,
            },
            "chain": (
                {"id": chain.id, "version": chain.version}
                if chain is not None
                else None
            ),
            "candidates": [
                {
                    "id": unit.id,
                    "version": unit.version,
                    "is_operating": unit.is_operating,
                    "managed_to": (
                        unit.managed_to.isoformat()
                        if unit.managed_to is not None
                        else None
                    ),
                }
                for unit in sorted(candidates, key=lambda row: row.id)
            ],
            "rented_unit_ids": sorted(derived.rented_unit_ids),
            "terminal_contract_map": {
                unit_id: sorted(contract_ids)
                for unit_id, contract_ids in sorted(
                    derived.terminal_contract_map.items()
                )
            },
        }
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @staticmethod
    def _report_fingerprint(report: MonthlyOccupancyReport) -> str:
        payload = {
            "id": report.id,
            "version": report.version,
            "status": report.status,
            "submitted_at": (
                report.submitted_at.isoformat()
                if report.submitted_at is not None
                else None
            ),
            "scope_version_id": report.scope_version_id,
        }
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @staticmethod
    def _request_fingerprint(
        *,
        actor_id: str,
        idempotency_key: str,
        operator_party_id: str,
        period: str,
        request: SubmitOccupancyReportRequest,
    ) -> str:
        payload = {
            "actor_id": actor_id,
            "action": _SUBMIT_ACTION,
            "idempotency_key": idempotency_key,
            "operator_party_id": operator_party_id,
            "period": period,
            "preview_token_hash": hashlib.sha256(
                request.preview_token.encode("utf-8")
            ).hexdigest(),
            "expected_scope_version_id": request.expected_scope_version_id,
            "expected_scope_version": request.expected_scope_version,
        }
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @staticmethod
    def _withdraw_fingerprint(
        *,
        actor_id: str,
        idempotency_key: str,
        report_id: str,
        request: WithdrawOccupancyReportRequest,
    ) -> str:
        payload = {
            "actor_id": actor_id,
            "action": _WITHDRAW_ACTION,
            "idempotency_key": idempotency_key,
            "report_id": report_id,
            "preview_token_hash": hashlib.sha256(
                request.preview_token.encode("utf-8")
            ).hexdigest(),
            "expected_version": request.expected_version,
            "withdraw_reason": request.withdraw_reason.strip(),
        }
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @staticmethod
    async def _get_receipt(
        db: AsyncSession, *, actor_id: str, idempotency_key: str
    ) -> AssetContractWriteReceipt | None:

        return await asset_contract_repository.get_write_receipt(
            db, actor_id=actor_id, idempotency_key=idempotency_key
        )

    @staticmethod
    async def _add_receipt(
        db: AsyncSession,
        *,
        actor_id: str,
        idempotency_key: str,
        request_fingerprint: str,
        result: OccupancyReportSubmitResponse | OccupancyReportWithdrawResponse,
        command_kind: str,
    ) -> None:

        await rent_command_repository.add_receipt(
            db,
            receipt=AssetContractWriteReceipt(  # type: ignore[call-arg]
                id=str(uuid.uuid4()),
                actor_id=actor_id,
                command_kind=command_kind,
                idempotency_key=idempotency_key,
                request_fingerprint=request_fingerprint,
                result_data=result.model_dump(mode="json"),
                created_at=datetime.now(UTC).replace(tzinfo=None),
            ),
        )

    @staticmethod
    async def _add_audit(
        db: AsyncSession,
        *,
        target_id: str,
        action: str,
        actor_id: str,
        before: dict[str, object],
        after: dict[str, object],
        occurred_at: datetime,
        correlation_id: str,
    ) -> None:

        await business_change_repository.add(
            db,
            event=BusinessChangeEvent(  # type: ignore[call-arg]
                id=str(uuid.uuid4()),
                target_type="monthly_occupancy_report",
                target_id=target_id,
                action=action,
                actor_id=actor_id,
                before=before,
                after=after,
                reason=None,
                correlation_id=correlation_id,
                occurred_at=occurred_at,
            ),
        )

    @staticmethod
    def _replay_submit(
        receipt: AssetContractWriteReceipt, *, request_fingerprint: str
    ) -> OccupancyReportSubmitResponse:
        if receipt.request_fingerprint != request_fingerprint:
            raise AssetOperationsIdempotencyConflictError()
        return OccupancyReportSubmitResponse.model_validate(
            {**receipt.result_data, "idempotent": True}
        )

    @staticmethod
    def _replay_withdraw(
        receipt: AssetContractWriteReceipt, *, request_fingerprint: str
    ) -> OccupancyReportWithdrawResponse:
        if receipt.request_fingerprint != request_fingerprint:
            raise AssetOperationsIdempotencyConflictError()
        return OccupancyReportWithdrawResponse.model_validate(
            {**receipt.result_data, "idempotent": True}
        )

    @staticmethod
    def _scope_summary(
        version: AssessmentScopeVersion | None
    ) -> AssessmentScopeVersionSummary | None:
        return summarize_version(version)

    @staticmethod
    def _api_datetime(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @staticmethod
    def _database_datetime(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value
        return value.astimezone(UTC).replace(tzinfo=None)


def _business_today() -> date:
    return datetime.now(UTC).astimezone(_BUSINESS_TIMEZONE).date()


occupancy_report_submission_service = OccupancyReportSubmissionService()


__all__ = [
    "OccupancyReportPreviewStore",
    "OccupancyReportSubmissionService",
    "occupancy_report_submission_service",
]
