"""Monthly draft lines derive from explicit decisions and month-end facts."""

from datetime import date
from decimal import Decimal

import pytest

from src.services.asset_operations.occupancy_report_draft_rules import (
    ReportAggregates,
    ReportLineFact,
    aggregates_from_lines,
    build_report_lines,
    compare_with_baseline,
    month_end,
)

pytestmark = pytest.mark.unit


def fact(
    unit_id: str = "a",
    *,
    managed_from: date = date(2020, 1, 1),
    managed_to: date | None = None,
    is_operating: bool = True,
    included: bool = True,
    rented: bool = False,
    building_area: Decimal = Decimal("100"),
    rentable_area: Decimal = Decimal("80"),
    owner_name: str = "产权方甲",
    usage_type: str = "commercial",
    project_name: str = "项目一",
    address: str = "地址一",
    terminal_contract_ids: tuple[str, ...] = (),
) -> ReportLineFact:
    return ReportLineFact(
        unit_id=unit_id,
        managed_from=managed_from,
        managed_to=managed_to,
        is_operating=is_operating,
        included=included,
        rented=rented,
        land_area=Decimal("0.5"),
        building_area=building_area,
        rentable_area=rentable_area,
        owner_name=owner_name,
        usage_type=usage_type,
        project_name=project_name,
        address=address,
        terminal_contract_ids=terminal_contract_ids,
    )


def test_lines_cover_only_included_month_end_managed_units() -> None:
    lines = build_report_lines(
        "2026-10",
        (
            fact("in"),
            fact("out", included=False),
            fact("ended", managed_to=date(2026, 10, 30)),
            fact("future", managed_from=date(2026, 11, 1)),
            fact("nonop", is_operating=False),
        ),
    )
    assert [line.asset_unit_id for line in lines] == ["in"]


def test_line_status_and_rented_area_follow_rental_fact() -> None:
    lines = build_report_lines(
        "2026-10",
        (
            fact("rented", rented=True, terminal_contract_ids=("t1", "t2")),
            fact("vacant", rentable_area=Decimal("10")),
            fact("nonrentable", rentable_area=Decimal("0")),
        ),
    )
    by_id = {line.asset_unit_id: line for line in lines}
    assert by_id["rented"].rental_status == "rented"
    assert by_id["rented"].rented_unit_count == 1
    assert by_id["rented"].rented_area == by_id["rented"].rentable_area
    assert by_id["rented"].terminal_contract_ids == ["t1", "t2"]
    assert by_id["vacant"].rental_status == "vacant"
    assert by_id["vacant"].rented_area == Decimal("0")
    assert by_id["nonrentable"].rental_status == "non_rentable"


def test_lines_recompute_the_published_totals() -> None:
    facts = (
        fact("a", rented=True, building_area=Decimal("100"), rentable_area=Decimal("80")),
        fact("b", rented=False, building_area=Decimal("60"), rentable_area=Decimal("50")),
    )
    lines = build_report_lines("2026-10", facts)
    assert len(lines) == 2
    assert sum(line.unit_count for line in lines) == 2
    assert sum(line.rented_unit_count for line in lines) == 1
    assert sum(line.land_area for line in lines) == Decimal("1.0")
    assert sum(line.building_area for line in lines) == Decimal("160")
    assert sum(line.rentable_area for line in lines) == Decimal("130")
    assert sum(line.rented_area for line in lines) == Decimal("80")


def test_line_order_is_stable_by_unit_id() -> None:
    lines = build_report_lines("2026-10", (fact("z"), fact("a"), fact("m")))
    assert [line.asset_unit_id for line in lines] == ["a", "m", "z"]


def test_duplicate_units_are_rejected() -> None:
    with pytest.raises(ValueError, match="Duplicate asset unit"):
        build_report_lines("2026-10", (fact("dup"), fact("dup")))


def test_invalid_period_is_rejected() -> None:
    with pytest.raises(ValueError, match="Invalid period"):
        build_report_lines("2026-13", (fact(),))


def test_month_end_covers_leap_and_short_months() -> None:
    assert month_end("2024-02") == date(2024, 2, 29)
    assert month_end("2026-02") == date(2026, 2, 28)
    assert month_end("2026-10") == date(2026, 10, 31)


def test_compare_flags_only_changed_aggregates_and_scope_version() -> None:
    current = ReportAggregates(
        unit_count=3,
        rented_unit_count=1,
        occupancy_rate=Decimal("0.3333"),
        land_area=Decimal("1.5"),
        building_area=Decimal("200"),
        rentable_area=Decimal("150"),
        rented_area=Decimal("80"),
        scope_version_id="ver-2",
    )
    baseline = ReportAggregates(
        unit_count=3,
        rented_unit_count=2,
        occupancy_rate=Decimal("0.6667"),
        land_area=Decimal("1.5"),
        building_area=Decimal("200"),
        rentable_area=Decimal("150"),
        rented_area=Decimal("80"),
        scope_version_id="ver-1",
    )
    changes = compare_with_baseline(current, baseline)
    assert [change.field_name for change in changes] == [
        "rented_unit_count",
        "occupancy_rate",
        "scope_version_id",
    ]


