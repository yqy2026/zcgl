"""Deposit API writes cannot supply projected balances or reversal facts."""

import pytest
from pydantic import ValidationError

from src.core.exception_handler import BaseBusinessError
from src.schemas.deposit_commands import DepositRecordRequest


def payload(**overrides):
    return {
        "record_type": "collect",
        "amount": "12.34",
        "occurred_on": "2026-10-28",
        "expected_version": 1,
        **overrides,
    }


@pytest.mark.parametrize(
    "field",
    [
        "agreed_amount",
        "held_amount",
        "carried_in_amount",
        "carried_out_amount",
        "direction",
        "outstanding_amount",
        "status",
    ],
)
def test_deposit_write_rejects_projected_fields(field):
    with pytest.raises(BaseBusinessError) as caught:
        DepositRecordRequest.model_validate(payload(**{field: 1}))
    assert caught.value.code == "DERIVED_FIELD_NOT_WRITABLE"


@pytest.mark.parametrize(
    "change",
    [
        {"record_type": "reversal"},
        {"amount": "0"},
        {"amount": "-1"},
        {"amount": "0.001"},
        {"expected_version": 0},
        {"lifecycle_event_id": "event"},
    ],
)
def test_deposit_write_rejects_invalid_or_server_owned_facts(change):
    with pytest.raises(ValidationError):
        DepositRecordRequest.model_validate(payload(**change))


def test_deposit_write_preserves_exact_decimal():
    assert str(DepositRecordRequest.model_validate(payload()).amount) == "12.34"
