"""Area-conservation rules for asset-unit split and merge operations."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from ...models.asset_contract import (
    ContractLifecycleEvent,
    TerminalContract,
    TerminalContractAssetUnit,
    UpstreamContract,
    UpstreamContractAssetUnit,
)
from ...models.asset_unit import AssetUnit
from .contract_projections import derive_terminal_contract_status
from .errors import (
    AssetUnitAreaMismatchError,
    AssetUnitBoundaryInvalidError,
    AssetUnitUpstreamScopeMismatchError,
)

_AREA_QUANTUM = Decimal("0.01")


@dataclass(frozen=True)
class AreaTotals:
    land_area: Decimal
    building_area: Decimal
    rentable_area: Decimal

    def as_dict(self) -> dict[str, str]:
        return {
            "land_area": str(self.land_area.quantize(_AREA_QUANTUM)),
            "building_area": str(self.building_area.quantize(_AREA_QUANTUM)),
            "rentable_area": str(self.rentable_area.quantize(_AREA_QUANTUM)),
        }


@dataclass(frozen=True)
class AreaCheck:
    source: AreaTotals
    result: AreaTotals


def _sum_areas(units: Iterable[AssetUnit]) -> AreaTotals:
    land_area = Decimal("0")
    building_area = Decimal("0")
    rentable_area = Decimal("0")
    for unit in units:
        land_area += unit.land_area
        building_area += unit.building_area
        rentable_area += unit.rentable_area
    return AreaTotals(
        land_area=land_area,
        building_area=building_area,
        rentable_area=rentable_area,
    )


def validate_split(
    *,
    source: AssetUnit,
    children: Iterable[AssetUnit],
    effective_date: date,
) -> AreaCheck:
    """Return area evidence or raise when a split changes source totals."""
    child_units = list(children)
    if len(child_units) < 2:
        raise AssetUnitBoundaryInvalidError(
            reason="split_requires_two_results",
            unit_ids=[child.id for child in child_units],
        )
    _validate_effective_boundary(
        sources=[source],
        results=child_units,
        effective_date=effective_date,
    )
    source_totals = _sum_areas([source])
    result_totals = _sum_areas(child_units)
    check = AreaCheck(source=source_totals, result=result_totals)
    if source_totals != result_totals:
        raise AssetUnitAreaMismatchError(
            source=source_totals.as_dict(),
            result=result_totals.as_dict(),
        )
    return check


def validate_merge(
    *,
    sources: Iterable[AssetUnit],
    result: AssetUnit,
    coverages: Iterable[UpstreamContractAssetUnit],
    upstream_contracts: Iterable[UpstreamContract],
    lifecycle_events: Iterable[ContractLifecycleEvent],
    effective_date: date,
) -> AreaCheck:
    """Validate active upstream scope and area conservation for a merge."""
    source_units = list(sources)
    if len(source_units) < 2:
        raise AssetUnitBoundaryInvalidError(
            reason="merge_requires_two_sources",
            unit_ids=[source.id for source in source_units],
        )
    _validate_effective_boundary(
        sources=source_units,
        results=[result],
        effective_date=effective_date,
    )
    source_ids = {unit.id for unit in source_units}
    source_scopes: dict[str, set[str]] = {unit.id: set() for unit in source_units}
    active_contract_ids = active_upstream_contract_ids(
        contracts=upstream_contracts,
        lifecycle_events=lifecycle_events,
        effective_date=effective_date,
    )

    for coverage in coverages:
        if coverage.asset_unit_id not in source_ids:
            continue
        if coverage.upstream_contract_id not in active_contract_ids:
            continue
        if coverage.effective_from > effective_date:
            continue
        if coverage.effective_to is not None and coverage.effective_to < effective_date:
            continue
        source_scopes[coverage.asset_unit_id].add(coverage.upstream_contract_id)

    distinct_scopes = {frozenset(scope) for scope in source_scopes.values()}
    if len(distinct_scopes) != 1 or not next(iter(distinct_scopes), frozenset()):
        raise AssetUnitUpstreamScopeMismatchError(
            effective_date=effective_date.isoformat(),
            source_scopes={
                unit_id: sorted(contract_ids)
                for unit_id, contract_ids in source_scopes.items()
            },
        )

    source_totals = _sum_areas(source_units)
    result_totals = _sum_areas([result])
    check = AreaCheck(source=source_totals, result=result_totals)
    if source_totals != result_totals:
        raise AssetUnitAreaMismatchError(
            source=source_totals.as_dict(),
            result=result_totals.as_dict(),
        )
    return check


def _validate_effective_boundary(
    *,
    sources: Iterable[AssetUnit],
    results: Iterable[AssetUnit],
    effective_date: date,
) -> None:
    expected_source_end = effective_date - timedelta(days=1)
    invalid_source_ids = sorted(
        source.id for source in sources if source.managed_to != expected_source_end
    )
    if len(invalid_source_ids) > 0:
        raise AssetUnitBoundaryInvalidError(
            reason="source_end_date_mismatch",
            unit_ids=invalid_source_ids,
        )
    invalid_result_ids = sorted(
        result.id for result in results if result.managed_from != effective_date
    )
    if len(invalid_result_ids) > 0:
        raise AssetUnitBoundaryInvalidError(
            reason="result_start_date_mismatch",
            unit_ids=invalid_result_ids,
        )


def active_upstream_contract_ids(
    *,
    contracts: Iterable[UpstreamContract],
    lifecycle_events: Iterable[ContractLifecycleEvent],
    effective_date: date,
) -> set[str]:
    events = tuple(
        event
        for event in lifecycle_events
        if event.contract_kind == "upstream" and event.effective_date <= effective_date
    )
    reversed_event_ids = {
        event.reversed_event_id
        for event in events
        if event.event_type == "reversed" and event.reversed_event_id is not None
    }
    exited_contract_ids = {
        event.contract_id
        for event in events
        if event.event_type == "exited" and event.id not in reversed_event_ids
    }
    return {
        contract.id
        for contract in contracts
        if contract.start_date <= effective_date <= contract.end_date
        and contract.id not in exited_contract_ids
    }


def terminal_contract_conflict_ids(
    *,
    asset_unit_ids: set[str],
    contracts: Iterable[TerminalContract],
    coverages: Iterable[TerminalContractAssetUnit],
    lifecycle_events: Iterable[ContractLifecycleEvent],
    effective_date: date,
) -> tuple[str, ...]:
    """Return terminal contracts whose coverage crosses a boundary change."""
    event_snapshot = tuple(lifecycle_events)
    contracts_by_id = {contract.id: contract for contract in contracts}
    candidate_contract_ids = {
        coverage.terminal_contract_id
        for coverage in coverages
        if coverage.asset_unit_id in asset_unit_ids
        and (coverage.effective_to is None or coverage.effective_to >= effective_date)
    }
    return tuple(
        sorted(
            contract_id
            for contract_id in candidate_contract_ids
            if (contract := contracts_by_id.get(contract_id)) is not None
            and derive_terminal_contract_status(
                contract,
                as_of=effective_date,
                lifecycle_events=event_snapshot,
            )
            in {"scheduled", "active", "expiring"}
        )
    )


__all__ = [
    "AreaCheck",
    "AreaTotals",
    "active_upstream_contract_ids",
    "terminal_contract_conflict_ids",
    "validate_merge",
    "validate_split",
]
