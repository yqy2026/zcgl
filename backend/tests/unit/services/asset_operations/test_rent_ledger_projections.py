"""Money and state are derived from append-only payment facts."""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from src.services.asset_operations.rent_ledger_projections import (
    effective_paid,
    ledger_status,
)

pytestmark = pytest.mark.unit


def test_second_payment_reversal_restores_partial_without_modifying_records():
    records = [
        SimpleNamespace(
            id="a", record_type="receipt", amount=Decimal("40"), reverses_record_id=None
        ),
        SimpleNamespace(
            id="b", record_type="receipt", amount=Decimal("60"), reverses_record_id=None
        ),
        SimpleNamespace(
            id="r", record_type="reversal", amount=Decimal("60"), reverses_record_id="b"
        ),
    ]
    assert effective_paid(records) == Decimal("40")
    assert records[1].amount == Decimal("60")
    assert (
        ledger_status(
            due_amount=Decimal("100"),
            paid_amount=effective_paid(records),
            due_date=date(2026, 10, 25),
            period_start=date(2026, 10, 1),
            voided=False,
            today=date(2026, 10, 20),
        )
        == "partial"
    )


@pytest.mark.parametrize(
    "paid,voided,today,expected",
    [
        ("100", False, date(2026, 11, 1), "paid"),
        ("40", False, date(2026, 11, 1), "overdue"),
        ("0", False, date(2026, 10, 20), "unpaid"),
        ("0", False, date(2026, 9, 30), "upcoming"),
        ("100", True, date(2026, 10, 20), "void"),
    ],
)
def test_state_precedence(paid, voided, today, expected):
    assert (
        ledger_status(
            due_amount=Decimal("100"),
            paid_amount=Decimal(paid),
            due_date=date(2026, 10, 25),
            period_start=date(2026, 10, 1),
            voided=voided,
            today=today,
        )
        == expected
    )
