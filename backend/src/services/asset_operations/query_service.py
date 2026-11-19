"""Scoped query interface for asset-operations v5."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterable, Sequence
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, Protocol
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
    AssetUnitCoverageInterval,
    AssetUnitDetail,
    AssetUnitFilterCounts,
    ContractCoverageItem,
    LifecycleEventItem,
    RenewalChainItem,
    RentScheduleItem,
    TerminalContractDetail,
    TerminalContractFilterCounts,
    UpstreamContractDetail,
    UpstreamPaymentPlanItem,
    UpstreamUnitMatrixItem,
)
from ...schemas.rent_queries import RentEntryView
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

    async def get_units_by_ids(
        self,
        db: AsyncSession,
        *,
        unit_ids: tuple[str, ...],
        scope: EffectivePartyScope,
    ) -> tuple[AssetUnit, ...]: ...

    async def distinct_usage_types(
        self,
        db: AsyncSession,
        *,
        scope: EffectivePartyScope,
    ) -> Sequence[str]: ...

    async def project_names(
        self,
        db: AsyncSession,
        *,
        project_ids: Iterable[str],
    ) -> dict[str, str]: ...

    async def active_certificate_counts(
        self,
        db: AsyncSession,
        *,
        unit_ids: tuple[str, ...],
        as_of: date,
    ) -> dict[str, int]: ...


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
        owner_party_id: str | None = None,
        query: str | None = None,
        offset: int = 0,
        limit: int = 50,
        contract_ids: set[str] | None = None,
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

    async def list_terminal_unit_labels(
        self,
        db: AsyncSession,
        *,
        contract_ids: tuple[str, ...],
    ) -> dict[str, tuple[str, ...]]: ...

    async def list_active_terminals_by_units(
        self,
        db: AsyncSession,
        *,
        unit_ids: tuple[str, ...],
        as_of: date,
    ) -> tuple[tuple[str, TerminalContract], ...]: ...

    async def coverage_history_for_unit(
        self,
        db: AsyncSession,
        *,
        asset_unit_id: str,
    ) -> tuple[tuple[TerminalContract, ...], tuple[UpstreamContract, ...]]: ...

    async def list_terminal_coverages_by_ids(
        self,
        db: AsyncSession,
        *,
        contract_ids: tuple[str, ...],
    ) -> tuple[tuple[str, TerminalContractAssetUnit], ...]: ...

    async def list_terminals_by_upstream_batched(
        self,
        db: AsyncSession,
        *,
        upstream_contract_ids: tuple[str, ...],
    ) -> tuple[tuple[str, TerminalContract], ...]: ...

    async def list_upstream_coverages_batched(
        self,
        db: AsyncSession,
        *,
        contract_ids: tuple[str, ...],
    ) -> tuple[tuple[str, UpstreamContractAssetUnit], ...]: ...


class PartyNameReader(Protocol):
    async def get_party_names_by_ids(
        self,
        db: AsyncSession,
        *,
        party_ids: tuple[str, ...],
    ) -> dict[str, str]: ...


class AssetOperationsQueryService:
    """Expose scoped reads while hiding range validation and persistence."""

    def __init__(
        self,
        *,
        asset_unit_repository: AssetUnitReader | None = None,
        asset_contract_repository: AssetContractReader | None = None,
        party_name_reader: PartyNameReader | None = None,
        business_today: Callable[[], date] = _business_today,
    ) -> None:
        self.asset_unit_repository = (
            asset_unit_repository or default_asset_unit_repository
        )
        self.asset_contract_repository = (
            asset_contract_repository or default_asset_contract_repository
        )
        self.party_name_reader = party_name_reader or default_party_name_reader
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
        assessment_operator_party_id: str | None = None,
        assessment_year: int | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[AssetUnitDetail], int]:
        items, total, _ = await self.list_asset_units_view(
            db,
            scope=scope,
            project_id=project_id,
            owner_party_id=owner_party_id,
            usage_type=usage_type,
            query=query,
            filter=filter,
            assessment_operator_party_id=assessment_operator_party_id,
            assessment_year=assessment_year,
            offset=offset,
            limit=limit,
        )
        return items, total

    async def list_asset_units_view(
        self,
        db: AsyncSession,
        *,
        scope: EffectivePartyScope,
        project_id: str | None = None,
        owner_party_id: str | None = None,
        usage_type: str | None = None,
        query: str | None = None,
        filter: str | None = None,
        assessment_operator_party_id: str | None = None,
        assessment_year: int | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[AssetUnitDetail], int, AssetUnitFilterCounts]:
        """Page of enriched unit rows plus the segmented-filter counts."""
        self._require_effective_scope(scope)
        today = self.business_today()
        rented_ids = await self.asset_contract_repository.list_rented_unit_ids(
            db,
            as_of=today,
            scope=scope,
        )
        assessment_maps = await self._assessment_maps(
            db,
            operator_party_id=assessment_operator_party_id,
            year=assessment_year,
            today=today,
        )
        decided, pending_ids = assessment_maps
        included_ids = frozenset(
            unit_id for unit_id, included in decided.items() if included
        )

        base_kwargs: dict[str, Any] = {
            "scope": scope,
            "project_id": project_id,
            "owner_party_id": owner_party_id,
            "usage_type": usage_type,
            "query": query,
        }

        def restricted(**extra: Any) -> dict[str, Any]:
            merged = dict(base_kwargs)
            merged.update(extra)
            return merged

        filter_kwargs = self._unit_filter_kwargs(
            filter,
            today=today,
            rented_ids=rented_ids,
            included_ids=included_ids,
        )
        units, total = await self.asset_unit_repository.list(
            db,
            offset=offset,
            limit=limit,
            **restricted(**filter_kwargs),
        )
        items = await self._enrich_units(
            db,
            units,
            rented_ids=rented_ids,
            decided=decided,
            pending_ids=pending_ids,
            today=today,
        )
        counts = AssetUnitFilterCounts(
            all=await self._count_units(db, **restricted()),
            in_assessment=await self._count_units(
                db, **restricted(unit_ids=tuple(sorted(included_ids)))
            ),
            vacant=await self._count_units(
                db,
                **restricted(
                    rentable_only=True,
                    exclude_unit_ids=tuple(sorted(rented_ids)),
                ),
            ),
            non_rentable=await self._count_units(
                db, **restricted(non_rentable_only=True)
            ),
            missing_certificate=await self._count_units(
                db, **restricted(missing_certificate_only=True, as_of=today)
            ),
        )
        return items, total, counts

    @staticmethod
    def _unit_filter_kwargs(
        filter: str | None,
        *,
        today: date,
        rented_ids: set[str],
        included_ids: frozenset[str],
    ) -> dict[str, Any]:
        if filter == "non_rentable":
            return {"non_rentable_only": True}
        if filter == "vacant":
            return {
                "rentable_only": True,
                "exclude_unit_ids": tuple(sorted(rented_ids)),
            }
        if filter == "in_assessment":
            return {"unit_ids": tuple(sorted(included_ids))}
        if filter == "missing_certificate":
            return {"missing_certificate_only": True, "as_of": today}
        return {}

    async def _count_units(self, db: AsyncSession, **kwargs: Any) -> int:
        _, total = await self.asset_unit_repository.list(
            db, offset=0, limit=1, **kwargs
        )
        return total

    async def _assessment_maps(
        self,
        db: AsyncSession,
        *,
        operator_party_id: str | None,
        year: int | None,
        today: date,
    ) -> tuple[dict[str, bool], frozenset[str]]:
        """Decided inclusion map and pending-confirm ids for current version."""
        if operator_party_id is None or year is None:
            return {}, frozenset()
        from ...crud.assessment_scope import assessment_scope_repository

        version = await assessment_scope_repository.get_active_version(
            db, operator_party_id=operator_party_id, year=year
        )
        if version is None:
            return {}, frozenset()
        items = await assessment_scope_repository.list_items(db, version_id=version.id)
        candidates = await assessment_scope_repository.list_managed_units(
            db,
            operator_party_id=operator_party_id,
            as_of=today,
            year=year,
            operating_only=True,
        )
        from .assessment_scope_command_service import view_for

        view = view_for(version, tuple(items), candidates)
        decided = {item.asset_unit_id: item.included for item in view.items}
        pending = frozenset(unit_id for unit_id, _reason in view.pending)
        return decided, pending

    async def _enrich_units(
        self,
        db: AsyncSession,
        units: Sequence[AssetUnit],
        *,
        rented_ids: set[str],
        decided: dict[str, bool],
        pending_ids: frozenset[str],
        today: date,
    ) -> list[AssetUnitDetail]:
        if len(units) == 0:
            return []
        unit_ids = tuple(unit.id for unit in units)
        project_names = await self.asset_unit_repository.project_names(
            db, project_ids=tuple(unit.project_id for unit in units)
        )
        owner_ids = tuple(
            sorted({unit.owner_party_id for unit in units if unit.owner_party_id})
        )
        party_names = await self._party_names(db, owner_ids)
        cert_counts = await self.asset_unit_repository.active_certificate_counts(
            db, unit_ids=unit_ids, as_of=today
        )
        terminal_rows = (
            await self.asset_contract_repository.list_active_terminals_by_units(
                db, unit_ids=unit_ids, as_of=today
            )
        )
        terminal_ids = tuple(
            sorted({terminal.id for _unit_id, terminal in terminal_rows})
        )
        terminal_events: dict[str, tuple[ContractLifecycleEvent, ...]] = {}
        if terminal_ids:
            events = await self.asset_contract_repository.list_lifecycle_events_by_contract_ids(  # noqa: E501
                db, contract_kind="terminal", contract_ids=terminal_ids
            )
            grouped: dict[str, list[ContractLifecycleEvent]] = {}
            for event in events:
                grouped.setdefault(event.contract_id, []).append(event)
            terminal_events = {key: tuple(value) for key, value in grouped.items()}
        tenant_ids = tuple(
            sorted(
                {
                    terminal.tenant_party_id
                    for _unit_id, terminal in terminal_rows
                    if terminal.tenant_party_id
                }
            )
        )
        tenant_names = await self._party_names(db, tenant_ids)
        from .rent_ledger_query_service import effective_end

        terminal_by_unit: dict[str, tuple[TerminalContract, date]] = {}
        for unit_id, terminal in terminal_rows:
            end = effective_end(terminal.end_date, terminal_events.get(terminal.id, ()))
            if end < today:
                continue
            current = terminal_by_unit.get(unit_id)
            if current is None or terminal.start_date > current[0].start_date:
                terminal_by_unit[unit_id] = (terminal, end)

        items: list[AssetUnitDetail] = []
        for unit in units:
            detail = self._unit_detail(unit, rented=unit.id in rented_ids)
            current = terminal_by_unit.get(unit.id)
            detail.owner_party_name = party_names.get(unit.owner_party_id, "")
            detail.project_name = project_names.get(unit.project_id, "")
            if unit.id in decided:
                detail.assessment = "included" if decided[unit.id] else "excluded"
            elif unit.id in pending_ids:
                detail.assessment = "pending"
            detail.certificate_count = cert_counts.get(unit.id, 0)
            if current is not None:
                terminal, end = current
                detail.current_tenant_name = tenant_names.get(
                    terminal.tenant_party_id, ""
                )
                detail.current_contract_number = terminal.contract_number
                detail.current_contract_end_date = end
            items.append(detail)
        return items

    async def _party_names(
        self, db: AsyncSession, party_ids: Sequence[str]
    ) -> dict[str, str]:
        if len(party_ids) == 0:
            return {}
        return await self.party_name_reader.get_party_names_by_ids(
            db, party_ids=tuple(party_ids)
        )

    async def coverage_history(
        self,
        db: AsyncSession,
        unit_id: str,
        *,
        scope: EffectivePartyScope,
    ) -> list[AssetUnitCoverageInterval] | None:
        """Timeline bars for one unit; None when the unit is out of scope."""
        self._require_effective_scope(scope)
        unit = await self.asset_unit_repository.get(db, unit_id=unit_id, scope=scope)
        if unit is None:
            return None
        (
            terminals,
            upstreams,
        ) = await self.asset_contract_repository.coverage_history_for_unit(
            db, asset_unit_id=unit_id
        )
        contract_ids = tuple(
            sorted(
                [contract.id for contract in terminals]
                + [contract.id for contract in upstreams]
            )
        )
        events = (
            await self.asset_contract_repository.list_lifecycle_events_by_contract_ids(
                db, contract_kind="upstream", contract_ids=contract_ids
            )
            if contract_ids
            else ()
        )
        terminal_events = (
            await self.asset_contract_repository.list_lifecycle_events_by_contract_ids(
                db, contract_kind="terminal", contract_ids=contract_ids
            )
            if contract_ids
            else ()
        )
        from .rent_ledger_query_service import effective_end

        all_events = tuple(events) + tuple(terminal_events)

        def _end(contract_id: str, raw_end: date) -> date:
            contract_events = tuple(
                event for event in all_events if event.contract_id == contract_id
            )
            return effective_end(raw_end, contract_events)

        items = [
            AssetUnitCoverageInterval(
                contract_kind="terminal",
                contract_id=contract.id,
                contract_number=contract.contract_number,
                start_date=contract.start_date,
                end_date=_end(contract.id, contract.end_date),
            )
            for contract in terminals
        ] + [
            AssetUnitCoverageInterval(
                contract_kind="upstream",
                contract_id=contract.id,
                contract_number=contract.contract_number,
                start_date=contract.start_date,
                end_date=_end(contract.id, contract.end_date),
            )
            for contract in upstreams
        ]
        items.sort(key=lambda item: (item.contract_kind, item.start_date))
        return items

    async def list_asset_unit_usage_types(
        self,
        db: AsyncSession,
        *,
        scope: EffectivePartyScope,
    ) -> Sequence[str]:
        self._require_effective_scope(scope)
        return await self.asset_unit_repository.distinct_usage_types(db, scope=scope)

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
        enriched = await self._enrich_units(
            db,
            [unit],
            rented_ids=rented_ids,
            decided={},
            pending_ids=frozenset(),
            today=today,
        )
        detail = enriched[0]
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
        occupancy = rented_area / rentable if rentable > 0 else Decimal("0")
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
        events = (
            await self.asset_contract_repository.list_lifecycle_events_by_contract_ids(  # noqa: E501
                db,
                contract_kind="upstream",
                contract_ids=(contract.id,),
            )
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
        detail = self._upstream_detail(
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

        from .rent_ledger_query_service import rent_ledger_query_service

        detail.rent_summary = await rent_ledger_query_service.contract_summary(
            db,
            contract=contract,
            contract_kind="upstream",
            schedules=schedules,
            events=events,
            today=self.business_today(),
        )
        today = self.business_today()
        detail.days_to_expiry = (contract.end_date - today).days

        if contract.contract_type == "lease":
            detail.payment_plan = await self._upstream_payment_plan(
                db,
                contract=contract,
                schedules=schedules,
                events=events,
                today=today,
            )
        detail.units_matrix = await self._upstream_units_matrix(
            db,
            contract=contract,
            coverages=coverages,
            terminal_contracts=terminal_contracts,
            scope=scope,
            today=today,
        )
        return detail

    async def _upstream_payment_plan(
        self,
        db: AsyncSession,
        *,
        contract: UpstreamContract,
        schedules: tuple[ContractRentSchedule, ...],
        events: tuple[ContractLifecycleEvent, ...],
        today: date,
    ) -> list[UpstreamPaymentPlanItem]:
        """Per-stage plan: 期间/月租/期数/进度/合计（prototype 付款计划）."""
        from .rent_ledger_query_service import effective_end, rent_ledger_query_service

        entries, records = await rent_ledger_query_service.repository.contract_entries(
            db, contract_kind="upstream", contract_id=contract.id
        )

        from ...crud.rent_ledger_queries import RentQueryFacts

        facts = RentQueryFacts((contract,), entries, records, schedules, events)
        views, _ = rent_ledger_query_service._views(facts, today=today)
        end = effective_end(contract.end_date, events)
        active_views = [view for view in views.values() if view.status != "void"]
        plan: list[UpstreamPaymentPlanItem] = []
        for index, stage in enumerate(
            sorted(schedules, key=lambda row: row.stage_start)
        ):
            # 期数/合计与期间同口径：终止回放后的合同截止截断阶段。
            effective_stage_end = min(stage.stage_end, end)
            months = (
                (effective_stage_end.year - stage.stage_start.year) * 12
                + effective_stage_end.month
                - stage.stage_start.month
                + 1
            )
            months = max(months, 0)
            stage_views = [
                view
                for view in active_views
                if stage.stage_start <= view.period_start <= effective_stage_end
            ]
            paid = len([view for view in stage_views if view.status == "paid"])
            pending = [view for view in stage_views if view.remaining_amount > 0]
            next_due = min((view.due_date for view in pending), default=None)
            if index == 0:
                note = "首期租金"
            elif stage.increase_rate:
                note = f"第 {index} 次递增"
            else:
                note = ""
            plan.append(
                UpstreamPaymentPlanItem(
                    stage_start=stage.stage_start,
                    stage_end=min(stage.stage_end, end),
                    monthly_rent=stage.actual_monthly_rent,
                    period_count=max(months, 0),
                    paid_count=paid,
                    next_due_date=next_due,
                    total_amount=stage.actual_monthly_rent * months,
                    note=note,
                )
            )
        return plan

    async def _upstream_units_matrix(
        self,
        db: AsyncSession,
        *,
        contract: UpstreamContract,
        coverages: tuple[UpstreamContractAssetUnit, ...],
        terminal_contracts: list[TerminalContract],
        scope: EffectivePartyScope,
        today: date,
    ) -> list[UpstreamUnitMatrixItem]:
        """单元×当前终端合同矩阵（prototype 资产单元与终端合同表）."""
        _ = contract
        unit_ids = tuple(
            sorted(
                coverage.asset_unit_id
                for coverage in coverages
                if coverage.effective_from <= today
                and (coverage.effective_to is None or coverage.effective_to >= today)
            )
        )
        units = await self.asset_unit_repository.get_units_by_ids(
            db, unit_ids=unit_ids, scope=scope
        )
        terminal_ids = tuple(sorted(terminal.id for terminal in terminal_contracts))
        terminal_events = (
            await self.asset_contract_repository.list_lifecycle_events_by_contract_ids(
                db, contract_kind="terminal", contract_ids=terminal_ids
            )
            if terminal_ids
            else ()
        )
        grouped: dict[str, list[ContractLifecycleEvent]] = {}
        for event in terminal_events:
            grouped.setdefault(event.contract_id, []).append(event)
        from .rent_ledger_query_service import effective_end

        schedules = (
            await self.asset_contract_repository.list_rent_schedules(
                db, contract_kind="terminal", contract_ids=terminal_ids
            )
            if terminal_ids
            else ()
        )
        tenant_names = await self.party_name_reader.get_party_names_by_ids(
            db,
            party_ids=tuple(
                sorted(
                    {
                        terminal.tenant_party_id
                        for terminal in terminal_contracts
                        if terminal.tenant_party_id
                    }
                )
            ),
        )
        covered_rows = (
            await self.asset_contract_repository.list_terminal_coverages_by_ids(
                db, contract_ids=terminal_ids
            )
        )
        covered_by_contract: dict[str, list[TerminalContractAssetUnit]] = defaultdict(
            list
        )
        for _contract_id, link in covered_rows:
            covered_by_contract[link.terminal_contract_id].append(link)
        terminal_by_unit: dict[str, tuple[TerminalContract | None, date | None]] = {}
        for terminal in terminal_contracts:
            covered = covered_by_contract.get(terminal.id, ())
            end = effective_end(terminal.end_date, tuple(grouped.get(terminal.id, ())))
            if end < today:
                continue
            for link in covered:
                current = terminal_by_unit.get(link.asset_unit_id)
                if (
                    current is None
                    or current[0] is None
                    or terminal.start_date > current[0].start_date
                ):
                    terminal_by_unit[link.asset_unit_id] = (terminal, end)
        matrix: list[UpstreamUnitMatrixItem] = []
        for unit in units:
            current_terminal, current_end = terminal_by_unit.get(unit.id, (None, None))
            stage = (
                [
                    row
                    for row in schedules
                    if row.contract_id == current_terminal.id
                    and row.stage_start <= today <= row.stage_end
                ]
                if current_terminal is not None
                else []
            )
            matrix.append(
                UpstreamUnitMatrixItem(
                    asset_unit_id=unit.id,
                    unit_code=unit.unit_code,
                    unit_name=unit.name,
                    rentable_area=unit.rentable_area,
                    tenant_party_name=(
                        tenant_names.get(current_terminal.tenant_party_id, "")
                        if current_terminal is not None
                        else None
                    ),
                    terminal_contract_number=(
                        current_terminal.contract_number
                        if current_terminal is not None
                        else None
                    ),
                    terminal_end_date=current_end,
                    monthly_rent=stage[0].actual_monthly_rent if stage else None,
                    has_scan=(
                        current_terminal.scan_document_id is not None
                        if current_terminal is not None
                        else None
                    ),
                )
            )
        return matrix

    async def list_terminal_contracts(
        self,
        db: AsyncSession,
        *,
        scope: EffectivePartyScope,
        contract_mode: str | None = None,
        upstream_contract_id: str | None = None,
        owner_party_id: str | None = None,
        query: str | None = None,
        offset: int = 0,
        limit: int = 50,
        rent_unpaid: bool = False,
        deposit_unsettled: bool = False,
    ) -> tuple[list[TerminalContractDetail], int]:
        items, total, _ = await self.list_terminal_contracts_view(
            db,
            scope=scope,
            contract_mode=contract_mode,
            upstream_contract_id=upstream_contract_id,
            owner_party_id=owner_party_id,
            query=query,
            filter_value=(
                "rent_unpaid"
                if rent_unpaid
                else "deposit_unsettled"
                if deposit_unsettled
                else None
            ),
            offset=offset,
            limit=limit,
        )
        return items, total

    async def list_terminal_contracts_view(
        self,
        db: AsyncSession,
        *,
        scope: EffectivePartyScope,
        contract_mode: str | None = None,
        upstream_contract_id: str | None = None,
        owner_party_id: str | None = None,
        query: str | None = None,
        filter_value: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[TerminalContractDetail], int, TerminalContractFilterCounts]:
        """Filtered page plus per-filter counts (prototype segmented bar)."""
        self._require_effective_scope(scope)
        today = self.business_today()
        contracts, _ = await self.asset_contract_repository.list_terminal(
            db,
            scope=scope,
            contract_mode=contract_mode,
            upstream_contract_id=upstream_contract_id,
            owner_party_id=owner_party_id,
            offset=0,
            limit=5000,
        )
        events = (
            await self.asset_contract_repository.list_lifecycle_events_by_contract_ids(
                db,
                contract_kind="terminal",
                contract_ids=tuple(sorted(c.id for c in contracts)),
            )
        )
        grouped_events: dict[str, list[ContractLifecycleEvent]] = {}
        for event in events:
            grouped_events.setdefault(event.contract_id, []).append(event)
        events_by_id: dict[str, tuple[ContractLifecycleEvent, ...]] = {
            key: tuple(value) for key, value in grouped_events.items()
        }

        statuses: dict[str, str] = {}
        for contract in contracts:
            contract_events = events_by_id.get(contract.id, ())
            successor_id, successor_from = self._active_successor(
                contract_events, as_of=today
            )
            _ = successor_id
            statuses[contract.id] = derive_terminal_contract_status(
                contract,
                as_of=today,
                lifecycle_events=contract_events,
                successor_effective_from=successor_from,
            )

        from .rent_ledger_query_service import rent_ledger_query_service

        scoped_terminal_ids = tuple(sorted(c.id for c in contracts))
        rent_unpaid_ids = await rent_ledger_query_service.unpaid_contract_ids(
            db, today=today, contract_ids=scoped_terminal_ids
        )
        from ...crud.deposit_queries import deposit_query_repository
        from .deposit_query_service import project_deposit_facts

        deposit_facts = await deposit_query_repository.load_facts(
            db, scope=scope, contract_kind="terminal"
        )
        unsettled_ids = {
            view.contract_id
            for view in project_deposit_facts(deposit_facts, today=today)
            if view.status != "settled"
        }

        counts = TerminalContractFilterCounts(
            active=len([c for c in contracts if statuses[c.id] == "active"]),
            expiring_180=len([c for c in contracts if statuses[c.id] == "expiring"]),
            rent_unpaid=len([c for c in contracts if c.id in rent_unpaid_ids]),
            deposit_unsettled=len([c for c in contracts if c.id in unsettled_ids]),
            missing_scan=len([c for c in contracts if c.scan_document_id is None]),
            ended=len(
                [c for c in contracts if statuses[c.id] in {"ended", "historical"}]
            ),
        )

        def _matches(contract: TerminalContract) -> bool:
            if filter_value == "active":
                return statuses[contract.id] == "active"
            if filter_value == "expiring_180":
                return statuses[contract.id] == "expiring"
            if filter_value == "rent_unpaid":
                return contract.id in rent_unpaid_ids
            if filter_value == "deposit_unsettled":
                return contract.id in unsettled_ids
            if filter_value == "missing_scan":
                return contract.scan_document_id is None
            if filter_value == "ended":
                return statuses[contract.id] in {"ended", "historical"}
            return True

        filtered = [contract for contract in contracts if _matches(contract)]
        filtered.sort(key=lambda contract: contract.contract_number)

        normalized_query = (query or "").strip()
        if normalized_query != "":
            tenant_ids = tuple(
                sorted({c.tenant_party_id for c in filtered if c.tenant_party_id})
            )
            tenant_names = await self.party_name_reader.get_party_names_by_ids(
                db, party_ids=tenant_ids
            )
            pattern = normalized_query.lower()
            filtered = [
                contract
                for contract in filtered
                if pattern in contract.contract_number.lower()
                or pattern in tenant_names.get(contract.tenant_party_id, "").lower()
            ]

        total = len(filtered)
        page = filtered[offset : offset + limit]

        events_by_page = await self._events_by_contract(
            db, contract_kind="terminal", contracts=page
        )
        upstream_ids = tuple(
            sorted(
                {
                    contract.upstream_contract_id
                    for contract in page
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

        page_ids = tuple(sorted(contract.id for contract in page))
        schedules = (
            await self.asset_contract_repository.list_rent_schedules(
                db, contract_kind="terminal", contract_ids=page_ids
            )
            if page_ids
            else ()
        )
        unit_labels = await self.asset_contract_repository.list_terminal_unit_labels(
            db, contract_ids=page_ids
        )
        tenant_names_page = await self.party_name_reader.get_party_names_by_ids(
            db,
            party_ids=tuple(
                sorted({c.tenant_party_id for c in page if c.tenant_party_id})
            ),
        )

        # 本月到账状态：整年台账事实一次读入后按页内合同聚合。
        from ...crud.rent_ledger_queries import rent_ledger_query_repository

        matrix_facts = await rent_ledger_query_repository.matrix_facts(
            db, scope=scope, ledger_type="terminal_rent", year=today.year
        )
        month_views, _ = rent_ledger_query_service._views(matrix_facts, today=today)
        month = today.strftime("%Y-%m")
        month_entries: dict[str, list[RentEntryView]] = {}
        for view in month_views.values():
            if view.period == month and view.status != "void":
                month_entries.setdefault(view.contract_id, []).append(view)

        items: list[TerminalContractDetail] = []
        for contract in page:
            detail = self._terminal_detail(
                contract,
                events=events_by_page.get(contract.id, ()),
                upstream=upstream_by_id.get(contract.upstream_contract_id or ""),
                coverages=(),
                schedules=(),
                chain=(),
                today=today,
            )
            detail.tenant_party_name = tenant_names_page.get(
                contract.tenant_party_id, ""
            )
            upstream = upstream_by_id.get(contract.upstream_contract_id or "")
            detail.upstream_contract_number = (
                upstream.contract_number if upstream is not None else None
            )
            detail.unit_labels = list(unit_labels.get(contract.id, ()))
            contract_schedules = [
                row
                for row in schedules
                if row.contract_id == contract.id
                and row.stage_start <= today <= row.stage_end
            ]
            detail.current_monthly_rent = (
                contract_schedules[0].actual_monthly_rent
                if contract_schedules
                else None
            )
            entries = month_entries.get(contract.id, [])
            if entries:
                remaining = sum((row.remaining_amount for row in entries), Decimal("0"))
                due = sum((row.due_amount for row in entries), Decimal("0"))
                if remaining <= 0:
                    detail.current_month_collection_status = "paid"
                elif remaining < due:
                    detail.current_month_collection_status = "partial"
                else:
                    detail.current_month_collection_status = "unpaid"
                detail.current_month_remaining = remaining
            else:
                detail.current_month_collection_status = "none"
                detail.current_month_remaining = None
            detail.has_scan = contract.scan_document_id is not None
            items.append(detail)
        return items, total, counts

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
        events = (
            await self.asset_contract_repository.list_lifecycle_events_by_contract_ids(  # noqa: E501
                db,
                contract_kind="terminal",
                contract_ids=(contract.id,),
            )
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
        detail = self._terminal_detail(
            contract,
            events=events,
            upstream=upstream,
            coverages=coverages,
            schedules=schedules,
            chain=chain,
            today=self.business_today(),
        )

        from .rent_ledger_query_service import rent_ledger_query_service

        detail.rent_summary = await rent_ledger_query_service.contract_summary(
            db,
            contract=contract,
            contract_kind="terminal",
            schedules=schedules,
            events=events,
            today=self.business_today(),
        )
        return detail

    async def _events_by_contract(
        self,
        db: AsyncSession,
        *,
        contract_kind: str,
        contracts: list[UpstreamContract] | list[TerminalContract],
    ) -> dict[str, tuple[ContractLifecycleEvent, ...]]:
        contract_ids = tuple(sorted(contract.id for contract in contracts))
        events = (
            await self.asset_contract_repository.list_lifecycle_events_by_contract_ids(  # noqa: E501
                db,
                contract_kind=contract_kind,
                contract_ids=contract_ids,
            )
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
        replayed = tuple(event for event in events if event.effective_date <= as_of)
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


class _DefaultPartyNameReader:
    """Lazily bind the CRUD party reader, keeping tests' injection seam."""

    async def get_party_names_by_ids(
        self,
        db: AsyncSession,
        *,
        party_ids: tuple[str, ...],
    ) -> dict[str, str]:
        from ...crud.party import CRUDParty

        return await CRUDParty().get_party_names_by_ids(db, party_ids=party_ids)


default_party_name_reader = _DefaultPartyNameReader()


asset_operations_query_service = AssetOperationsQueryService(
    asset_unit_repository=default_asset_unit_repository,
    asset_contract_repository=default_asset_contract_repository,
)


__all__ = [
    "AssetOperationsQueryService",
    "AssetContractReader",
    "AssetUnitReader",
    "PartyNameReader",
    "asset_operations_query_service",
]