def test_same_scope_version_is_not_flagged() -> None:
    current = ReportAggregates(
        unit_count=3,
        rented_unit_count=2,
        occupancy_rate=Decimal("0.6667"),
        land_area=Decimal("1.5"),
        building_area=Decimal("200"),
        rentable_area=Decimal("150"),
        rented_area=Decimal("80"),
        scope_version_id="ver-1",
    )
    baseline = ReportAggregates(
        unit_count=3,
        rented_unit_count=2,
        occupancy_rate=Decimal("0.6667"),
        land_area=Decimal("1.5"),
        building_area=Decimal("200"),
        rentable_area=Decimal("150"),
        rented_area=Decimal("80"),
        scope_version_id="ver-1",
    )
    assert compare_with_baseline(current, baseline) == ()


def test_compare_treats_missing_rate_and_zero_identically() -> None:
    current = ReportAggregates(
        unit_count=0,
        rented_unit_count=0,
        occupancy_rate=None,
        land_area=Decimal("0"),
        building_area=Decimal("0"),
        rentable_area=Decimal("0"),
        rented_area=Decimal("0"),
    )
    baseline = ReportAggregates(
        unit_count=0,
        rented_unit_count=0,
        occupancy_rate=None,
        land_area=Decimal("0"),
        building_area=Decimal("0"),
        rentable_area=Decimal("0"),
        rented_area=Decimal("0"),
        scope_version_id=None,
    )
    assert compare_with_baseline(current, baseline) == ()
    assert [c.field_name for c in compare_with_baseline(current, baseline)] == []


def test_full_precision_rate_matches_stored_scale_without_phantom_change() -> None:
    """1/3 stored at Numeric(19,10) equals the full-precision derived rate."""
    stored = (Decimal(1) / Decimal(3)).quantize(Decimal("1E-10"))
    current = ReportAggregates(
        unit_count=3,
        rented_unit_count=1,
        occupancy_rate=Decimal(1) / Decimal(3),
        land_area=Decimal("0"),
        building_area=Decimal("0"),
        rentable_area=Decimal("0"),
        rented_area=Decimal("0"),
        scope_version_id="ver-1",
    )
    baseline = ReportAggregates(
        unit_count=3,
        rented_unit_count=1,
        occupancy_rate=stored,
        land_area=Decimal("0"),
        building_area=Decimal("0"),
        rentable_area=Decimal("0"),
        rented_area=Decimal("0"),
        scope_version_id="ver-1",
    )
    assert compare_with_baseline(current, baseline) == ()


def test_rate_differs_only_beyond_stored_scale_is_not_a_change() -> None:
    current = ReportAggregates(
        unit_count=6,
        rented_unit_count=2,
        occupancy_rate=Decimal(1) / Decimal(3),
        land_area=Decimal("0"),
        building_area=Decimal("0"),
        rentable_area=Decimal("0"),
        rented_area=Decimal("0"),
        scope_version_id="ver-1",
    )
    baseline = ReportAggregates(
        unit_count=6,
        rented_unit_count=2,
        occupancy_rate=Decimal("0.3333333333"),
        land_area=Decimal("0"),
        building_area=Decimal("0"),
        rentable_area=Decimal("0"),
        rented_area=Decimal("0"),
        scope_version_id="ver-1",
    )
    assert compare_with_baseline(current, baseline) == ()


def test_empty_lines_have_zero_denominator_and_null_rate() -> None:
    aggregates = aggregates_from_lines(())
    assert aggregates.unit_count == 0
    assert aggregates.rented_unit_count == 0
    assert aggregates.occupancy_rate is None
    assert (
        aggregates.land_area
        == aggregates.building_area
        == aggregates.rentable_area
        == aggregates.rented_area
        == Decimal(0)
    )


def test_project_counts_split_operating_and_non_operating_projects() -> None:
    from src.services.asset_operations.occupancy_report_draft_rules import (
        project_counts,
    )

    facts = (
        ReportLineFact(
            unit_id="op1",
            managed_from=date(2026, 1, 1),
            managed_to=None,
            is_operating=True,
            included=True,
            rented=False,
            land_area=Decimal("0"),
            building_area=Decimal("1"),
            rentable_area=Decimal("1"),
            owner_name="o",
            usage_type="u",
            project_name="项目甲",
            address="a",
        ),
        ReportLineFact(
            unit_id="op2",
            managed_from=date(2026, 1, 1),
            managed_to=None,
            is_operating=True,
            included=True,
            rented=False,
            land_area=Decimal("0"),
            building_area=Decimal("1"),
            rentable_area=Decimal("1"),
            owner_name="o",
            usage_type="u",
            project_name="项目甲",
            address="a",
        ),
        ReportLineFact(
            unit_id="nonop",
            managed_from=date(2026, 1, 1),
            managed_to=None,
            is_operating=False,
            included=False,
            rented=False,
            land_area=Decimal("0"),
            building_area=Decimal("1"),
            rentable_area=Decimal("0"),
            owner_name="o",
            usage_type="u",
            project_name="项目乙",
            address="a",
        ),
        ReportLineFact(
            unit_id="nonop2",
            managed_from=date(2026, 1, 1),
            managed_to=None,
            is_operating=False,
            included=False,
            rented=False,
            land_area=Decimal("0"),
            building_area=Decimal("1"),
            rentable_area=Decimal("0"),
            owner_name="o",
            usage_type="u",
            project_name="项目乙",
            address="a",
        ),
    )
    assert project_counts(facts) == (2, 1, 1)
    assert project_counts(()) == (0, 0, 0)
