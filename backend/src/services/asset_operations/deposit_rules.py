"""Pure deposit balance projections over effective, reversal-adjusted totals."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class DepositBalance:
    agreed_amount: Decimal
    held_amount: Decimal
    carried_in_amount: Decimal
    carried_out_amount: Decimal
    direction: str
    outstanding_amount: Decimal
    status: str


def project_deposit_balance(
    *,
    contract_kind: str,
    contract_status: str,
    has_ended_event: bool,
    renewed: bool,
    agreed_amount: Decimal,
    income_amount: Decimal,
    expense_amount: Decimal,
    carried_in_amount: Decimal,
) -> DepositBalance:
    """An unrevoked renewal transfers holdings immediately, without a refund.

    Callers supply totals excluding reversed records and carry-in from the
    predecessor projection. An unrevoked end event settles the deposit even
    before its effective date, independently of the contract display status.
    Management agreements have no deposit entry and must not call this rule.
    """
    if contract_kind not in {"upstream", "terminal"}:
        raise ValueError("Unknown deposit contract kind")
    active = {"scheduled", "active", "expiring"}
    ended = {"historical"}
    if contract_kind == "upstream":
        active.add("expired_pending_action")
        ended.add("exited")
    else:
        ended.add("ended")
    if contract_status not in active | ended:
        raise ValueError("Unknown deposit contract status")
    for amount in (agreed_amount, income_amount, expense_amount, carried_in_amount):
        if not amount.is_finite() or amount < 0:
            raise ValueError("Deposit amounts must be finite and nonnegative")
    own_held = income_amount - expense_amount + carried_in_amount
    if own_held < 0:
        raise ValueError("Deposit expenses exceed effective holdings")
    carried_out = own_held if renewed else Decimal("0")
    held = own_held - carried_out
    in_term = contract_status in active and not has_ended_event
    target = agreed_amount if in_term and not renewed else Decimal("0")
    gap = target - held
    if gap > 0:
        direction, status = (
            ("payable", "payable_unpaid")
            if contract_kind == "upstream"
            else ("receivable", "receivable_uncollected")
        )
    elif gap < 0:
        direction, status = (
            ("recoverable", "recoverable_unreceived")
            if contract_kind == "upstream"
            else ("refundable", "refundable_unreturned")
        )
    else:
        direction, status = "none", "settled"
    return DepositBalance(
        agreed_amount=agreed_amount,
        held_amount=held,
        carried_in_amount=carried_in_amount,
        carried_out_amount=carried_out,
        direction=direction,
        outstanding_amount=abs(gap),
        status=status,
    )
