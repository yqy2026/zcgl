"""Scoped query interface for asset-operations v5."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Protocol
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exception_handler import PartyScopeForbiddenError
from ...crud.asset_contract import (
    asset_contract_repository as default_asset_contract_repository,
)
from ...crud.asset_unit import asset_unit_repository as default_asset_unit_repository
from ...models.asset_contract import (
    ContractLifecycleEvent,
    ContractRentSchedule,
    TerminalContract,
    TerminalContractAssetUnit,
    UpstreamContract,
    UpstreamContractAssetUnit,
)
from ...models.asset_unit import AssetUnit
from ...schemas.asset_operations import (
    AssetUnitDetail,
    ContractCoverageItem,
    LifecycleEventItem,
    RenewalChainItem,
    RentScheduleItem,
    TerminalContractDetail,
    UpstreamContractDetail,
)
from ..party_scope_resolver import EffectivePartyScope
from .contract_projections import (
    derive_terminal_contract_status,
    derive_terminal_contract_warnings,
    derive_upstream_contract_status,
    public_warning,
)


def _business_today() -> date:
    return datetime.now(UTC).astimezone(ZoneInfo("Asia/Shanghai")).date()


class AssetUnitReader(Protocol):
    async def list(
        self,
        db: AsyncSession,
        *,
        scope: EffectivePartyScope,
        project_id: str | None = None,
        owner_party_id: str | None = None,
        usage_type: str | None = None,
        query: str | None = None,
        non_rentable_only: bool = False,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[AssetUnit], int]: ...

    async def get(
        self,
        db: AsyncSession,
        *,
        unit_id: str,
        scope: EffectivePartyScope,
        for_update: bool = False,
    ) -> AssetUnit | None: ...


class AssetContractReader(Protocol):
    async def list_upstream(
        self,
        db: AsyncSession,
        *,
        scope: EffectivePartyScope,
        contract_type: str | None = None,
        owner_party_id: str | None = None,
        query: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[UpstreamContract], int]: ...

    async def get_upstream(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        scope: EffectivePartyScope,
        for_update: bool = False,
    ) -> UpstreamContract | None: ...

    async def get_upstreams_by_ids(
        self,
        db: AsyncSession,
        *,
        contract_ids: tuple[str, ...],
        scope: EffectivePartyScope,
    ) -> tuple[UpstreamContract, ...]: ...

    async def list_terminal(
        self,
        db: AsyncSession,
        *,
        scope: EffectivePartyScope,
        contract_mode: str | None = None,
        upstream_contract_id: str | None = None,
        query: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[TerminalContract], int]: ...

    async def get_terminal(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        scope: EffectivePartyScope,
        for_update: bool = False,
    ) -> TerminalContract | None: ...

    async def find_terminal_overlaps(
        self,
        db: AsyncSession,
        *,
        unit_ids: tuple[str, ...],
        start_date: date,
        end_date: date,
    ) -> tuple[str, ...]: ...

    async def list_rented_unit_ids(
        self,
        db: AsyncSession,
        *,
        as_of: date,
        scope: EffectivePartyScope,
    ) -> set[str]: ...

    async def list_lifecycle_events_by_contract_ids(
        self,
        db: AsyncSession,
        *,
        contract_kind: str,
        contract_ids: tuple[str, ...],
    ) -> tuple[ContractLifecycleEvent, ...]: ...

    async def list_rent_schedules(
        self,
        db: AsyncSession,
        *,
        contract_kind: str,
        contract_ids: tuple[str, ...],
    ) -> tuple[ContractRentSchedule, ...]: ...

    async def list_upstream_coverages(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
    ) -> tuple[UpstreamContractAssetUnit, ...]: ...

    async def list_terminal_coverages(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
    ) -> tuple[TerminalContractAssetUnit, ...]: ...

    async def list_terminal_by_upstream(
        self,
        db: AsyncSession,
        *,
        upstream_contract_id: str,
    ) -> tuple[TerminalContract, ...]: ...


class AssetOperationsQueryService:
    """Expose scoped reads while hiding range validation and persistence."""

    def __init__(
        self,
        *,
        asset_unit_repository: AssetUnitReader | None = None,
        asset_contract_repository: AssetContractReader | None = None,
        business_today: Callable[[], date] = _business_today,
    ) -> None:
        self.asset_unit_repository = (
            asset_unit_repository or default_asset_unit_repository
        )
        self.asset_contract_repository = (
            asset_contract_repository or default_asset_contract_repository
        )
        self.business_today = business_today

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

    async def list_asset_units(
        self,
        db: AsyncSession,
        *,
        scope: EffectivePartyScope,
        project_id: str | None = None,
        owner_party_id: str | None = None,
        usage_type: str | None = None,
        query: str | None = None,
        filter: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[AssetUnitDetail], int]:
        self._require_effective_scope(scope)
        units, total = await self.asset_unit_repository.list(
            db,
            scope=scope,
            project_id=project_id,
            owner_party_id=owner_party_id,
            usage_type=usage_type,
            query=query,
            non_rentable_only=filter == "non_rentable",
            offset=offset,
            limit=limit,
        )
        rented_ids = await self.asset_contract_repository.list_rented_unit_ids(
            db,
            as_of=self.business_today(),
            scope=scope,
        )
        items = [
            self._unit_detail(unit, rented=unit.id in rented_ids)
            for unit in units
        ]
        return items, total

    async def get_asset_unit_detail(
        self,
        db: AsyncSession,
        unit_id: str,
        *,
        scope: EffectivePartyScope,
    ) -> AssetUnitDetail | None:
        self._require_effective_scope(scope)
        unit = await self.asset_unit_repository.get(
            db,
            unit_id=unit_id,
            scope=scope,
        )
        if unit is None:
            return None
        today = self.business_today()
        rented_ids = await self.asset_contract_repository.list_rented_unit_ids(
            db,
            as_of=today,
            scope=scope,
        )
        contract_ids = sorted(
            await self.asset_contract_repository.find_terminal_overlaps(
                db,
                unit_ids=(unit.id,),
                start_date=today,
                end_date=today,
            )
        )
        detail = self._unit_detail(unit, rented=unit.id in rented_ids)
        return detail.model_copy(update={"terminal_contract_ids": contract_ids})

    @staticmethod
    def _unit_detail(unit: AssetUnit, *, rented: bool) -> AssetUnitDetail:
        rentable = unit.rentable_area
        if not unit.is_operating or rentable <= 0:
            status = "non_rentable"
        elif rented:
            status = "rented"
        else:
            status = "vacant"
        rented_area = rentable if status == "rented" else Decimal("0")
        occupancy = (
            rented_area / rentable if rentable > 0 else Decimal("0")
        )
        return AssetUnitDetail.model_validate(
            {
                **{
                    field: getattr(unit, field)
                    for field in (
                        "id",
                        "unit_code",
                        "name",
                        "project_id",
                        "owner_party_id",
                        "address",
                        "usage_type",
                        "acquisition_mode",
                        "is_operating",
                        "land_area",
                        "building_area",
                        "rentable_area",
                        "managed_from",
                        "managed_to",
                        "vacancy_reason",
                        "expected_lease_start",
                        "predecessor_unit_ids",
                        "version",
                        "created_at",
                        "updated_at",
                    )
                },
                "rental_status": status,
                "rented_area": rented_area,
                "occupancy_rate": occupancy,
                "warnings": [],
            }
        )

    async def get_asset_unit(
        self,
        db: AsyncSession,
        *,
        unit_id: str,
        scope: EffectivePartyScope,
        for_update: bool = False,
    ) -> AssetUnit | None:
        self._require_effective_scope(scope)
        return await self.asset_unit_repository.get(
            db,
            unit_id=unit_id,
            scope=scope,
            for_update=for_update,
        )

    async def list_upstream_contracts(
        self,
        db: AsyncSession,
        *,
        scope: EffectivePartyScope,
        contract_type: str | None = None,
        owner_party_id: str | None = None,
        query: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[UpstreamContractDetail], int]:
        self._require_effective_scope(scope)
        contracts, total = await self.asset_contract_repository.list_upstream(
            db,
            scope=scope,
            contract_type=contract_type,
            owner_party_id=owner_party_id,
            query=query,
            offset=offset,
            limit=limit,
        )
        events_by_id = await self._events_by_contract(
            db, contract_kind="upstream", contracts=contracts
        )
        today = self.business_today()
        items = [
            self._upstream_detail(
                contract,
                events=events_by_id.get(contract.id, ()),
                coverages=(),
                schedules=(),
                chain=(),
                terminal_contract_ids=(),
                today=today,
            )
            for contract in contracts
        ]
        return items, total

    async def get_upstream_contract(
        self,
        db: AsyncSession,
        contract_id: str,
        *,
        scope: EffectivePartyScope,
        for_update: bool = False,
    ) -> UpstreamContractDetail | None:
        self._require_effective_scope(scope)
        contract = await self.asset_contract_repository.get_upstream(
            db,
            contract_id=contract_id,
            scope=scope,
            for_update=for_update,
        )
        if contract is None:
            return None
        events = await self.asset_contract_repository.list_lifecycle_events_by_contract_ids(  # noqa: E501
            db,
            contract_kind="upstream",
            contract_ids=(contract.id,),
        )
        coverages = await self.asset_contract_repository.list_upstream_coverages(
            db,
            contract_id=contract.id,
        )
        schedules = await self.asset_contract_repository.list_rent_schedules(
            db,
            contract_kind="upstream",
            contract_ids=(contract.id,),
        )
        chain = await self._upstream_chain(
            db, contract, scope=scope, events=events, as_of=self.business_today()
        )
        terminal_contracts, _ = await self.asset_contract_repository.list_terminal(
            db,
            scope=scope,
            upstream_contract_id=contract.id,
        )
        return self._upstream_detail(
            contract,
            events=events,
            coverages=coverages,
            schedules=schedules,
            chain=chain,
            terminal_contract_ids=tuple(
                sorted(terminal.id for terminal in terminal_contracts)
            ),
            today=self.business_today(),
        )

    async def list_terminal_contracts(
        self,
        db: AsyncSession,
        *,
        scope: EffectivePartyScope,
        contract_mode: str | None = None,
        upstream_contract_id: str | None = None,
        query: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[TerminalContractDetail], int]:
        self._require_effective_scope(scope)
        contracts, total = await self.asset_contract_repository.list_terminal(
            db,
            scope=scope,
            contract_mode=contract_mode,
            upstream_contract_id=upstream_contract_id,
            query=query,
            offset=offset,
            limit=limit,
        )
        events_by_id = await self._events_by_contract(
            db, contract_kind="terminal", contracts=contracts
        )
        upstream_ids = tuple(
            sorted(
                {
                    contract.upstream_contract_id
                    for contract in contracts
                    if contract.upstream_contract_id is not None
                }
            )
        )
        upstreams = await self.asset_contract_repository.get_upstreams_by_ids(
            db,
            contract_ids=upstream_ids,
            scope=scope,
        )
        upstream_by_id = {upstream.id: upstream for upstream in upstreams}
        today = self.business_today()
        items = [
            self._terminal_detail(
                contract,
                events=events_by_id.get(contract.id, ()),
                upstream=upstream_by_id.get(contract.upstream_contract_id or ""),
                coverages=(),
                schedules=(),
                chain=(),
                today=today,
            )
            for contract in contracts
        ]
        return items, total

    async def get_terminal_contract(
        self,
        db: AsyncSession,
        contract_id: str,
        *,
        scope: EffectivePartyScope,
        for_update: bool = False,
    ) -> TerminalContractDetail | None:
        self._require_effective_scope(scope)
        contract = await self.asset_contract_repository.get_terminal(
            db,
            contract_id=contract_id,
            scope=scope,
            for_update=for_update,
        )
        if contract is None:
            return None
        events = await self.asset_contract_repository.list_lifecycle_events_by_contract_ids(  # noqa: E501
            db,
            contract_kind="terminal",
            contract_ids=(contract.id,),
        )
        coverages = await self.asset_contract_repository.list_terminal_coverages(
            db,
            contract_id=contract.id,
        )
        schedules = await self.asset_contract_repository.list_rent_schedules(
            db,
            contract_kind="terminal",
            contract_ids=(contract.id,),
        )
        chain = await self._terminal_chain(
            db, contract, scope=scope, events=events, as_of=self.business_today()
        )
        upstream: UpstreamContract | None = None
        if contract.upstream_contract_id is not None:
            upstream = await self.asset_contract_repository.get_upstream(
                db,
                contract_id=contract.upstream_contract_id,
                scope=scope,
            )
        return self._terminal_detail(
            contract,
            events=events,
            upstream=upstream,
            coverages=coverages,
            schedules=schedules,
            chain=chain,
            today=self.business_today(),
        )

    async def _events_by_contract(
        self,
        db: AsyncSession,
        *,
        contract_kind: str,
        contracts: list[UpstreamContract] | list[TerminalContract],
    ) -> dict[str, tuple[ContractLifecycleEvent, ...]]:
        contract_ids = tuple(sorted(contract.id for contract in contracts))
        events = await self.asset_contract_repository.list_lifecycle_events_by_contract_ids(  # noqa: E501
            db,
            contract_kind=contract_kind,
            contract_ids=contract_ids,
        )
        grouped: dict[str, list[ContractLifecycleEvent]] = {}
        for event in events:
            grouped.setdefault(event.contract_id, []).append(event)
        return {key: tuple(value) for key, value in grouped.items()}

    async def _upstream_chain(
        self,
        db: AsyncSession,
        contract: UpstreamContract,
        *,
        scope: EffectivePartyScope,
        events: tuple[ContractLifecycleEvent, ...],
        as_of: date,
    ) -> tuple[RenewalChainItem, ...]:
        chain: list[RenewalChainItem] = []
        if contract.renewed_from_id is not None:
            predecessor = await self.asset_contract_repository.get_upstream(
                db,
                contract_id=contract.renewed_from_id,
                scope=scope,
            )
            if predecessor is not None:
                chain.append(self._chain_item(predecessor, "predecessor"))
        chain.append(self._chain_item(contract, "current"))
        successor_id, _ = self._active_successor(events, as_of=as_of)
        if successor_id is not None:
            successor = await self.asset_contract_repository.get_upstream(
                db,
                contract_id=successor_id,
                scope=scope,
            )
            if successor is not None:
                chain.append(self._chain_item(successor, "successor"))
        return tuple(chain)

    async def _terminal_chain(
        self,
        db: AsyncSession,
        contract: TerminalContract,
        *,
        scope: EffectivePartyScope,
        events: tuple[ContractLifecycleEvent, ...],
        as_of: date,
    ) -> tuple[RenewalChainItem, ...]:
        chain: list[RenewalChainItem] = []
        if contract.renewed_from_id is not None:
            predecessor = await self.asset_contract_repository.get_terminal(
                db,
                contract_id=contract.renewed_from_id,
                scope=scope,
            )
            if predecessor is not None:
                chain.append(self._chain_item(predecessor, "predecessor"))
        chain.append(self._chain_item(contract, "current"))
        successor_id, _ = self._active_successor(events, as_of=as_of)
        if successor_id is not None:
            successor = await self.asset_contract_repository.get_terminal(
                db,
                contract_id=successor_id,
                scope=scope,
            )
            if successor is not None:
                chain.append(self._chain_item(successor, "successor"))
        return tuple(chain)

    @staticmethod
    def _active_successor(
        events: tuple[ContractLifecycleEvent, ...],
        *,
        as_of: date,
    ) -> tuple[str | None, date | None]:
        """Return the unreversed successor id and its effective date.

        Events later than ``as_of`` do not exist yet, matching the
        replay-by-date rule the status derivations apply.
        """
        replayed = tuple(
            event for event in events if event.effective_date <= as_of
        )
        reversed_event_ids = {
            event.reversed_event_id
            for event in replayed
            if event.event_type == "reversed" and event.reversed_event_id is not None
        }
        for event in replayed:
            if (
                event.event_type == "renewed"
                and event.id not in reversed_event_ids
                and event.successor_contract_id is not None
            ):
                return event.successor_contract_id, event.effective_date
        return None, None

    @staticmethod
    def _chain_item(
        contract: UpstreamContract | TerminalContract,
        relation: str,
    ) -> RenewalChainItem:
        return RenewalChainItem(
            contract_id=contract.id,
            contract_number=contract.contract_number,
            start_date=contract.start_date,
            end_date=contract.end_date,
            relation=relation,  # type: ignore[arg-type]
        )

    def _upstream_detail(
        self,
        contract: UpstreamContract,
        *,
        events: tuple[ContractLifecycleEvent, ...],
        coverages: tuple[UpstreamContractAssetUnit, ...],
        schedules: tuple[ContractRentSchedule, ...],
        chain: tuple[RenewalChainItem, ...],
        terminal_contract_ids: tuple[str, ...],
        today: date,
    ) -> UpstreamContractDetail:
        _, successor_effective_from = self._active_successor(events, as_of=today)
        return UpstreamContractDetail.model_validate(
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
                "asset_unit_ids": [],
                "version": contract.version,
                "created_at": contract.created_at,
                "updated_at": contract.updated_at,
                "status": derive_upstream_contract_status(
                    contract,
                    as_of=today,
                    lifecycle_events=events,
                    successor_effective_from=successor_effective_from,
                ),
                "warnings": [],
                "coverages": [
                    ContractCoverageItem(
                        asset_unit_id=coverage.asset_unit_id,
                        effective_from=coverage.effective_from,
                        effective_to=coverage.effective_to,
                    )
                    for coverage in coverages
                ],
                "rent_schedules": [
                    RentScheduleItem(
                        id=schedule.id,
                        stage_start=schedule.stage_start,
                        stage_end=schedule.stage_end,
                        base_monthly_rent=schedule.base_monthly_rent,
                        increase_rate=schedule.increase_rate,
                        free_rent_months=schedule.free_rent_months,
                        discount_amount=schedule.discount_amount,
                        actual_monthly_rent=schedule.actual_monthly_rent,
                        payment_cycle=schedule.payment_cycle,  # type: ignore[arg-type]
                        due_day=schedule.due_day,
                    )
                    for schedule in schedules
                ],
                "renewal_chain": list(chain),
                "terminal_contract_ids": list(terminal_contract_ids),
                "lifecycle_events": [
                    LifecycleEventItem(
                        id=event.id,
                        event_type=event.event_type,  # type: ignore[arg-type]
                        effective_date=event.effective_date,
                        successor_contract_id=event.successor_contract_id,
                        reversed_event_id=event.reversed_event_id,
                        reason=event.reason,
                        created_by=event.created_by,
                        created_at=event.created_at,
                    )
                    for event in events
                ],
            }
        )

    def _terminal_detail(
        self,
        contract: TerminalContract,
        *,
        events: tuple[ContractLifecycleEvent, ...],
        upstream: UpstreamContract | None,
        coverages: tuple[TerminalContractAssetUnit, ...],
        schedules: tuple[ContractRentSchedule, ...],
        chain: tuple[RenewalChainItem, ...],
        today: date,
    ) -> TerminalContractDetail:
        _, successor_effective_from = self._active_successor(events, as_of=today)
        warning_codes = derive_terminal_contract_warnings(
            contract,
            upstream=upstream,
        )
        return TerminalContractDetail.model_validate(
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
                "asset_unit_ids": [],
                "version": contract.version,
                "created_at": contract.created_at,
                "updated_at": contract.updated_at,
                "status": derive_terminal_contract_status(
                    contract,
                    as_of=today,
                    lifecycle_events=events,
                    successor_effective_from=successor_effective_from,
                ),
                "warnings": [public_warning(code) for code in warning_codes],
                "coverages": [
                    ContractCoverageItem(
                        asset_unit_id=coverage.asset_unit_id,
                        effective_from=coverage.effective_from,
                        effective_to=coverage.effective_to,
                    )
                    for coverage in coverages
                ],
                "rent_schedules": [
                    RentScheduleItem(
                        id=schedule.id,
                        stage_start=schedule.stage_start,
                        stage_end=schedule.stage_end,
                        base_monthly_rent=schedule.base_monthly_rent,
                        increase_rate=schedule.increase_rate,
                        free_rent_months=schedule.free_rent_months,
                        discount_amount=schedule.discount_amount,
                        actual_monthly_rent=schedule.actual_monthly_rent,
                        payment_cycle=schedule.payment_cycle,  # type: ignore[arg-type]
                        due_day=schedule.due_day,
                    )
                    for schedule in schedules
                ],
                "renewal_chain": list(chain),
                "lifecycle_events": [
                    LifecycleEventItem(
                        id=event.id,
                        event_type=event.event_type,  # type: ignore[arg-type]
                        effective_date=event.effective_date,
                        successor_contract_id=event.successor_contract_id,
                        reversed_event_id=event.reversed_event_id,
                        reason=event.reason,
                        created_by=event.created_by,
                        created_at=event.created_at,
                    )
                    for event in events
                ],
            }
        )


asset_operations_query_service = AssetOperationsQueryService(
    asset_unit_repository=default_asset_unit_repository,
    asset_contract_repository=default_asset_contract_repository,
)


__all__ = [
    "AssetOperationsQueryService",
    "AssetContractReader",
    "AssetUnitReader",
    "asset_operations_query_service",
]
