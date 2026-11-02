"""Assessment-scope defaults derive from explicit facts, never from guesses."""

from datetime import date

import pytest

from src.services.asset_operations.assessment_scope_rules import (
    PriorScopeDecision,
    ScopeUnitFact,
    affected_periods,
    derive_scope_defaults,
)

pytestmark = pytest.mark.unit


def fact(
    unit_id: str = "u",
    *,
    managed_from: date = date(2020, 1, 1),
    managed_to: date | None = None,
    is_operating: bool = True,
    predecessor_unit_ids: tuple[str, ...] = (),
) -> ScopeUnitFact:
    return ScopeUnitFact(
        unit_id=unit_id,
        managed_from=managed_from,
        managed_to=managed_to,
        is_operating=is_operating,
        predecessor_unit_ids=predecessor_unit_ids,
    )


def decisions_by_id(result: object, unit_id: str) -> object:
    return next(d for d in result.decisions if d.unit_id == unit_id)  # type: ignore[attr-defined]


def pending_by_id(result: object, unit_id: str) -> object:
    return next(p for p in result.pending if p.unit_id == unit_id)  # type: ignore[attr-defined]


def test_stock_operating_unit_managed_before_year_start_is_included_by_default() -> None:
    result = derive_scope_defaults(2026, (fact("stock"),), ())
    assert [d.unit_id for d in result.decisions] == ["stock"]
    assert decisions_by_id(result, "stock").included is True
    assert decisions_by_id(result, "stock").origin == "default"
    assert result.pending == ()


def test_unit_managed_from_january_first_is_stock_not_new_takeover() -> None:
    result = derive_scope_defaults(
        2026, (fact("boundary", managed_from=date(2026, 1, 1)),), ()
    )
    assert decisions_by_id(result, "boundary").included is True
    assert result.pending == ()


def test_mid_year_takeover_requires_manual_confirmation() -> None:
    result = derive_scope_defaults(
        2026, (fact("new", managed_from=date(2026, 6, 15)),), ()
    )
    assert result.decisions == ()
    assert pending_by_id(result, "new").reason == "new_takeover"


def test_prior_inclusion_is_carried_over_for_still_valid_units() -> None:
    result = derive_scope_defaults(
        2026,
        (fact("kept"),),
        (PriorScopeDecision(unit_id="kept", included=True),),
    )
    assert decisions_by_id(result, "kept").included is True
    assert decisions_by_id(result, "kept").origin == "prior"


def test_prior_exclusion_is_carried_over_with_its_reason() -> None:
    result = derive_scope_defaults(
        2026,
        (fact("out"),),
        (
            PriorScopeDecision(
                unit_id="out", included=False, exclusion_reason=" 非经营改造 "
            ),
        ),
    )
    decision = decisions_by_id(result, "out")
    assert decision.included is False
    assert decision.exclusion_reason == "非经营改造"
    assert decision.origin == "prior"


def test_prior_decision_for_unit_outside_the_year_is_dropped() -> None:
    result = derive_scope_defaults(
        2026,
        (fact("gone", managed_to=date(2025, 12, 31)),),
        (PriorScopeDecision(unit_id="gone", included=True),),
    )
    assert result.decisions == ()
    assert result.pending == ()


def test_split_result_inherits_inclusion_when_all_sources_were_included() -> None:
    result = derive_scope_defaults(
        2026,
        (
            fact(
                "part-a",
                managed_from=date(2026, 5, 1),
                predecessor_unit_ids=("src",),
            ),
        ),
        (PriorScopeDecision(unit_id="src", included=True),),
    )
    decision = decisions_by_id(result, "part-a")
    assert decision.included is True
    assert decision.origin == "inherited"


def test_split_result_with_mixed_source_decisions_stays_pending() -> None:
    result = derive_scope_defaults(
        2026,
        (
            fact(
                "part-b",
                managed_from=date(2026, 5, 1),
                predecessor_unit_ids=("inc", "exc"),
            ),
        ),
        (
            PriorScopeDecision(unit_id="inc", included=True),
            PriorScopeDecision(unit_id="exc", included=False, exclusion_reason="闲置"),
        ),
    )
    assert result.decisions == ()
    assert pending_by_id(result, "part-b").reason == "boundary_uncertain"


