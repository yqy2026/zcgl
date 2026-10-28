"""Deterministic actual-rent allocation over natural-month anchored periods."""

from __future__ import annotations

import calendar
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

MONEY_QUANTUM = Decimal("0.01")


@dataclass(frozen=True)
class RentStage:
    stage_start: date
    stage_end: date
    actual_monthly_rent: Decimal
    payment_cycle: str
    due_day: int
    source_id: str = ""


@dataclass(frozen=True)
class ObligationTarget:
    period: str
    period_start: date
    period_end: date
    due_date: date
    due_amount: Decimal
    source_schedule_ids: tuple[str, ...] = ()


def month_start(value: date) -> date:
    return value.replace(day=1)


def add_months(value: date, count: int) -> date:
    month_index = value.year * 12 + value.month - 1 + count
    return date(month_index // 12, month_index % 12 + 1, 1)


def _amount_for_range(stages: Sequence[RentStage], start: date, end: date) -> Decimal:
    total = Decimal("0")
    for stage in stages:
        cursor = max(start, stage.stage_start)
        last = min(end, stage.stage_end)
        while cursor <= last:
            days_in_month = calendar.monthrange(cursor.year, cursor.month)[1]
            month_end = cursor.replace(day=days_in_month)
            covered_end = min(last, month_end)
            total += (
                stage.actual_monthly_rent
                * Decimal((covered_end - cursor).days + 1)
                / Decimal(days_in_month)
            )
            if covered_end == last:
                break
            cursor = covered_end + timedelta(days=1)
    return total.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def generate_obligations(
    *, start_date: date, end_date: date, stages: Sequence[RentStage]
) -> tuple[list[ObligationTarget], list[tuple[date, date]]]:
    """Return positive obligations and uncovered ranges; custom stages count as covered."""
    if end_date < start_date:
        return [], []
    active = sorted(
        (
            stage
            for stage in stages
            if stage.stage_start <= end_date and stage.stage_end >= start_date
        ),
        key=lambda stage: stage.stage_start,
    )
    gaps: list[tuple[date, date]] = []
    covered_until = start_date - timedelta(days=1)
    groups: list[list[RentStage]] = []
    for stage in active:
        if (
            stage.stage_end < stage.stage_start
            or stage.payment_cycle not in {"monthly", "quarterly", "yearly", "custom"}
            or not 1 <= stage.due_day <= 31
        ):
            raise ValueError("Invalid rent stage")
        clipped_start, clipped_end = (
            max(start_date, stage.stage_start),
            min(end_date, stage.stage_end),
        )
        if clipped_start <= covered_until:
            raise ValueError("Overlapping rent stages")
        if clipped_start > covered_until + timedelta(days=1):
            gaps.append(
                (covered_until + timedelta(days=1), clipped_start - timedelta(days=1))
            )
        if (
            groups
            and groups[-1][-1].payment_cycle == stage.payment_cycle
            and groups[-1][-1].stage_end + timedelta(days=1) == stage.stage_start
        ):
            groups[-1].append(stage)
        else:
            groups.append([stage])
        covered_until = clipped_end
    if covered_until < end_date:
        gaps.append((covered_until + timedelta(days=1), end_date))
    targets: list[ObligationTarget] = []
    for group in groups:
        cycle = group[0].payment_cycle
        if cycle == "custom":
            continue
        length = {"monthly": 1, "quarterly": 3, "yearly": 12}[cycle]
        segment_start = max(start_date, group[0].stage_start)
        segment_end = min(end_date, group[-1].stage_end)
        anchor = month_start(segment_start)
        cursor = segment_start
        while cursor <= segment_end:
            next_start = add_months(anchor, length)
            last = min(segment_end, next_start - timedelta(days=1))
            amount = _amount_for_range(group, cursor, last)
            if amount > 0:
                first_stage = next(
                    stage
                    for stage in group
                    if stage.stage_start <= cursor <= stage.stage_end
                )
                due = cursor.replace(
                    day=min(
                        first_stage.due_day,
                        calendar.monthrange(cursor.year, cursor.month)[1],
                    )
                )
                targets.append(
                    ObligationTarget(
                        period=cursor.strftime("%Y-%m"),
                        period_start=cursor,
                        period_end=last,
                        due_date=max(cursor, due),
                        due_amount=amount,
                        source_schedule_ids=tuple(
                            stage.source_id
                            for stage in group
                            if stage.stage_start <= last
                            and stage.stage_end >= cursor
                            and stage.source_id
                        ),
                    )
                )
            cursor, anchor = next_start, next_start
    return targets, gaps
