"""Deposit directions come from current contract facts, never stored balances."""

from decimal import Decimal

import pytest

from src.services.asset_operations.deposit_rules import project_deposit_balance

pytestmark = pytest.mark.unit


def project(**changes):
    values = dict(
        contract_kind="terminal",
        contract_status="active",
        has_ended_event=False,
        renewed=False,
        agreed_amount=Decimal("100"),
        income_amount=Decimal("0"),
        expense_amount=Decimal("0"),
        carried_in_amount=Decimal("0"),
    )
    values.update(changes)
    return project_deposit_balance(**values)


@pytest.mark.parametrize(
    "kind,direction,status",
    [
        ("terminal", "receivable", "receivable_uncollected"),
        ("upstream", "payable", "payable_unpaid"),
    ],
)
def test_unpaid_deposit_direction_depends_on_contract_kind(kind, direction, status):
    balance = project(contract_kind=kind, income_amount=Decimal("40"))
    assert (balance.direction, balance.status, balance.outstanding_amount) == (
        direction,
        status,
        Decimal("60"),
    )
    assert balance.held_amount == Decimal("40")


@pytest.mark.parametrize(
    "kind,direction,status",
    [
        ("terminal", "refundable", "refundable_unreturned"),
        ("upstream", "recoverable", "recoverable_unreceived"),
    ],
)
def test_reduced_agreement_creates_return_or_recovery(kind, direction, status):
    balance = project(
        contract_kind=kind, agreed_amount=Decimal("30"), income_amount=Decimal("100")
    )
    assert (balance.direction, balance.status, balance.outstanding_amount) == (
        direction,
        status,
        Decimal("70"),
    )


@pytest.mark.parametrize("kind", ["terminal", "upstream"])
def test_registered_future_end_event_already_requires_settlement(kind):
    balance = project(
        contract_kind=kind,
        contract_status="active",
        has_ended_event=True,
        income_amount=Decimal("100"),
    )
    assert balance.outstanding_amount == Decimal("100")
    assert balance.direction == ("refundable" if kind == "terminal" else "recoverable")


def test_upstream_expired_pending_action_remains_in_term():
    assert project(
        contract_kind="upstream", contract_status="expired_pending_action"
    ).outstanding_amount == Decimal("100")
    terminal = project(contract_status="ended")
    assert (terminal.direction, terminal.status, terminal.outstanding_amount) == (
        "none",
        "settled",
        Decimal("0"),
    )


def test_renewal_transfers_all_held_money_without_refund_and_can_chain():
    first = project(income_amount=Decimal("100"), renewed=True)
    assert first.carried_out_amount == Decimal("100")
    assert (first.held_amount, first.status) == (Decimal("0"), "settled")
    second = project(
        carried_in_amount=first.carried_out_amount,
        expense_amount=Decimal("20"),
        renewed=True,
    )
    third = project(
        carried_in_amount=second.carried_out_amount, agreed_amount=Decimal("120")
    )
    assert second.carried_out_amount == Decimal("80")
    assert (third.held_amount, third.outstanding_amount) == (
        Decimal("80"),
        Decimal("40"),
    )


def test_expense_and_its_reversal_are_reflected_by_effective_totals():
    deducted = project(
        has_ended_event=True, income_amount=Decimal("100"), expense_amount=Decimal("40")
    )
    reversed_expense = project(has_ended_event=True, income_amount=Decimal("100"))
    assert deducted.outstanding_amount == Decimal("60")
    assert reversed_expense.outstanding_amount == Decimal("100")


def test_zero_agreement_and_no_facts_is_settled():
    assert project(agreed_amount=Decimal("0")).status == "settled"


@pytest.mark.parametrize(
    "field,value",
    [
        ("agreed_amount", Decimal("-1")),
        ("income_amount", Decimal("NaN")),
        ("expense_amount", Decimal("Infinity")),
        ("carried_in_amount", Decimal("-1")),
    ],
)
def test_invalid_money_is_rejected(field, value):
    with pytest.raises(ValueError):
        project(**{field: value})


def test_negative_held_balance_is_not_silently_clamped():
    with pytest.raises(ValueError):
        project(expense_amount=Decimal("1"))


@pytest.mark.parametrize(
    "changes", [{"contract_kind": "other"}, {"contract_status": "unknown"}]
)
def test_unknown_contract_facts_are_rejected(changes):
    with pytest.raises(ValueError):
        project(**changes)
