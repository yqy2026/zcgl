"""Scoped creation of confirmed v5 signed-contract facts."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Iterable
from datetime import UTC, date, datetime
from typing import Protocol, TypeVar, cast
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.exc import StaleDataError

from ...core.exception_handler import (
    DuplicateResourceError,
    PartyScopeForbiddenError,
    ResourceNotFoundError,
)
from ...crud.asset_contract import (
    asset_contract_repository as default_contract_repository,
)
from ...crud.asset_unit import asset_unit_repository as default_unit_repository
from ...models.asset_contract import (
    AssetContractWriteReceipt,
    ContractLifecycleEvent,
    ContractRentSchedule,
    TerminalContract,
    TerminalContractAssetUnit,
    UpstreamContract,
    UpstreamContractAssetUnit,
)
from ...models.asset_unit import AssetUnit
from ...schemas.asset_operations import (
    ContractRentScheduleInput,
    ContractWarning,
    TerminalContractCreate,
    TerminalContractResponse,
    TerminalContractUpdate,
    UpstreamContractCreate,
    UpstreamContractResponse,
    UpstreamContractUpdate,
)
from ..party_scope_resolver import EffectivePartyScope
from .business_change_service import contract_snapshot, record_contract_change
from .contract_projections import (
    derive_terminal_contract_status,
    derive_terminal_contract_warnings,
    derive_upstream_contract_status,
    public_warning,
)
from .errors import (
    AssetContractCoverageInvalidError,
    AssetOperationsIdempotencyConflictError,
    AssetOperationsVersionConflictError,
    AssetUnitPeriodOverlapError,
    ContractFieldNotApplicableError,
    RentScheduleInvalidError,
    ScanDocumentAlreadyBoundError,
    ScanDocumentRequiredError,
    TerminalContractAlreadyTerminatedError,
    UpstreamContractAlreadyExitedError,
)


class AssetContractWriter(Protocol):
    async def get_write_receipt(
        self, db: AsyncSession, *, actor_id: str, idempotency_key: str
    ) -> AssetContractWriteReceipt | None: ...

    async def get_upstream(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        scope: EffectivePartyScope,
        for_update: bool = False,
    ) -> UpstreamContract | None: ...

    async def get_terminal(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        scope: EffectivePartyScope,
        for_update: bool = False,
    ) -> TerminalContract | None: ...

    async def retarget_upstream_coverage_ends(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        old_end: date,
        new_end: date,
    ) -> int: ...

    async def retarget_terminal_coverage_ends(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        old_end: date,
        new_end: date,
    ) -> int: ...

    async def list_terminal_coverages(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
    ) -> tuple[TerminalContractAssetUnit, ...]: ...

    async def list_rent_schedules(
        self,
        db: AsyncSession,
        *,
        contract_kind: str,
        contract_ids: tuple[str, ...],
    ) -> tuple[ContractRentSchedule, ...]: ...

    async def list_lifecycle_events(
        self,
        db: AsyncSession,
        *,
        contract_kind: str,
        contract_id: str,
    ) -> tuple[ContractLifecycleEvent, ...]: ...

    async def require_contract_attachment(
        self, db: AsyncSession, *, attachment_id: str
    ) -> object | None: ...

    async def bind_contract_attachment(
        self,
        db: AsyncSession,
        *,
        attachment_id: str,
        contract_id: str,
        expected_owner_id: str,
    ) -> bool: ...

    async def get_upstream_for_terminal(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        unit_ids: tuple[str, ...],
        scope: EffectivePartyScope,
    ) -> UpstreamContract | None: ...

    async def list_upstream_coverages(
        self, db: AsyncSession, *, contract_id: str
    ) -> tuple[UpstreamContractAssetUnit, ...]: ...

    async def find_terminal_overlaps(
        self,
        db: AsyncSession,
        *,
        unit_ids: tuple[str, ...],
        start_date: date,
        end_date: date,
    ) -> tuple[str, ...]: ...

    async def add_lifecycle_event(
        self,
        db: AsyncSession,
        *,
        event: ContractLifecycleEvent,
    ) -> None: ...

    async def add_upstream(
        self,
        db: AsyncSession,
        *,
        contract: UpstreamContract,
        coverages: tuple[UpstreamContractAssetUnit, ...],
        schedules: tuple[ContractRentSchedule, ...],
    ) -> None: ...

    async def add_terminal(
        self,
        db: AsyncSession,
        *,
        contract: TerminalContract,
        coverages: tuple[TerminalContractAssetUnit, ...],
        schedules: tuple[ContractRentSchedule, ...],
    ) -> None: ...

    async def add_write_receipt(
        self, db: AsyncSession, *, receipt: AssetContractWriteReceipt
    ) -> None: ...


class AssetUnitWriter(Protocol):
    async def lock_for_write(
        self,
        db: AsyncSession,
        *,
        unit_ids: Iterable[str],
        scope: EffectivePartyScope,
    ) -> tuple[AssetUnit, ...]: ...

    async def get_project_manager_party_ids(
        self,
        db: AsyncSession,
        *,
        project_ids: Iterable[str],
    ) -> dict[str, str | None]: ...


ResponseT = TypeVar("ResponseT", UpstreamContractResponse, TerminalContractResponse)


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _business_today() -> date:
    from zoneinfo import ZoneInfo

    return datetime.now(ZoneInfo("Asia/Shanghai")).date()


class AssetContractCommandService:
    """Write one contract aggregate after scope, coverage and risk validation."""

    def __init__(
        self,
        *,
        repository: AssetContractWriter | None = None,
        unit_repository: AssetUnitWriter | None = None,
        clock: Callable[[], datetime] = _utcnow,
        business_today: Callable[[], date] = _business_today,
        id_factory: Callable[[], str] = lambda: str(uuid4()),
    ) -> None:
        self.repository = repository or default_contract_repository
        self.unit_repository = unit_repository or default_unit_repository
        self.clock = clock
        self.business_today = business_today
        self.id_factory = id_factory

    async def create_upstream(
        self,
        db: AsyncSession,
        *,
        request: UpstreamContractCreate,
        actor_id: str,
        scope: EffectivePartyScope,
        idempotency_key: str,
        attachment_owner_id: str,
        lifecycle_event: ContractLifecycleEvent | None = None,
    ) -> UpstreamContractResponse:
        self._require_effective_scope(scope)
        self._validate_upstream_fields(
            contract_type=request.contract_type,
            management_fee_rate=request.management_fee_rate,
            deposit_amount=request.deposit_amount,
            rent_schedules=request.rent_schedules,
            payment_cycle=request.payment_cycle,
            payment_day=request.payment_day,
        )
        fingerprint = self._fingerprint("create_upstream", request)
        existing = await self.repository.get_write_receipt(
            db, actor_id=actor_id, idempotency_key=idempotency_key
        )
        if existing is not None:
            await self._lock_exact_units(db, request.asset_unit_ids, scope)
            return self._replay(
                existing,
                request_fingerprint=fingerprint,
                response_type=UpstreamContractResponse,
            )

        units = await self._lock_exact_units(db, request.asset_unit_ids, scope)
        existing = await self.repository.get_write_receipt(
            db, actor_id=actor_id, idempotency_key=idempotency_key
        )
        if existing is not None:
            return self._replay(
                existing,
                request_fingerprint=fingerprint,
                response_type=UpstreamContractResponse,
            )
        await self._require_scan(db, request.scan_document_id)
        self._validate_unit_periods(
            units, start_date=request.start_date, end_date=request.end_date
        )
        mismatched_owner_ids = sorted(
            unit.id for unit in units if unit.owner_party_id != request.owner_party_id
        )
        if mismatched_owner_ids:
            raise AssetContractCoverageInvalidError(
                reason="owner_party_mismatch", asset_unit_ids=mismatched_owner_ids
            )
        self._validate_schedules(
            request.rent_schedules,
            contract_start=request.start_date,
            contract_end=request.end_date,
        )

        now = self.clock()
        contract_id = self.id_factory()
        contract = UpstreamContract(  # type: ignore[call-arg]
            id=contract_id,
            contract_number=request.contract_number,
            contract_type=request.contract_type,
            name=request.name,
            owner_party_id=request.owner_party_id,
            operator_party_id=request.operator_party_id,
            start_date=request.start_date,
            end_date=request.end_date,
            payment_cycle=request.payment_cycle,
            payment_day=request.payment_day,
            management_fee_rate=request.management_fee_rate,
            deposit_amount=request.deposit_amount,
            oa_reference=request.oa_reference,
            renewed_from_id=request.renewed_from_id,
            scan_document_id=request.scan_document_id,
            version=1,
            created_at=self._naive_utc(now),
            updated_at=self._naive_utc(now),
        )
        coverages = tuple(
            UpstreamContractAssetUnit(  # type: ignore[call-arg]
                upstream_contract_id=contract_id,
                asset_unit_id=unit_id,
                effective_from=request.start_date,
                effective_to=request.end_date,
            )
            for unit_id in sorted(request.asset_unit_ids)
        )
        schedules = self._schedule_models(
            contract_kind="upstream",
            contract_id=contract_id,
            values=request.rent_schedules,
        )
        response = UpstreamContractResponse.model_validate(
            {
                **request.model_dump(mode="json"),
                "id": contract_id,
                "version": 1,
                "created_at": now,
                "updated_at": now,
                "status": derive_upstream_contract_status(
                    contract,
                    as_of=self.business_today(),
                    lifecycle_events=(),
                ),
                "warnings": [],
                "idempotent": False,
            }
        )
        if lifecycle_event is not None:
            lifecycle_event.successor_contract_id = contract_id
        return await self._persist_upstream(
            db,
            contract=contract,
            coverages=coverages,
            schedules=schedules,
            response=response,
            actor_id=actor_id,
            idempotency_key=idempotency_key,
            request_fingerprint=fingerprint,
            attachment_owner_id=attachment_owner_id,
            lifecycle_event=lifecycle_event,
        )

    async def create_terminal(
        self,
        db: AsyncSession,
        *,
        request: TerminalContractCreate,
        actor_id: str,
        scope: EffectivePartyScope,
        idempotency_key: str,
        attachment_owner_id: str,
        lifecycle_event: ContractLifecycleEvent | None = None,
    ) -> TerminalContractResponse:
        self._require_effective_scope(scope)
        fingerprint = self._fingerprint("create_terminal", request)
        existing = await self.repository.get_write_receipt(
            db, actor_id=actor_id, idempotency_key=idempotency_key
        )
        if existing is not None:
            await self._lock_exact_units(db, request.asset_unit_ids, scope)
            return self._replay(
                existing,
                request_fingerprint=fingerprint,
                response_type=TerminalContractResponse,
            )

        units = await self._lock_exact_units(db, request.asset_unit_ids, scope)
        existing = await self.repository.get_write_receipt(
            db, actor_id=actor_id, idempotency_key=idempotency_key
        )
        if existing is not None:
            return self._replay(
                existing,
                request_fingerprint=fingerprint,
                response_type=TerminalContractResponse,
            )
        await self._require_scan(db, request.scan_document_id)
        self._validate_unit_periods(
            units, start_date=request.start_date, end_date=request.end_date
        )
        self._validate_schedules(
            request.rent_schedules,
            contract_start=request.start_date,
            contract_end=request.end_date,
        )
        unit_ids = tuple(sorted(request.asset_unit_ids))
        overlap_ids = await self.repository.find_terminal_overlaps(
            db,
            unit_ids=unit_ids,
            start_date=request.start_date,
            end_date=request.end_date,
        )
        if overlap_ids:
            raise AssetUnitPeriodOverlapError(
                asset_unit_ids=list(unit_ids),
                terminal_contract_ids=list(overlap_ids),
            )

        upstream = await self._resolve_upstream(
            db,
            request=request,
            scope=scope,
            units=units,
        )
        now = self.clock()
        contract_id = self.id_factory()
        contract = TerminalContract(  # type: ignore[call-arg]
            id=contract_id,
            contract_number=request.contract_number,
            contract_mode=request.contract_mode,
            tenant_party_id=request.tenant_party_id,
            lessor_party_id=request.lessor_party_id,
            upstream_contract_id=request.upstream_contract_id,
            start_date=request.start_date,
            end_date=request.end_date,
            deposit_months=request.deposit_months,
            deposit_amount=request.deposit_amount,
            rent_collector=request.rent_collector,
            renewed_from_id=request.renewed_from_id,
            scan_document_id=request.scan_document_id,
            version=1,
            created_at=self._naive_utc(now),
            updated_at=self._naive_utc(now),
        )
        coverages = tuple(
            TerminalContractAssetUnit(  # type: ignore[call-arg]
                terminal_contract_id=contract_id,
                asset_unit_id=unit_id,
                effective_from=request.start_date,
                effective_to=request.end_date,
            )
            for unit_id in unit_ids
        )
        schedules = self._schedule_models(
            contract_kind="terminal",
            contract_id=contract_id,
            values=request.rent_schedules,
        )
        warnings = [
            self._warning(code)
            for code in derive_terminal_contract_warnings(contract, upstream=upstream)
        ]
        response = TerminalContractResponse.model_validate(
            {
                **request.model_dump(mode="json"),
                "id": contract_id,
                "version": 1,
                "created_at": now,
                "updated_at": now,
                "status": derive_terminal_contract_status(
                    contract,
                    as_of=self.business_today(),
                    lifecycle_events=(),
                ),
                "warnings": warnings,
                "idempotent": False,
            }
        )
        if lifecycle_event is not None:
            lifecycle_event.successor_contract_id = contract_id
        return await self._persist_terminal(
            db,
            contract=contract,
            coverages=coverages,
            schedules=schedules,
            response=response,
            actor_id=actor_id,
            idempotency_key=idempotency_key,
            request_fingerprint=fingerprint,
            attachment_owner_id=attachment_owner_id,
            lifecycle_event=lifecycle_event,
        )

    async def update_upstream(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        request: UpstreamContractUpdate,
        actor_id: str,
        scope: EffectivePartyScope,
    ) -> UpstreamContractResponse:
        """Apply editable-term changes under optimistic locking."""
        self._require_effective_scope(scope)
        contract = await self.repository.get_upstream(
            db,
            contract_id=contract_id,
            scope=scope,
            for_update=True,
        )
        if contract is None:
            raise ResourceNotFoundError("UpstreamContract", contract_id)
        if contract.version != request.expected_version:
            raise AssetOperationsVersionConflictError(
                unit_id=contract_id,
                expected_version=request.expected_version,
                actual_version=contract.version,
            )
        events = await self.repository.list_lifecycle_events(
            db,
            contract_kind="upstream",
            contract_id=contract_id,
        )
        active_exit = self._active_exit(events)
        if active_exit is not None:
            raise UpstreamContractAlreadyExitedError(event_id=active_exit.id)
        upstream_coverages = await self.repository.list_upstream_coverages(
            db,
            contract_id=contract_id,
        )
        if request.end_date is not None and request.end_date < contract.start_date:
            raise AssetContractCoverageInvalidError(
                reason="end_date_before_start",
                asset_unit_ids=[],
            )
        before = contract_snapshot(contract)
        old_end = contract.end_date
        if (
            contract.contract_type == "lease"
            and "management_fee_rate" in request.model_fields_set
        ):
            raise ContractFieldNotApplicableError(
                contract_type=contract.contract_type,
                field_names=["management_fee_rate"],
            )
        self._validate_upstream_fields(
            contract_type=contract.contract_type,
            management_fee_rate=request.management_fee_rate,
            deposit_amount=request.deposit_amount,
        )
        for field in (
            "name",
            "end_date",
            "management_fee_rate",
            "deposit_amount",
            "oa_reference",
        ):
            value = getattr(request, field)
            if value is not None:
                setattr(contract, field, value)
        try:
            if request.end_date is not None and request.end_date != old_end:
                units = await self._lock_exact_units(
                    db,
                    sorted({coverage.asset_unit_id for coverage in upstream_coverages}),
                    scope,
                )
                units_by_id = {unit.id: unit for unit in units}
                for coverage in upstream_coverages:
                    if coverage.effective_to == old_end:
                        self._validate_unit_periods(
                            (units_by_id[coverage.asset_unit_id],),
                            start_date=coverage.effective_from,
                            end_date=request.end_date,
                        )
                await self.repository.retarget_upstream_coverage_ends(
                    db,
                    contract_id=contract_id,
                    old_end=old_end,
                    new_end=request.end_date,
                )
            await db.flush()
            await record_contract_change(
                db,
                contract=contract,
                contract_kind="upstream",
                action="updated",
                actor_id=actor_id,
                before=before,
                occurred_at=self.clock(),
            )
            await db.flush()
            await db.commit()
        except StaleDataError as exc:
            await db.rollback()
            raise AssetOperationsVersionConflictError(
                unit_id=contract_id,
                expected_version=request.expected_version,
                actual_version=None,
            ) from exc
        except Exception:
            await db.rollback()
            raise
        upstream_schedules = await self.repository.list_rent_schedules(
            db,
            contract_kind="upstream",
            contract_ids=(contract_id,),
        )
        return UpstreamContractResponse.model_validate(
            {
                "id": contract.id,
                "contract_number": contract.contract_number,
                "contract_type": contract.contract_type,
                "name": contract.name,
                "owner_party_id": contract.owner_party_id,
                "operator_party_id": contract.operator_party_id,
                "start_date": contract.start_date,
                "end_date": contract.end_date,
                "payment_cycle": contract.payment_cycle,
                "payment_day": contract.payment_day,
                "management_fee_rate": contract.management_fee_rate,
                "deposit_amount": contract.deposit_amount,
                "oa_reference": contract.oa_reference,
                "renewed_from_id": contract.renewed_from_id,
                "scan_document_id": contract.scan_document_id,
                "asset_unit_ids": sorted(
                    {coverage.asset_unit_id for coverage in upstream_coverages}
                ),
                "rent_schedules": [
                    {
                        "stage_start": schedule.stage_start,
                        "stage_end": schedule.stage_end,
                        "base_monthly_rent": schedule.base_monthly_rent,
                        "increase_rate": schedule.increase_rate,
                        "free_rent_months": schedule.free_rent_months,
                        "discount_amount": schedule.discount_amount,
                        "actual_monthly_rent": schedule.actual_monthly_rent,
                        "payment_cycle": schedule.payment_cycle,
                        "due_day": schedule.due_day,
                    }
                    for schedule in upstream_schedules
                ],
                "version": contract.version,
                "created_at": contract.created_at,
                "updated_at": contract.updated_at,
                "status": derive_upstream_contract_status(
                    contract,
                    as_of=self.business_today(),
                    lifecycle_events=events,
                ),
                "warnings": [],
                "idempotent": False,
            }
        )

    async def update_terminal(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        request: TerminalContractUpdate,
        actor_id: str,
        scope: EffectivePartyScope,
    ) -> TerminalContractResponse:
        """Apply editable-term changes and recompute derived risks."""
        self._require_effective_scope(scope)
        contract = await self.repository.get_terminal(
            db,
            contract_id=contract_id,
            scope=scope,
            for_update=True,
        )
        if contract is None:
            raise ResourceNotFoundError("TerminalContract", contract_id)
        if contract.version != request.expected_version:
            raise AssetOperationsVersionConflictError(
                unit_id=contract_id,
                expected_version=request.expected_version,
                actual_version=contract.version,
            )
        before = contract_snapshot(contract)
        events = await self.repository.list_lifecycle_events(
            db,
            contract_kind="terminal",
            contract_id=contract_id,
        )
        active_termination = self._active_termination(events)
        if active_termination is not None:
            raise TerminalContractAlreadyTerminatedError(event_id=active_termination.id)
        terminal_coverages = await self.repository.list_terminal_coverages(
            db,
            contract_id=contract_id,
        )
        if request.end_date is not None and request.end_date < contract.start_date:
            raise AssetContractCoverageInvalidError(
                reason="end_date_before_start",
                asset_unit_ids=[],
            )
        upstream: UpstreamContract | None = None
        old_end = contract.end_date
        for field in ("deposit_months", "deposit_amount"):
            value = getattr(request, field)
            if value is not None:
                setattr(contract, field, value)
        extends = request.end_date is not None and request.end_date != old_end
        new_end = request.end_date if request.end_date is not None else old_end
        if extends:
            contract.end_date = new_end
        try:
            if request.upstream_contract_id is not None:
                upstream = await self._validate_upstream_link(
                    db,
                    upstream_contract_id=request.upstream_contract_id,
                    scope=scope,
                    contract_mode=contract.contract_mode,
                    lessor_party_id=contract.lessor_party_id,
                    start_date=contract.start_date,
                    asset_unit_ids=tuple(
                        sorted(
                            {coverage.asset_unit_id for coverage in terminal_coverages}
                        )
                    ),
                )
                contract.upstream_contract_id = request.upstream_contract_id
            if extends:
                units = await self._lock_exact_units(
                    db,
                    sorted({coverage.asset_unit_id for coverage in terminal_coverages}),
                    scope,
                )
                units_by_id = {unit.id: unit for unit in units}
                for coverage in terminal_coverages:
                    if coverage.effective_to == old_end:
                        self._validate_unit_periods(
                            (units_by_id[coverage.asset_unit_id],),
                            start_date=coverage.effective_from,
                            end_date=new_end,
                        )
                await self.repository.retarget_terminal_coverage_ends(
                    db,
                    contract_id=contract_id,
                    old_end=old_end,
                    new_end=new_end,
                )
            await db.flush()
            await record_contract_change(
                db,
                contract=contract,
                contract_kind="terminal",
                action="updated",
                actor_id=actor_id,
                before=before,
                occurred_at=self.clock(),
            )
            await db.flush()
            await db.commit()
        except StaleDataError as exc:
            await db.rollback()
            raise AssetOperationsVersionConflictError(
                unit_id=contract_id,
                expected_version=request.expected_version,
                actual_version=None,
            ) from exc
        except IntegrityError as exc:
            await db.rollback()
            if self._constraint_name(exc) == (
                "ex_terminal_contract_asset_units_unit_period"
            ):
                raise AssetContractCoverageInvalidError(
                    reason="coverage_overlap_after_extension",
                    asset_unit_ids=[],
                ) from exc
            raise
        except Exception:
            await db.rollback()
            raise
        if upstream is None and contract.upstream_contract_id is not None:
            upstream = await self.repository.get_upstream(
                db,
                contract_id=contract.upstream_contract_id,
                scope=scope,
            )
        terminal_schedules = await self.repository.list_rent_schedules(
            db,
            contract_kind="terminal",
            contract_ids=(contract_id,),
        )
        warning_codes = derive_terminal_contract_warnings(
            contract,
            upstream=upstream,
        )
        return TerminalContractResponse.model_validate(
            {
                "id": contract.id,
                "contract_number": contract.contract_number,
                "contract_mode": contract.contract_mode,
                "tenant_party_id": contract.tenant_party_id,
                "lessor_party_id": contract.lessor_party_id,
                "upstream_contract_id": contract.upstream_contract_id,
                "start_date": contract.start_date,
                "end_date": contract.end_date,
                "deposit_months": contract.deposit_months,
                "deposit_amount": contract.deposit_amount,
                "rent_collector": contract.rent_collector,
                "renewed_from_id": contract.renewed_from_id,
                "scan_document_id": contract.scan_document_id,
                "asset_unit_ids": sorted(
                    {coverage.asset_unit_id for coverage in terminal_coverages}
                ),
                "rent_schedules": [
                    {
                        "stage_start": schedule.stage_start,
                        "stage_end": schedule.stage_end,
                        "base_monthly_rent": schedule.base_monthly_rent,
                        "increase_rate": schedule.increase_rate,
                        "free_rent_months": schedule.free_rent_months,
                        "discount_amount": schedule.discount_amount,
                        "actual_monthly_rent": schedule.actual_monthly_rent,
                        "payment_cycle": schedule.payment_cycle,
                        "due_day": schedule.due_day,
                    }
                    for schedule in terminal_schedules
                ],
                "version": contract.version,
                "created_at": contract.created_at,
                "updated_at": contract.updated_at,
                "status": derive_terminal_contract_status(
                    contract,
                    as_of=self.business_today(),
                    lifecycle_events=events,
                ),
                "warnings": [self._warning(code) for code in warning_codes],
                "idempotent": False,
            }
        )

    async def _resolve_upstream(
        self,
        db: AsyncSession,
        *,
        request: TerminalContractCreate,
        scope: EffectivePartyScope,
        units: tuple[AssetUnit, ...],
    ) -> UpstreamContract | None:
        contract_id = request.upstream_contract_id
        if contract_id is None:
            await self._validate_unlinked_lessor(db, request=request, units=units)
            return None
        return await self._validate_upstream_link(
            db,
            upstream_contract_id=contract_id,
            scope=scope,
            contract_mode=request.contract_mode,
            lessor_party_id=request.lessor_party_id,
            start_date=request.start_date,
            asset_unit_ids=tuple(sorted(request.asset_unit_ids)),
        )

    async def _validate_upstream_link(
        self,
        db: AsyncSession,
        *,
        upstream_contract_id: str,
        scope: EffectivePartyScope,
        contract_mode: str,
        lessor_party_id: str,
        start_date: date,
        asset_unit_ids: tuple[str, ...],
    ) -> UpstreamContract:
        upstream = await self.repository.get_upstream_for_terminal(
            db,
            contract_id=upstream_contract_id,
            unit_ids=asset_unit_ids,
            scope=scope,
        )
        if upstream is None:
            raise ResourceNotFoundError("UpstreamContract", upstream_contract_id)
        expected_type = (
            "lease" if contract_mode == "sublease" else "management_agreement"
        )
        if upstream.contract_type != expected_type:
            raise AssetContractCoverageInvalidError(
                reason="upstream_type_mismatch",
                asset_unit_ids=sorted(asset_unit_ids),
            )
        expected_lessor = (
            upstream.operator_party_id
            if contract_mode == "sublease"
            else upstream.owner_party_id
        )
        if lessor_party_id != expected_lessor:
            raise AssetContractCoverageInvalidError(
                reason="lessor_party_mismatch",
                asset_unit_ids=sorted(asset_unit_ids),
            )
        coverages = await self.repository.list_upstream_coverages(
            db, contract_id=upstream_contract_id
        )
        active_unit_ids = {
            coverage.asset_unit_id
            for coverage in coverages
            if coverage.effective_from <= start_date
            and (coverage.effective_to is None or coverage.effective_to >= start_date)
        }
        missing_ids = sorted(set(asset_unit_ids) - active_unit_ids)
        if missing_ids:
            raise AssetContractCoverageInvalidError(
                reason="upstream_does_not_cover_terminal_start",
                asset_unit_ids=missing_ids,
            )
        return upstream

    async def _validate_unlinked_lessor(
        self,
        db: AsyncSession,
        *,
        request: TerminalContractCreate,
        units: tuple[AssetUnit, ...],
    ) -> None:
        if request.contract_mode == "direct_lease":
            expected_lessor_ids = {unit.owner_party_id for unit in units}
        else:
            project_ids = tuple(sorted({unit.project_id for unit in units}))
            managers = await self.unit_repository.get_project_manager_party_ids(
                db,
                project_ids=project_ids,
            )
            expected_lessor_ids = {
                manager_party_id
                for manager_party_id in managers.values()
                if manager_party_id is not None
            }
            if len(managers) != len(project_ids) or any(
                managers.get(project_id) is None for project_id in project_ids
            ):
                expected_lessor_ids = set()

        if (
            len(expected_lessor_ids) != 1
            or request.lessor_party_id not in expected_lessor_ids
        ):
            raise AssetContractCoverageInvalidError(
                reason="lessor_party_mismatch",
                asset_unit_ids=sorted(request.asset_unit_ids),
            )

    async def _lock_exact_units(
        self,
        db: AsyncSession,
        unit_ids: list[str],
        scope: EffectivePartyScope,
    ) -> tuple[AssetUnit, ...]:
        normalized_ids = tuple(sorted(unit_ids))
        units = await self.unit_repository.lock_for_write(
            db, unit_ids=normalized_ids, scope=scope
        )
        if tuple(sorted(unit.id for unit in units)) != normalized_ids:
            raise ResourceNotFoundError(
                "AssetUnit", details={"asset_unit_ids": list(normalized_ids)}
            )
        return units

    async def _require_scan(self, db: AsyncSession, attachment_id: str) -> None:
        attachment = await self.repository.require_contract_attachment(
            db, attachment_id=attachment_id
        )
        if attachment is None:
            raise ScanDocumentRequiredError(attachment_id=attachment_id)

    @staticmethod
    def _validate_unit_periods(
        units: tuple[AssetUnit, ...], *, start_date: date, end_date: date
    ) -> None:
        invalid_ids = sorted(
            unit.id
            for unit in units
            if start_date < unit.managed_from
            or (unit.managed_to is not None and end_date > unit.managed_to)
        )
        if invalid_ids:
            raise AssetContractCoverageInvalidError(
                reason="outside_asset_unit_managed_period",
                asset_unit_ids=invalid_ids,
            )

    @staticmethod
    def _validate_upstream_fields(
        *,
        contract_type: str,
        management_fee_rate: object = None,
        deposit_amount: object = None,
        rent_schedules: list[ContractRentScheduleInput] | None = None,
        payment_cycle: object = None,
        payment_day: object = None,
    ) -> None:
        invalid: list[str] = []
        if contract_type == "lease":
            if management_fee_rate is not None:
                invalid.append("management_fee_rate")
        else:
            if deposit_amount is not None and deposit_amount != 0:
                invalid.append("deposit_amount")
            if rent_schedules:
                invalid.append("rent_schedules")
            if payment_cycle is not None:
                invalid.append("payment_cycle")
            if payment_day is not None:
                invalid.append("payment_day")
        if invalid:
            raise ContractFieldNotApplicableError(
                contract_type=contract_type, field_names=invalid
            )

    @staticmethod
    def _validate_schedules(
        schedules: list[ContractRentScheduleInput],
        *,
        contract_start: date,
        contract_end: date,
    ) -> None:
        ordered = sorted(schedules, key=lambda item: (item.stage_start, item.stage_end))
        previous_end: date | None = None
        for item in ordered:
            if item.stage_start < contract_start or item.stage_end > contract_end:
                raise RentScheduleInvalidError(
                    reason="rent_schedule_outside_contract_period"
                )
            if previous_end is not None and item.stage_start <= previous_end:
                raise RentScheduleInvalidError(reason="rent_schedule_overlap")
            previous_end = item.stage_end

    @staticmethod
    def _schedule_models(
        *,
        contract_kind: str,
        contract_id: str,
        values: list[ContractRentScheduleInput],
    ) -> tuple[ContractRentSchedule, ...]:
        return tuple(
            ContractRentSchedule(  # type: ignore[call-arg]
                contract_kind=contract_kind,
                contract_id=contract_id,
                **item.model_dump(),
            )
            for item in sorted(values, key=lambda value: value.stage_start)
        )

    async def _persist_upstream(
        self,
        db: AsyncSession,
        *,
        contract: UpstreamContract,
        coverages: tuple[UpstreamContractAssetUnit, ...],
        schedules: tuple[ContractRentSchedule, ...],
        response: UpstreamContractResponse,
        actor_id: str,
        idempotency_key: str,
        request_fingerprint: str,
        attachment_owner_id: str,
        lifecycle_event: ContractLifecycleEvent | None = None,
    ) -> UpstreamContractResponse:
        try:
            await self.repository.add_upstream(
                db, contract=contract, coverages=coverages, schedules=schedules
            )
            bound = await self.repository.bind_contract_attachment(
                db,
                attachment_id=contract.scan_document_id,
                contract_id=contract.id,
                expected_owner_id=attachment_owner_id,
            )
            if not bound:
                raise ScanDocumentAlreadyBoundError(
                    attachment_id=contract.scan_document_id
                )
            if lifecycle_event is not None:
                await self.repository.add_lifecycle_event(db, event=lifecycle_event)
            await self._record_confirmation(
                db,
                contract=contract,
                contract_kind="upstream",
                actor_id=actor_id,
                lifecycle_event=lifecycle_event,
            )
            await self._add_receipt(
                db,
                command_kind="create_upstream",
                response=response,
                actor_id=actor_id,
                idempotency_key=idempotency_key,
                request_fingerprint=request_fingerprint,
            )
            await db.commit()
            return response
        except IntegrityError as exc:
            await db.rollback()
            return await self._raise_integrity_error(
                db,
                exc=exc,
                actor_id=actor_id,
                idempotency_key=idempotency_key,
                request_fingerprint=request_fingerprint,
                response_type=UpstreamContractResponse,
                contract_number=contract.contract_number,
            )
        except Exception:
            await db.rollback()
            raise

    async def _persist_terminal(
        self,
        db: AsyncSession,
        *,
        contract: TerminalContract,
        coverages: tuple[TerminalContractAssetUnit, ...],
        schedules: tuple[ContractRentSchedule, ...],
        response: TerminalContractResponse,
        actor_id: str,
        idempotency_key: str,
        request_fingerprint: str,
        attachment_owner_id: str,
        lifecycle_event: ContractLifecycleEvent | None = None,
    ) -> TerminalContractResponse:
        try:
            await self.repository.add_terminal(
                db, contract=contract, coverages=coverages, schedules=schedules
            )
            bound = await self.repository.bind_contract_attachment(
                db,
                attachment_id=contract.scan_document_id,
                contract_id=contract.id,
                expected_owner_id=attachment_owner_id,
            )
            if not bound:
                raise ScanDocumentAlreadyBoundError(
                    attachment_id=contract.scan_document_id
                )
            if lifecycle_event is not None:
                await self.repository.add_lifecycle_event(db, event=lifecycle_event)
            await self._record_confirmation(
                db,
                contract=contract,
                contract_kind="terminal",
                actor_id=actor_id,
                lifecycle_event=lifecycle_event,
            )
            await self._add_receipt(
                db,
                command_kind="create_terminal",
                response=response,
                actor_id=actor_id,
                idempotency_key=idempotency_key,
                request_fingerprint=request_fingerprint,
            )
            await db.commit()
            return response
        except IntegrityError as exc:
            await db.rollback()
            constraint_name = self._constraint_name(exc)
            if constraint_name == "ex_terminal_contract_asset_units_unit_period":
                overlap_ids = await self.repository.find_terminal_overlaps(
                    db,
                    unit_ids=tuple(sorted(response.asset_unit_ids)),
                    start_date=response.start_date,
                    end_date=response.end_date,
                )
                raise AssetUnitPeriodOverlapError(
                    asset_unit_ids=sorted(response.asset_unit_ids),
                    terminal_contract_ids=list(overlap_ids),
                ) from exc
            return await self._raise_integrity_error(
                db,
                exc=exc,
                actor_id=actor_id,
                idempotency_key=idempotency_key,
                request_fingerprint=request_fingerprint,
                response_type=TerminalContractResponse,
                contract_number=contract.contract_number,
            )
        except Exception:
            await db.rollback()
            raise

    async def _record_confirmation(
        self,
        db: AsyncSession,
        *,
        contract: UpstreamContract | TerminalContract,
        contract_kind: str,
        actor_id: str,
        lifecycle_event: ContractLifecycleEvent | None,
    ) -> None:
        correlation_id = str(uuid4())
        await record_contract_change(
            db,
            contract=contract,
            contract_kind=contract_kind,
            action="confirmed",
            actor_id=actor_id,
            correlation_id=correlation_id,
            occurred_at=self.clock(),
        )
        if lifecycle_event is not None:
            await record_contract_change(
                db,
                contract=contract,
                target_id=lifecycle_event.contract_id,
                contract_kind=contract_kind,
                action="renewed",
                actor_id=actor_id,
                before={"successor_contract_id": None},
                after={
                    "successor_contract_id": contract.id,
                    "lifecycle_event_id": lifecycle_event.id,
                },
                correlation_id=correlation_id,
                occurred_at=self.clock(),
            )

    async def _add_receipt(
        self,
        db: AsyncSession,
        *,
        command_kind: str,
        response: UpstreamContractResponse | TerminalContractResponse,
        actor_id: str,
        idempotency_key: str,
        request_fingerprint: str,
    ) -> None:
        await self.repository.add_write_receipt(
            db,
            receipt=AssetContractWriteReceipt(  # type: ignore[call-arg]
                id=self.id_factory(),
                actor_id=actor_id,
                command_kind=command_kind,
                idempotency_key=idempotency_key,
                request_fingerprint=request_fingerprint,
                result_data=response.model_dump(mode="json"),
                created_at=self._naive_utc(self.clock()),
            ),
        )

    async def _raise_integrity_error(
        self,
        db: AsyncSession,
        *,
        exc: IntegrityError,
        actor_id: str,
        idempotency_key: str,
        request_fingerprint: str,
        response_type: type[ResponseT],
        contract_number: str,
    ) -> ResponseT:
        constraint_name = self._constraint_name(exc)
        if constraint_name == "uq_asset_contract_write_receipts_actor_request":
            receipt = await self.repository.get_write_receipt(
                db, actor_id=actor_id, idempotency_key=idempotency_key
            )
            if receipt is not None:
                return self._replay(
                    receipt,
                    request_fingerprint=request_fingerprint,
                    response_type=response_type,
                )
        if constraint_name in {
            "uq_upstream_contracts_contract_number",
            "uq_terminal_contracts_contract_number",
        }:
            raise DuplicateResourceError(
                "Contract", "contract_number", contract_number
            ) from exc
        raise exc

    @staticmethod
    def _constraint_name(exc: IntegrityError) -> str | None:
        diagnostics = getattr(exc.orig, "diag", None)
        name = getattr(diagnostics, "constraint_name", None)
        if isinstance(name, str) and name != "":
            return name
        match = re.search(r"((?:ex|uq|ck|fk)_[a-z0-9_]+)", str(exc.orig))
        return match.group(1) if match else None

    @staticmethod
    def _fingerprint(
        command_kind: str,
        request: UpstreamContractCreate | TerminalContractCreate,
    ) -> str:
        data = request.model_dump(mode="json")
        data["asset_unit_ids"] = sorted(data["asset_unit_ids"])
        schedules = cast(list[dict[str, object]], data["rent_schedules"])
        data["rent_schedules"] = sorted(
            schedules,
            key=lambda item: (str(item["stage_start"]), str(item["stage_end"])),
        )
        encoded = json.dumps(
            {"command_kind": command_kind, "request": data},
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _replay(
        receipt: AssetContractWriteReceipt,
        *,
        request_fingerprint: str,
        response_type: type[ResponseT],
    ) -> ResponseT:
        if receipt.request_fingerprint != request_fingerprint:
            raise AssetOperationsIdempotencyConflictError()
        return response_type.model_validate({**receipt.result_data, "idempotent": True})

    @staticmethod
    def _warning(code: str) -> ContractWarning:
        return public_warning(code)

    @staticmethod
    def _active_termination(
        events: tuple[ContractLifecycleEvent, ...],
    ) -> ContractLifecycleEvent | None:
        reversed_event_ids = {
            event.reversed_event_id
            for event in events
            if event.event_type == "reversed" and event.reversed_event_id is not None
        }
        for event in events:
            if event.event_type == "terminated" and event.id not in reversed_event_ids:
                return event
        return None

    @staticmethod
    def _active_exit(
        events: tuple[ContractLifecycleEvent, ...],
    ) -> ContractLifecycleEvent | None:
        reversed_event_ids = {
            event.reversed_event_id
            for event in events
            if event.event_type == "reversed" and event.reversed_event_id is not None
        }
        for event in events:
            if event.event_type == "exited" and event.id not in reversed_event_ids:
                return event
        return None

    @staticmethod
    def _require_effective_scope(scope: EffectivePartyScope) -> None:
        if scope.scope_mode == "unrestricted":
            return
        has_required_axis = (
            scope.scope_mode == "owner"
            and len(scope.owner_party_ids) > 0
            or scope.scope_mode == "manager"
            and len(scope.manager_party_ids) > 0
            or scope.scope_mode == "all"
            and len(scope.effective_party_ids) > 0
        )
        if scope.error_code is not None or not has_required_axis:
            raise PartyScopeForbiddenError(
                code=scope.error_code or "PARTY_SCOPE_MISSING"
            )

    @staticmethod
    def _naive_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value
        return value.astimezone(UTC).replace(tzinfo=None)


asset_contract_command_service = AssetContractCommandService()


__all__ = [
    "AssetContractCommandService",
    "asset_contract_command_service",
]
