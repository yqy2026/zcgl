"""Full managed-property totals remain separate from assessment denominators."""

from decimal import Decimal

import pytest

from src.services.asset_operations.occupancy_report_draft_rules import (
    FullScopeUnitFact,
    ReportAggregates,
    aggregates_with_full_scope,
    full_scope_project_counts,
)

pytestmark = pytest.mark.unit


def test_full_scope_areas_include_non_operating_and_excluded_units() -> None:
    scope = (
        FullScopeUnitFact(
            "in", "Included", "same-id", "Same", True, Decimal("10"), Decimal("20")
        ),
        FullScopeUnitFact(
            "excluded",
            "Excluded",
            "other-id",
            "Same",
            True,
            Decimal("30"),
            Decimal("40"),
        ),
        FullScopeUnitFact(
            "public",
            "Public",
            "public-id",
            "Public",
            False,
            Decimal("50"),
            Decimal("60"),
        ),
        FullScopeUnitFact(
            "unassigned", "Unassigned", None, "", True, Decimal("70"), Decimal("80")
        ),
    )
    base = ReportAggregates(
        1, 1, Decimal("1"), Decimal("10"), Decimal("20"), Decimal("15"), Decimal("15")
    )
    totals = aggregates_with_full_scope(base, scope)
    assert totals.land_area == Decimal("160")
    assert totals.building_area == Decimal("200")
    assert (totals.unit_count, totals.rented_unit_count, totals.occupancy_rate) == (
        1,
        1,
        Decimal("1"),
    )
    assert (totals.rentable_area, totals.rented_area) == (Decimal("15"), Decimal("15"))
    assert full_scope_project_counts(scope) == (3, 2, 1)


def test_mixed_project_counts_once_as_operating() -> None:
    rows = (
        FullScopeUnitFact("a", "A", "one", "P", False, Decimal(0), Decimal(0)),
        FullScopeUnitFact("b", "B", "one", "P", True, Decimal(0), Decimal(0)),
    )
    assert full_scope_project_counts(rows) == (1, 1, 0)


def test_duplicate_full_scope_unit_fails_loud() -> None:
    row = FullScopeUnitFact("a", "A", None, "", False, Decimal(0), Decimal(0))
    with pytest.raises(ValueError, match="Duplicate asset unit"):
        full_scope_project_counts((row, row))
