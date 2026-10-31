"""Assessment-scope default decisions from explicit facts and prior versions.

Callers resolve the operator, permissions, candidate units and prior items.
Only unanimous source inclusion inherits automatically; every other new or
boundary-derived unit waits for one explicit human decision.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class ScopePendingReason(StrEnum):
    """Why a candidate unit has no decision yet."""

    NEW_TAKEOVER = "new_takeover"
    BOUNDARY_UNCERTAIN = "boundary_uncertain"


@dataclass(frozen=True)
class ScopeUnitFact:
    unit_id: str
    managed_from: date
    managed_to: date | None
    is_operating: bool
    predecessor_unit_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class PriorScopeDecision:
    unit_id: str
    included: bool
    exclusion_reason: str | None = None


@dataclass(frozen=True)
class ScopeDecision:
    unit_id: str
    included: bool
    exclusion_reason: str | None
    origin: str  # "prior" | "default" | "inherited"


@dataclass(frozen=True)
class ScopePendingUnit:
    unit_id: str
    reason: ScopePendingReason


@dataclass(frozen=True)
class ScopeDerivation:
    decisions: tuple[ScopeDecision, ...]
    pending: tuple[ScopePendingUnit, ...]


def derive_scope_defaults(
    year: int,
    facts: Sequence[ScopeUnitFact],
    prior_decisions: Sequence[PriorScopeDecision],
) -> ScopeDerivation:
    """Split candidates into carried/default decisions and pending confirmations.

    Candidates are operating units under management at any point of the year.
    Prior decisions survive only for units that are still candidates; units
    managed before January 1st default to inclusion, later takeovers and
    boundary results with non-unanimous sources stay pending.
    """
    facts = tuple(facts)
    prior_decisions = tuple(prior_decisions)
    year_start = date(year, 1, 1)
    year_end = date(year, 12, 31)
    seen: set[str] = set()
    for unit in facts:
        if unit.unit_id in seen:
            raise ValueError(f"Duplicate asset unit: {unit.unit_id}")
        seen.add(unit.unit_id)
    prior: dict[str, PriorScopeDecision] = {}
    for decision in prior_decisions:
        if decision.unit_id in prior:
            raise ValueError(f"Duplicate prior decision: {decision.unit_id}")
        if not decision.included and not _has_reason(decision.exclusion_reason):
            raise ValueError(
                f"Prior exclusion lacks exclusion_reason: {decision.unit_id}"
            )
        prior[decision.unit_id] = decision

    decisions: list[ScopeDecision] = []
    pending: list[ScopePendingUnit] = []
    for unit in facts:
        if not unit.is_operating:
            continue
        if unit.managed_from > year_end:
            continue
        if unit.managed_to is not None and unit.managed_to < year_start:
            continue
        carried = prior.get(unit.unit_id)
        if carried is not None:
            decisions.append(
                ScopeDecision(
                    unit_id=unit.unit_id,
                    included=carried.included,
                    exclusion_reason=(
                        carried.exclusion_reason.strip()
                        if carried.exclusion_reason is not None
                        else None
                    ),
                    origin="prior",
                )
            )
            continue
        sources = unit.predecessor_unit_ids
        if len(sources) > 0:
            source_decisions = [prior.get(source) for source in sources]
            if all(
                source is not None and source.included for source in source_decisions
            ):
                decisions.append(
                    ScopeDecision(
                        unit_id=unit.unit_id,
                        included=True,
                        exclusion_reason=None,
                        origin="inherited",
                    )
                )
            else:
                pending.append(
                    ScopePendingUnit(
                        unit_id=unit.unit_id,
                        reason=ScopePendingReason.BOUNDARY_UNCERTAIN,
                    )
                )
            continue
        if unit.managed_from <= year_start:
            decisions.append(
                ScopeDecision(
                    unit_id=unit.unit_id,
                    included=True,
                    exclusion_reason=None,
                    origin="default",
                )
            )
        else:
            pending.append(
                ScopePendingUnit(
                    unit_id=unit.unit_id,
                    reason=ScopePendingReason.NEW_TAKEOVER,
                )
            )
    return ScopeDerivation(
        decisions=tuple(sorted(decisions, key=lambda d: d.unit_id)),
        pending=tuple(sorted(pending, key=lambda p: p.unit_id)),
    )


def affected_periods(effective_from_period: str, year: int) -> tuple[str, ...]:
    """List the report months a newly saved version can still change."""
    if re.fullmatch(r"[0-9]{4}-[0-9]{2}", effective_from_period) is None:
        raise ValueError(f"Invalid effective_from_period: {effective_from_period}")
    head_year, head_month = (
        int(effective_from_period[:4]),
        int(effective_from_period[5:7]),
    )
    if head_year != year or not 1 <= head_month <= 12:
        raise ValueError(f"Invalid effective_from_period: {effective_from_period}")
    return tuple(f"{year}-{month:02d}" for month in range(head_month, 13))


def _has_reason(reason: str | None) -> bool:
    return reason is not None and reason.strip() != ""
