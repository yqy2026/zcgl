"""Asset-unit split and merge rules at the service seam."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from src.models.asset_contract import (
    ContractLifecycleEvent,
    TerminalContract,
    TerminalContractAssetUnit,
    UpstreamContract,
    UpstreamContractAssetUnit,
)
from src.models.asset_unit import AssetUnit
from src.services.asset_operations.boundary_rules import (
    terminal_contract_conflict_ids,
    validate_merge,
    validate_split,
)
from src.services.asset_operations.errors import (
    AssetUnitAreaMismatchError,
    AssetUnitBoundaryInvalidError,
    AssetUnitUpstreamScopeMismatchError,
)


def _unit(
    unit_id: str,
    *,
    building_area: str,
    rentable_area: str,
    land_area: str = "0",
    managed_from: date = date(2026, 1, 1),
    managed_to: date | None = None,
) -> AssetUnit:
    return AssetUnit(
        id=unit_id,
        unit_code=unit_id.upper(),
        name=unit_id,
        project_id="project-1",
        owner_party_id="owner-1",
        address="测试地址",
        usage_type="商铺",
        acquisition_mode="leased",
        land_area=Decimal(land_area),
        building_area=Decimal(building_area),
        rentable_area=Decimal(rentable_area),
        managed_from=managed_from,
        managed_to=managed_to,
    )


def _coverage(
    *,
    unit_id: str,
    contract_id: str,
    effective_from: date = date(2026, 1, 1),
    effective_to: date | None = None,
) -> UpstreamContractAssetUnit:
    return UpstreamContractAssetUnit(
        asset_unit_id=unit_id,
        upstream_contract_id=contract_id,
        effective_from=effective_from,
        effective_to=effective_to,
    )


def _upstream(
    contract_id: str,
    *,
    start_date: date = date(2026, 1, 1),
    end_date: date = date(2026, 12, 31),
) -> UpstreamContract:
    return UpstreamContract(
        id=contract_id,
        contract_number=f"UP-{contract_id}",
        contract_type="lease",
        name=contract_id,
        owner_party_id="owner-1",
        operator_party_id="operator-1",
        start_date=start_date,
        end_date=end_date,
        payment_cycle="monthly",
        payment_day=1,
        deposit_amount=Decimal("0"),
        scan_document_id="scan-1",
    )


def _merge_units(*, effective_date: date) -> tuple[list[AssetUnit], AssetUnit]:
    sources = [
        _unit(
            "source-1",
            building_area="50",
            rentable_area="40",
            managed_to=date(2026, 5, 31),
        ),
        _unit(
            "source-2",
            building_area="50",
            rentable_area="40",
            managed_to=date(2026, 5, 31),
        ),
    ]
    result = _unit(
        "result",
        building_area="100",
        rentable_area="80",
        managed_from=effective_date,
    )
    return sources, result


def test_split_rejects_area_mismatch_with_stable_conflict() -> None:
    effective_date = date(2026, 6, 1)
    source = _unit(
        "source",
        building_area="100",
        rentable_area="80",
        managed_to=date(2026, 5, 31),
    )
    children = [
        _unit(
            "child-1",
            building_area="50",
            rentable_area="40",
            managed_from=effective_date,
        ),
        _unit(
            "child-2",
            building_area="45",
            rentable_area="40",
            managed_from=effective_date,
        ),
    ]

    with pytest.raises(AssetUnitAreaMismatchError) as error:
        validate_split(
            source=source,
            children=children,
            effective_date=effective_date,
        )

    assert error.value.status_code == 409
    assert error.value.code == "ASSET_UNIT_AREA_MISMATCH"
    assert error.value.details == {
        "source": {
            "land_area": "0.00",
            "building_area": "100.00",
            "rentable_area": "80.00",
        },
        "result": {
            "land_area": "0.00",
            "building_area": "95.00",
            "rentable_area": "80.00",
        },
    }


def test_split_rejects_single_result_and_invalid_effective_boundary() -> None:
    effective_date = date(2026, 6, 1)
    source = _unit(
        "source",
        building_area="100",
        rentable_area="80",
        managed_to=date(2026, 5, 31),
    )

    with pytest.raises(AssetUnitBoundaryInvalidError) as cardinality_error:
        validate_split(
            source=source,
            children=[
                _unit(
                    "child-1",
                    building_area="100",
                    rentable_area="80",
                    managed_from=effective_date,
                )
            ],
            effective_date=effective_date,
        )

    assert cardinality_error.value.code == "ASSET_UNIT_BOUNDARY_INVALID"
    assert cardinality_error.value.details["reason"] == "split_requires_two_results"

    with pytest.raises(AssetUnitBoundaryInvalidError) as date_error:
        validate_split(
            source=source,
            children=[
                _unit("child-1", building_area="50", rentable_area="40"),
                _unit("child-2", building_area="50", rentable_area="40"),
            ],
            effective_date=effective_date,
        )

    assert date_error.value.code == "ASSET_UNIT_BOUNDARY_INVALID"
    assert date_error.value.details["reason"] == "result_start_date_mismatch"


def test_merge_rejects_different_active_upstream_scopes() -> None:
    effective_date = date(2026, 6, 1)
    sources, result = _merge_units(effective_date=effective_date)
    coverages = [
        _coverage(unit_id="source-1", contract_id="upstream-1"),
        _coverage(unit_id="source-2", contract_id="upstream-2"),
    ]

    with pytest.raises(AssetUnitUpstreamScopeMismatchError) as error:
        validate_merge(
            sources=sources,
            result=result,
            coverages=coverages,
            upstream_contracts=[_upstream("upstream-1"), _upstream("upstream-2")],
            lifecycle_events=[],
            effective_date=effective_date,
        )

    assert error.value.status_code == 409
    assert error.value.code == "ASSET_UNIT_UPSTREAM_SCOPE_MISMATCH"
    assert error.value.details == {
        "effective_date": "2026-06-01",
        "source_scopes": {
            "source-1": ["upstream-1"],
            "source-2": ["upstream-2"],
        },
    }


def test_merge_accepts_same_non_empty_active_upstream_scope_and_conserved_area() -> (
    None
):
    effective_date = date(2026, 6, 1)
    sources, result = _merge_units(effective_date=effective_date)
    coverages = [
        _coverage(unit_id="source-1", contract_id="upstream-1"),
        _coverage(unit_id="source-2", contract_id="upstream-1"),
        _coverage(
            unit_id="source-2",
            contract_id="expired-upstream",
            effective_to=date(2026, 5, 31),
        ),
    ]

    check = validate_merge(
        sources=sources,
        result=result,
        coverages=coverages,
        upstream_contracts=[
            _upstream("upstream-1"),
            _upstream("expired-upstream", end_date=date(2026, 5, 31)),
        ],
        lifecycle_events=[],
        effective_date=effective_date,
    )

    assert check.source.as_dict()["building_area"] == "100.00"
    assert check.result.as_dict()["building_area"] == "100.00"


def test_merge_rejects_coverage_whose_upstream_contract_is_expired_or_exited() -> None:
    effective_date = date(2026, 6, 1)
    sources, result = _merge_units(effective_date=effective_date)
    coverages = [
        _coverage(unit_id="source-1", contract_id="upstream-1"),
        _coverage(unit_id="source-2", contract_id="upstream-1"),
    ]
    exited = ContractLifecycleEvent(
        id="event-1",
        contract_kind="upstream",
        contract_id="upstream-1",
        event_type="exited",
        effective_date=date(2026, 5, 31),
        reason="已退出",
        created_by="user-1",
        idempotency_key="exit-upstream-1",
    )

    with pytest.raises(AssetUnitUpstreamScopeMismatchError):
        validate_merge(
            sources=sources,
            result=result,
            coverages=coverages,
            upstream_contracts=[_upstream("upstream-1")],
            lifecycle_events=[exited],
            effective_date=effective_date,
        )

    with pytest.raises(AssetUnitUpstreamScopeMismatchError):
        validate_merge(
            sources=sources,
            result=result,
            coverages=coverages,
            upstream_contracts=[_upstream("upstream-1", end_date=date(2026, 5, 31))],
            lifecycle_events=[],
            effective_date=effective_date,
        )


def test_merge_rejects_single_source() -> None:
    effective_date = date(2026, 6, 1)
    sources, result = _merge_units(effective_date=effective_date)

    with pytest.raises(AssetUnitBoundaryInvalidError) as error:
        validate_merge(
            sources=[sources[0]],
            result=result,
            coverages=[_coverage(unit_id="source-1", contract_id="upstream-1")],
            upstream_contracts=[_upstream("upstream-1")],
            lifecycle_events=[],
            effective_date=effective_date,
        )

    assert error.value.code == "ASSET_UNIT_BOUNDARY_INVALID"
    assert error.value.details["reason"] == "merge_requires_two_sources"


def test_terminal_coverage_starting_after_boundary_is_a_conflict() -> None:
    effective_date = date(2026, 6, 1)
    contract = TerminalContract(
        id="terminal-1",
        contract_number="TM-001",
        contract_mode="sublease",
        tenant_party_id="tenant-1",
        lessor_party_id="operator-1",
        upstream_contract_id="upstream-1",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        deposit_amount=Decimal("0"),
        rent_collector="operator",
        scan_document_id="scan-terminal",
    )

    conflicts = terminal_contract_conflict_ids(
        asset_unit_ids={"source-1"},
        contracts=[contract],
        coverages=[
            TerminalContractAssetUnit(
                terminal_contract_id=contract.id,
                asset_unit_id="source-1",
                effective_from=date(2026, 7, 1),
            )
        ],
        lifecycle_events=[],
        effective_date=effective_date,
    )

    assert conflicts == ("terminal-1",)
