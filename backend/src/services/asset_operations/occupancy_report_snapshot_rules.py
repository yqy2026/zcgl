"""Read-only diff between a submitted occupancy snapshot and current facts."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from decimal import Decimal
from typing import TypeVar

# Stored line columns are Numeric(14,2); identity comparisons quantize to
# that scale so formatting differences never surface as phantom changes.
_AREA_SCALE = Decimal("1E-2")
_AREA_FIELDS = frozenset({"land_area", "building_area", "rentable_area", "rented_area"})


@dataclass(frozen=True)
class SnapshotLine:
    asset_unit_id: str
    owner_name_snapshot: str
    usage_type_snapshot: str
    project_name_snapshot: str
    address_snapshot: str
    land_area: Decimal
    building_area: Decimal
    rentable_area: Decimal
    rented_area: Decimal
    rented_unit_count: int
    rental_status: str
    terminal_contract_ids: list[str]


@dataclass(frozen=True)
class CurrentLine:
    asset_unit_id: str
    owner_name: str
    usage_type: str
    project_name: str
    address: str
    land_area: Decimal
    building_area: Decimal
    rentable_area: Decimal
    rented_area: Decimal
    rented_unit_count: int
    rental_status: str
    terminal_contract_ids: list[str]


@dataclass(frozen=True)
class FieldDiff:
    field_name: str
    snapshot_value: str | None
    current_value: str | None


@dataclass(frozen=True)
class UnitDiff:
    asset_unit_id: str
    kind: str  # "changed" | "unit_left_scope" | "unit_entered_scope"
    changes: tuple[FieldDiff, ...]


def diff_snapshot_against_current(
    snapshot_lines: Iterable[SnapshotLine],
    current_lines: Iterable[CurrentLine],
) -> tuple[UnitDiff, ...]:
    """Per-unit field differences; snapshot values always stay untouched."""
    snapshots = _materialize_unique(snapshot_lines, key=lambda line: line.asset_unit_id)
    currents = _materialize_unique(current_lines, key=lambda line: line.asset_unit_id)
    diffs: list[UnitDiff] = []
    for unit_id, snap in snapshots.items():
        now = currents.get(unit_id)
        if now is None:
            diffs.append(
                UnitDiff(
                    asset_unit_id=unit_id,
                    kind="unit_left_scope",
                    changes=(),
                )
            )
            continue
        changes = _compare(snap, now)
        if len(changes) > 0:
            diffs.append(
                UnitDiff(asset_unit_id=unit_id, kind="changed", changes=changes)
            )
    for unit_id in sorted(set(currents) - set(snapshots)):
        diffs.append(
            UnitDiff(
                asset_unit_id=unit_id,
                kind="unit_entered_scope",
                changes=(),
            )
        )
    return tuple(diffs)


def _compare(snap: SnapshotLine, now: CurrentLine) -> tuple[FieldDiff, ...]:
    pairs: tuple[tuple[str, object, object], ...] = (
        ("owner_name", snap.owner_name_snapshot, now.owner_name),
        ("usage_type", snap.usage_type_snapshot, now.usage_type),
        ("project_name", snap.project_name_snapshot, now.project_name),
        ("address", snap.address_snapshot, now.address),
        ("land_area", snap.land_area, now.land_area),
        ("building_area", snap.building_area, now.building_area),
        ("rentable_area", snap.rentable_area, now.rentable_area),
        ("rented_area", snap.rented_area, now.rented_area),
        ("rented_unit_count", snap.rented_unit_count, now.rented_unit_count),
        ("rental_status", snap.rental_status, now.rental_status),
        (
            "terminal_contract_ids",
            tuple(snap.terminal_contract_ids),
            tuple(now.terminal_contract_ids),
        ),
    )
    changes: list[FieldDiff] = []
    for name, before, after in pairs:
        if name in _AREA_FIELDS:
            before = _quantize(before)
            after = _quantize(after)
        if before != after:
            changes.append(
                FieldDiff(
                    field_name=name,
                    snapshot_value=_render(before),
                    current_value=_render(after),
                )
            )
    return tuple(changes)


_LineT = TypeVar("_LineT")


def _materialize_unique(
    lines: Iterable[_LineT], *, key: Callable[[_LineT], str]
) -> dict[str, _LineT]:
    seen: dict[str, _LineT] = {}
    for line in lines:
        unit_id = key(line)
        if unit_id in seen:
            raise ValueError(f"Duplicate asset unit: {unit_id}")
        seen[unit_id] = line
    return seen


def _quantize(value: object) -> object:
    if not isinstance(value, Decimal):
        return value
    return value.quantize(_AREA_SCALE)


def _render(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, tuple):
        return "[" + ",".join(str(item) for item in value) + "]"
    return str(value)


__all__ = [
    "CurrentLine",
    "FieldDiff",
    "SnapshotLine",
    "UnitDiff",
    "diff_snapshot_against_current",
]
