"""Rent comes only from actual stage rent and natural-month anchored periods."""

from datetime import date
from decimal import Decimal

import pytest

from src.services.asset_operations.rent_obligation_rules import (
    RentStage,
    generate_obligations,
)

pytestmark = pytest.mark.unit


def stage(start, end, rent="1000", cycle="monthly", due_day=25):
    return RentStage(
        date.fromisoformat(start),
        date.fromisoformat(end),
        Decimal(rent),
        cycle,
        due_day,
    )


def test_quarterly_uses_start_month_and_cross_stage_amounts():
    targets, gaps = generate_obligations(
        start_date=date(2026, 5, 1),
        end_date=date(2026, 12, 31),
        stages=[
            stage("2026-05-01", "2026-06-30", cycle="quarterly"),
            stage("2026-07-01", "2026-12-31", rent="2000", cycle="quarterly"),
        ],
    )
    assert not gaps
    assert [row.period for row in targets] == ["2026-05", "2026-08", "2026-11"]
    assert [row.due_amount for row in targets] == [
        Decimal("4000.00"),
        Decimal("6000.00"),
        Decimal("4000.00"),
    ]


def test_midmonth_stage_split_is_prorated_once_and_zero_periods_are_absent():
    targets, gaps = generate_obligations(
        start_date=date(2026, 1, 16),
        end_date=date(2026, 3, 15),
        stages=[
            stage("2026-01-16", "2026-01-31", rent="0"),
            stage("2026-02-01", "2026-02-14", rent="1000"),
            stage("2026-02-15", "2026-03-31", rent="2000"),
        ],
    )
    assert not gaps
    assert [row.period for row in targets] == ["2026-02", "2026-03"]
    assert [row.due_amount for row in targets] == [
        Decimal("1500.00"),
        Decimal("967.74"),
    ]
    assert targets[1].period_end == date(2026, 3, 15)


def test_custom_has_no_generated_rows_and_gaps_remain_visible():
    targets, gaps = generate_obligations(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 3, 31),
        stages=[
            stage("2026-01-01", "2026-01-31", cycle="custom"),
            stage("2026-03-10", "2026-03-31", due_day=5),
        ],
    )
    assert gaps == [(date(2026, 2, 1), date(2026, 3, 9))]
    assert len(targets) == 1
    assert targets[0].due_date == date(2026, 3, 10)


def test_yearly_emits_each_anchored_year_and_last_short_period():
    targets, _ = generate_obligations(
        start_date=date(2026, 5, 1),
        end_date=date(2028, 6, 30),
        stages=[stage("2026-05-01", "2028-06-30", cycle="yearly")],
    )
    assert [row.period for row in targets] == ["2026-05", "2027-05", "2028-05"]
    assert [row.due_amount for row in targets] == [
        Decimal("12000.00"),
        Decimal("12000.00"),
        Decimal("2000.00"),
    ]


def test_due_day_clamps_to_leap_month_end():
    targets, _ = generate_obligations(
        start_date=date(2028, 2, 1),
        end_date=date(2028, 2, 29),
        stages=[stage("2028-02-01", "2028-02-29", due_day=31)],
    )
    assert targets[0].due_date == date(2028, 2, 29)
