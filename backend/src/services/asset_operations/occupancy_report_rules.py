"""Operating assessment totals from explicit scope and month-end rental facts.

Callers resolve the operator, permissions, scope version and rental status.
These totals exclude non-operating property and are not full report totals.
"""

from __future__ import annotations

import calendar
import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class OccupancyUnitFact:
    unit_id: str
    managed_from: date
    managed_to: date | None
    is_operating: bool
    included: bool | None
    rented: bool
    land_area: Decimal
    building_area: Decimal
    rentable_area: Decimal


@dataclass(frozen=True)
class OccupancyProjection:
    unit_count: int
    rented_unit_count: int
    occupancy_rate: Decimal | None
    land_area: Decimal
    building_area: Decimal
    rentable_area: Decimal
    rented_area: Decimal


def project_occupancy(
    period: str, units: Iterable[OccupancyUnitFact]
) -> OccupancyProjection:
    """Count each included operating unit once, without display rounding."""
    if re.fullmatch(r"[0-9]{4}-[0-9]{2}", period) is None:
        raise ValueError(f"Invalid period: {period}")
    try:
        first = date.fromisoformat(f"{period}-01")
    except ValueError as exc:
        raise ValueError(f"Invalid period: {period}") from exc
    month_end = first.replace(day=calendar.monthrange(first.year, first.month)[1])
    materialized = tuple(units)
    seen: set[str] = set()
    for unit in materialized:
        if unit.unit_id in seen:
            raise ValueError(f"Duplicate asset unit: {unit.unit_id}")
        seen.add(unit.unit_id)
    included = tuple(
        u
        for u in materialized
        if u.is_operating
        and u.included is True
        and u.managed_from <= month_end
        and (u.managed_to is None or u.managed_to >= month_end)
    )
    rented = tuple(u for u in included if u.rented)
    return OccupancyProjection(
        unit_count=len(included),
        rented_unit_count=len(rented),
        occupancy_rate=(Decimal(len(rented)) / Decimal(len(included)))
        if included
        else None,
        land_area=sum((u.land_area for u in included), Decimal(0)),
        building_area=sum((u.building_area for u in included), Decimal(0)),
        rentable_area=sum((u.rentable_area for u in included), Decimal(0)),
        rented_area=sum((u.rentable_area for u in rented), Decimal(0)),
    )
