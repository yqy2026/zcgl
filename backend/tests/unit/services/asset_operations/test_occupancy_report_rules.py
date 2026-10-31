"""Operating assessment statistics count asset units, never contracts."""

from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from src.services.asset_operations.occupancy_report_rules import (
    OccupancyUnitFact,
    project_occupancy,
)

pytestmark = pytest.mark.unit


def unit(unit_id: str = "a") -> OccupancyUnitFact:
    return OccupancyUnitFact(
        unit_id=unit_id,
        managed_from=date(2020, 1, 1),
        managed_to=None,
        is_operating=True,
        included=True,
        rented=True,
        land_area=Decimal("0.1"),
        building_area=Decimal("20.25"),
        rentable_area=Decimal("15.125"),
    )


def test_counts_two_units_without_grouping_by_contract_or_project() -> None:
    result = project_occupancy("2026-10", (unit(), replace(unit("b"), rented=False)))
    assert result.unit_count == 2
    assert result.rented_unit_count == 1
    assert result.occupancy_rate == Decimal("0.5")
    assert result.land_area == Decimal("0.2")
    assert result.building_area == Decimal("40.50")
    assert result.rentable_area == Decimal("30.250")
    assert result.rented_area == Decimal("15.125")


@pytest.mark.parametrize(
    "units",
    [
        (),
        (replace(unit(), included=False),),
        (replace(unit(), included=None),),
        (replace(unit(), is_operating=False),),
    ],
)
def test_empty_denominator_has_no_rate(units: tuple[OccupancyUnitFact, ...]) -> None:
    result = project_occupancy("2026-10", units)
    assert result.unit_count == 0
    assert result.rented_unit_count == 0
    assert result.occupancy_rate is None
    assert (
        result.land_area
        == result.building_area
        == result.rentable_area
        == result.rented_area
        == Decimal(0)
    )


@pytest.mark.parametrize(
    "period,last_day",
    [
        ("2024-02", date(2024, 2, 29)),
        ("2026-02", date(2026, 2, 28)),
        ("2026-10", date(2026, 10, 31)),
    ],
)
def test_only_month_end_in_management_counts(period: str, last_day: date) -> None:
    from datetime import timedelta

    result = project_occupancy(
        period,
        (
            replace(unit("start"), managed_from=last_day),
            replace(unit("end"), managed_to=last_day),
            replace(unit("future"), managed_from=last_day + timedelta(days=1)),
            replace(unit("past"), managed_to=last_day - timedelta(days=1)),
        ),
    )
    assert result.unit_count == 2
    assert result.rented_unit_count == 2


def test_duplicate_unit_identity_is_rejected_even_when_excluded() -> None:
    with pytest.raises(ValueError, match="Duplicate asset unit"):
        project_occupancy("2026-10", (unit(), replace(unit(), included=False)))


@pytest.mark.parametrize(
    "period", ["2026-1", "2026-13", "2026-00", "2026-10-01", "not-a-month"]
)
def test_invalid_period_is_rejected(period: str) -> None:
    with pytest.raises(ValueError, match="Invalid period"):
        project_occupancy(period, ())


def test_decimal_totals_and_rate_are_not_rounded_for_display() -> None:
    result = project_occupancy(
        "2026-10",
        (
            unit(),
            replace(unit("b"), rented=False),
            replace(unit("c"), rented=False),
        ),
    )
    assert result.land_area == Decimal("0.3")
    assert result.rentable_area == Decimal("45.375")
    assert result.occupancy_rate == Decimal("0.3333333333333333333333333333")


def test_generator_input_is_not_exhausted_by_the_duplicate_scan() -> None:
    result = project_occupancy("2026-10", (unit() for _ in range(1)))
    assert result.unit_count == 1
    assert result.rented_unit_count == 1
