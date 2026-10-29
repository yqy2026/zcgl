"""Renewal carry-forward is immediate and never exposes hidden ancestors."""

from datetime import date
from decimal import Decimal

import pytest

from src.crud.deposit_queries import DepositQueryFacts
from src.models.asset_contract import ContractLifecycleEvent, TerminalContract
from src.models.deposit_ledger import DepositLedgerEntry
from src.services.asset_operations.deposit_query_service import (
    effective_deposit_ancestors,
    project_deposit_facts,
)

pytestmark = pytest.mark.unit


def contract(identifier, parent=None):
    return TerminalContract(
        id=identifier,
        renewed_from_id=parent,
        deposit_amount=Decimal("100"),
        start_date=date(2026, 1, 1),
        end_date=date(2027, 1, 1),
    )


def entry(identifier):
    return DepositLedgerEntry(
        id=f"deposit-{identifier}",
        contract_kind="terminal",
        contract_id=identifier,
        collector="operator",
        version=1,
    )


def event(identifier, kind, owner, **extra):
    return ContractLifecycleEvent(
        id=identifier,
        contract_kind="terminal",
        contract_id=owner,
        event_type=kind,
        effective_date=date(2027, 1, 1),
        **extra,
    )


def test_future_renewal_carries_balance_immediately_without_exposing_ancestor():
    facts = DepositQueryFacts(
        contracts=(contract("old"), contract("new", "old")),
        entries=(entry("old"), entry("new")),
        records=(),
        events=(event("renew", "renewed", "old", successor_contract_id="new"),),
        visible_contract_ids=frozenset({"new"}),
        totals={"deposit-old": (Decimal("80"), Decimal("0"))},
    )
    views = project_deposit_facts(facts, today=date(2026, 10, 28))
    assert len(views) == 1
    assert views[0].contract_id == "new"
    assert views[0].held_amount == views[0].carried_in_amount == Decimal("80")
    assert views[0].outstanding_amount == Decimal("20")
    facts.visible_contract_ids = frozenset({"old"})
    old = project_deposit_facts(facts, today=date(2026, 10, 28))[0]
    assert old.read_only and old.status == "settled"
    assert old.held_amount == 0 and old.carried_out_amount == Decimal("80")


def test_reversed_renewal_does_not_carry_into_linked_successor():
    facts = DepositQueryFacts(
        contracts=(contract("old"), contract("new", "old")),
        entries=(entry("old"), entry("new")),
        records=(),
        events=(
            event("renew", "renewed", "old", successor_contract_id="new"),
            event("undo", "reversed", "old", reversed_event_id="renew"),
        ),
        visible_contract_ids=frozenset({"new"}),
        totals={"deposit-old": (Decimal("80"), Decimal("0"))},
    )
    view = project_deposit_facts(facts, today=date(2026, 10, 28))[0]
    assert view.carried_in_amount == 0 and view.outstanding_amount == Decimal("100")


def test_future_termination_changes_deposit_direction_immediately():
    facts = DepositQueryFacts(
        contracts=(contract("current"),),
        entries=(entry("current"),),
        records=(),
        events=(event("end", "terminated", "current"),),
        visible_contract_ids=frozenset({"current"}),
        totals={"deposit-current": (Decimal("80"), Decimal("0"))},
    )
    view = project_deposit_facts(facts, today=date(2026, 10, 28))[0]
    assert view.ended and view.status == "refundable_unreturned"
    assert view.outstanding_amount == Decimal("80")


def test_offset_chain_stops_at_revoked_renewal():
    facts = DepositQueryFacts(
        contracts=(contract("old"), contract("new", "old")),
        entries=(),
        records=(),
        events=(event("renew", "renewed", "old", successor_contract_id="new"),),
        visible_contract_ids=frozenset({"new"}),
        totals={},
    )
    assert effective_deposit_ancestors(facts, "new") == frozenset({"new", "old"})
    facts.events += (event("undo", "reversed", "old", reversed_event_id="renew"),)
    assert effective_deposit_ancestors(facts, "new") == frozenset({"new"})
