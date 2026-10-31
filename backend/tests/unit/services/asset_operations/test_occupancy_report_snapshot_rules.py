"""Snapshot-vs-current diff derives per-unit field changes, never rewrites."""

from datetime import date
from decimal import Decimal

import pytest

from src.services.asset_operations.occupancy_report_snapshot_rules import (
    CurrentLine,
    SnapshotLine,
    diff_snapshot_against_current,
)

pytestmark = pytest.mark.unit


def snapshot(
    unit_id: str = "a",
    *,
    owner_name: str = "产权方甲",
    usage_type: str = "commercial",
    project_name: str = "项目一",
    address: str = "地址一",
    land_area: Decimal = Decimal("1.0"),
    building_area: Decimal = Decimal("100"),
    rentable_area: Decimal = Decimal("80"),
    rented_area: Decimal = Decimal("0"),
    rented_unit_count: int = 0,
    rental_status: str = "vacant",
    terminal_contract_ids: tuple[str, ...] = (),
) -> SnapshotLine:
    return SnapshotLine(
        asset_unit_id=unit_id,
        owner_name_snapshot=owner_name,
        usage_type_snapshot=usage_type,
        project_name_snapshot=project_name,
        address_snapshot=address,
        land_area=land_area,
        building_area=building_area,
        rentable_area=rentable_area,
        rented_area=rented_area,
        rented_unit_count=rented_unit_count,
        rental_status=rental_status,
        terminal_contract_ids=list(terminal_contract_ids),
    )


def current(
    unit_id: str = "a",
    *,
    owner_name: str = "产权方甲",
    usage_type: str = "commercial",
    project_name: str = "项目一",
    address: str = "地址一",
    land_area: Decimal = Decimal("1.0"),
    building_area: Decimal = Decimal("100"),
    rentable_area: Decimal = Decimal("80"),
    rented_area: Decimal = Decimal("0"),
    rented_unit_count: int = 0,
    rental_status: str = "vacant",
    terminal_contract_ids: tuple[str, ...] = (),
) -> CurrentLine:
    return CurrentLine(
        asset_unit_id=unit_id,
        owner_name=owner_name,
        usage_type=usage_type,
        project_name=project_name,
        address=address,
        land_area=land_area,
        building_area=building_area,
        rentable_area=rentable_area,
        rented_area=rented_area,
        rented_unit_count=rented_unit_count,
        rental_status=rental_status,
        terminal_contract_ids=list(terminal_contract_ids),
    )


def test_identical_snapshot_and_current_has_no_differences() -> None:
    diff = diff_snapshot_against_current((snapshot(),), (current(),))
    assert diff == ()


def test_changed_fields_are_listed_per_unit() -> None:
    diff = diff_snapshot_against_current(
        (snapshot(rentable_area=Decimal("80"), rental_status="vacant"),),
        (
            current(
                rentable_area=Decimal("70"),
                rental_status="rented",
                rented_area=Decimal("70"),
                rented_unit_count=1,
                terminal_contract_ids=("t1",),
            ),
        ),
    )
    assert len(diff) == 1
    entry = diff[0]
    assert entry.asset_unit_id == "a"
    changed = {change.field_name for change in entry.changes}
    assert changed == {
        "rentable_area",
        "rented_area",
        "rented_unit_count",
        "rental_status",
        "terminal_contract_ids",
    }


def test_units_only_in_snapshot_or_only_in_current_are_reported() -> None:
    diff = diff_snapshot_against_current(
        (snapshot("kept"), snapshot("removed")),
        (current("kept"), current("added")),
    )
    by_unit = {entry.asset_unit_id: entry for entry in diff}
    assert set(by_unit) == {"removed", "added"}
    assert by_unit["removed"].kind == "unit_left_scope"
    assert by_unit["added"].kind == "unit_entered_scope"
    assert by_unit["removed"].changes == ()
    assert by_unit["added"].changes == ()


def test_areas_compare_at_stored_scale_not_full_precision() -> None:
    diff = diff_snapshot_against_current(
        (snapshot(land_area=Decimal("1.0000000000"), building_area=Decimal("100.00")),),
        (current(land_area=Decimal("1"), building_area=Decimal("100.0000000000")),),
    )
    assert diff == ()


def test_duplicate_snapshot_units_are_rejected() -> None:
    with pytest.raises(ValueError, match="Duplicate"):
        diff_snapshot_against_current((snapshot(), snapshot()), (current(),))
    with pytest.raises(ValueError, match="Duplicate"):
        diff_snapshot_against_current((snapshot(),), (current(), current()))


def test_unmanaged_before_month_end_snapshot_still_diffs_by_unit_id() -> None:
    """The diff is identity-based; managed windows are resolved upstream."""

    diff = diff_snapshot_against_current((snapshot("x"),), ())
    assert len(diff) == 1
    assert diff[0].kind == "unit_left_scope"
    _ = date(2026, 1, 1)
