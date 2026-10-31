"""Monthly occupancy-report draft lines and baseline comparison rules.

Lines come from explicit scope decisions plus month-end unit and rental
facts; the caller resolves operator identity, permissions and persistence.
Draft totals are re-derivable from the lines by construction.
"""

from __future__ import annotations

import calendar
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class ReportLineFact:
    unit_id: str
    managed_from: date
    managed_to: date | None
    is_operating: bool
    included: bool
    rented: bool
    land_area: Decimal
    building_area: Decimal
    rentable_area: Decimal
    owner_name: str
    usage_type: str
    project_name: str
    address: str
    terminal_contract_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class ReportLine:
    asset_unit_id: str
    owner_name_snapshot: str
    usage_type_snapshot: str
    project_name_snapshot: str
    address_snapshot: str
    land_area: Decimal
    building_area: Decimal
    rentable_area: Decimal
    rented_area: Decimal
    unit_count: int
    rented_unit_count: int
    rental_status: str  # "rented" | "vacant" | "non_rentable"
    terminal_contract_ids: list[str]


@dataclass(frozen=True)
class ReportAggregates:
    """The aggregate set a report is published and compared with."""

    unit_count: int
    rented_unit_count: int
    occupancy_rate: Decimal | None
    land_area: Decimal
    building_area: Decimal
    rentable_area: Decimal
    rented_area: Decimal
    scope_version_id: str | None = None


@dataclass(frozen=True)
class FieldChange:
    field_name: str
    previous: str | None
    current: str | None


def month_end(period: str) -> date:
    """Resolve the last calendar day of a ``YYYY-MM`` report month."""
    if re.fullmatch(r"[0-9]{4}-[0-9]{2}", period) is None:
        raise ValueError(f"Invalid period: {period}")
    try:
        first = date.fromisoformat(f"{period}-01")
    except ValueError as exc:
        raise ValueError(f"Invalid period: {period}") from exc
    return first.replace(day=calendar.monthrange(first.year, first.month)[1])


def build_report_lines(
    period: str, facts: Iterable[ReportLineFact]
) -> tuple[ReportLine, ...]:
    """One line per included, operating unit under management at month end."""
    end_of_month = month_end(period)
    materialized = tuple(facts)
    seen: set[str] = set()
    for unit in materialized:
        if unit.unit_id in seen:
            raise ValueError(f"Duplicate asset unit: {unit.unit_id}")
        seen.add(unit.unit_id)
    lines = []
    for unit in sorted(materialized, key=lambda row: row.unit_id):
        if not unit.is_operating or not unit.included:
            continue
        if unit.managed_from > end_of_month:
            continue
        if unit.managed_to is not None and unit.managed_to < end_of_month:
            continue
        if unit.rentable_area > 0:
            rental_status = "rented" if unit.rented else "vacant"
        else:
            rental_status = "non_rentable"
        lines.append(
            ReportLine(
                asset_unit_id=unit.unit_id,
                owner_name_snapshot=unit.owner_name,
                usage_type_snapshot=unit.usage_type,
                project_name_snapshot=unit.project_name,
                address_snapshot=unit.address,
                land_area=unit.land_area,
                building_area=unit.building_area,
                rentable_area=unit.rentable_area,
                rented_area=(
                    unit.rentable_area if unit.rented else Decimal("0")
                ),
                unit_count=1,
                rented_unit_count=1 if unit.rented else 0,
                rental_status=rental_status,
                terminal_contract_ids=list(unit.terminal_contract_ids),
            )
        )
    return tuple(lines)


def aggregates_from_lines(lines: Sequence[ReportLine]) -> ReportAggregates:
    """Recompute published totals so lines remain the single source."""
    unit_count = sum(line.unit_count for line in lines)
    rented_unit_count = sum(line.rented_unit_count for line in lines)
    return ReportAggregates(
        unit_count=unit_count,
        rented_unit_count=rented_unit_count,
        occupancy_rate=(
            Decimal(rented_unit_count) / Decimal(unit_count)
            if unit_count > 0
            else None
        ),
        land_area=sum((line.land_area for line in lines), Decimal(0)),
        building_area=sum((line.building_area for line in lines), Decimal(0)),
        rentable_area=sum((line.rentable_area for line in lines), Decimal(0)),
        rented_area=sum((line.rented_area for line in lines), Decimal(0)),
    )


# Stored occupancy_rate is Numeric(19,10); comparisons quantize to that
# scale so a full-precision 1/3 rate equals its stored counterpart instead
# of producing a phantom change every period.
_AGGREGATE_SCALE = Decimal("1E-10")
_QUANTIZED_FIELDS = ("occupancy_rate", "land_area", "building_area", "rentable_area", "rented_area")


def compare_with_baseline(
    current: ReportAggregates, baseline: ReportAggregates
) -> tuple[FieldChange, ...]:
    """Field-level diff of the five aggregates plus the scope version."""
    changes: list[FieldChange] = []
    pairs: tuple[tuple[str, object, object], ...] = (
        ("unit_count", baseline.unit_count, current.unit_count),
        ("rented_unit_count", baseline.rented_unit_count, current.rented_unit_count),
        ("occupancy_rate", baseline.occupancy_rate, current.occupancy_rate),
        ("land_area", baseline.land_area, current.land_area),
        ("building_area", baseline.building_area, current.building_area),
        ("rentable_area", baseline.rentable_area, current.rentable_area),
        ("rented_area", baseline.rented_area, current.rented_area),
        ("scope_version_id", baseline.scope_version_id, current.scope_version_id),
    )
    for name, previous, current_value in pairs:
        if name in _QUANTIZED_FIELDS:
            previous = _quantize(previous)
            current_value = _quantize(current_value)
        if not _values_equal(previous, current_value):
            changes.append(
                FieldChange(
                    field_name=name,
                    previous=_render(previous),
                    current=_render(current_value),
                )
            )
    return tuple(changes)


def _quantize(value: object) -> object:
    if not isinstance(value, Decimal):
        return value
    return value.quantize(_AGGREGATE_SCALE)


def _values_equal(previous: object, current: object) -> bool:
    if previous is None and current is None:
        return True
    if previous is None or current is None:
        return False
    return previous == current


def _render(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


__all__ = [
    "FieldChange",
    "ReportAggregates",
    "ReportLine",
    "ReportLineFact",
    "aggregates_from_lines",
    "build_report_lines",
    "compare_with_baseline",
    "month_end",
]


def project_counts(units: Sequence[ReportLineFact]) -> tuple[int, int, int]:
    """Split month-end managed projects into operating vs fully non-operating.

    The full set spans both operating and non-operating units under
    management at month end; the report lines only ever cover the operating
    included subset, so these counts are derived from the wider set.
    """
    projects: set[str] = set()
    operating_projects: set[str] = set()
    seen: set[str] = set()
    for unit in units:
        if unit.unit_id in seen:
            raise ValueError(f"Duplicate asset unit: {unit.unit_id}")
        seen.add(unit.unit_id)
        projects.add(unit.project_name)
        if unit.is_operating:
            operating_projects.add(unit.project_name)
    non_operating = projects - operating_projects
    return len(projects), len(operating_projects), len(non_operating)