def test_merge_result_from_fully_excluded_sources_stays_pending() -> None:
    """Only unanimous inclusion inherits; every other combination is manual."""

    result = derive_scope_defaults(
        2026,
        (
            fact(
                "merged",
                managed_from=date(2026, 5, 1),
                predecessor_unit_ids=("x1", "x2"),
            ),
        ),
        (
            PriorScopeDecision(unit_id="x1", included=False, exclusion_reason="a"),
            PriorScopeDecision(unit_id="x2", included=False, exclusion_reason="b"),
        ),
    )
    assert result.decisions == ()
    assert pending_by_id(result, "merged").reason == "boundary_uncertain"


def test_boundary_result_with_unknown_source_stays_pending() -> None:
    result = derive_scope_defaults(
        2026,
        (
            fact(
                "part-c",
                managed_from=date(2026, 5, 1),
                predecessor_unit_ids=("unknown",),
            ),
        ),
        (PriorScopeDecision(unit_id="other", included=True),),
    )
    assert result.decisions == ()
    assert pending_by_id(result, "part-c").reason == "boundary_uncertain"


@pytest.mark.parametrize(
    "units",
    [
        (fact("nonop", is_operating=False),),
        (fact("future", managed_from=date(2027, 1, 1)),),
        (fact("ended", managed_to=date(2025, 12, 31)),),
        (fact("nonop_split", is_operating=False, predecessor_unit_ids=("s",)),),
    ],
)
def test_non_candidates_are_never_decided_nor_pending(units: tuple) -> None:
    result = derive_scope_defaults(2026, units, ())
    assert result.decisions == ()
    assert result.pending == ()


def test_unit_managed_through_december_thirty_first_is_still_a_candidate() -> None:
    result = derive_scope_defaults(
        2026, (fact("last-day", managed_to=date(2026, 12, 31)),), ()
    )
    assert decisions_by_id(result, "last-day").included is True


def test_duplicate_unit_facts_are_rejected() -> None:
    with pytest.raises(ValueError, match="Duplicate asset unit"):
        derive_scope_defaults(2026, (fact("dup"), fact("dup")), ())


def test_prior_exclusion_without_reason_is_rejected() -> None:
    with pytest.raises(ValueError, match="exclusion_reason"):
        derive_scope_defaults(
            2026,
            (fact("broken"),),
            (PriorScopeDecision(unit_id="broken", included=False),),
        )


def test_output_is_ordered_by_unit_id_for_stable_diffing() -> None:
    result = derive_scope_defaults(
        2026,
        (fact("b"), fact("a"), fact("c", managed_from=date(2026, 2, 1))),
        (),
    )
    assert [d.unit_id for d in result.decisions] == ["a", "b"]
    assert [p.unit_id for p in result.pending] == ["c"]


@pytest.mark.parametrize(
    "effective_from,expected_head,expected_tail",
    [
        ("2026-01", "2026-01", "2026-12"),
        ("2026-07", "2026-07", "2026-12"),
        ("2026-12", "2026-12", "2026-12"),
    ],
)
def test_affected_periods_run_to_year_end(
    effective_from: str, expected_head: str, expected_tail: str
) -> None:
    periods = affected_periods(effective_from, 2026)
    assert periods[0] == expected_head
    assert periods[-1] == expected_tail
    assert len(periods) == 13 - int(effective_from[5:])


@pytest.mark.parametrize(
    "effective_from,year",
    [
        ("2026-1", 2026),
        ("2026-13", 2026),
        ("2025-12", 2026),
        ("2027-01", 2026),
        ("2026-10-01", 2026),
    ],
)
def test_invalid_effective_from_period_is_rejected(effective_from: str, year: int) -> None:
    with pytest.raises(ValueError, match="Invalid effective_from_period"):
        affected_periods(effective_from, year)
