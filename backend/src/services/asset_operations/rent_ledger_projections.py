"""Pure projections of money and state from immutable rent records."""

from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from typing import Protocol


class PaymentFact(Protocol):
    @property
    def id(self) -> str: ...
    @property
    def record_type(self) -> str: ...
    @property
    def amount(self) -> Decimal: ...
    @property
    def reverses_record_id(self) -> str | None: ...


def effective_paid(records: Sequence[PaymentFact]) -> Decimal:
    reversed_ids = {
        row.reverses_record_id for row in records if row.record_type == "reversal"
    }
    return sum(
        (
            row.amount
            for row in records
            if row.record_type != "reversal" and row.id not in reversed_ids
        ),
        Decimal("0"),
    )


def ledger_status(
    *,
    due_amount: Decimal,
    paid_amount: Decimal,
    due_date: date,
    period_start: date,
    voided: bool,
    today: date,
) -> str:
    if voided:
        return "void"
    if due_amount - paid_amount <= 0:
        return "paid"
    if today > due_date:
        return "overdue"
    if paid_amount > 0:
        return "partial"
    if period_start.replace(day=1) <= today.replace(day=1):
        return "unpaid"
    return "upcoming"
