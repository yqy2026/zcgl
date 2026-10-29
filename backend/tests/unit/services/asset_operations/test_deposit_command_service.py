from decimal import Decimal

import pytest

from src.core.exception_handler import BaseBusinessError
from src.services.asset_operations.deposit_command_service import (
    validate_deposit_record,
)

pytestmark = pytest.mark.unit


def validate(**overrides):
    args = dict(
        kind="terminal",
        collector="operator",
        record_type="collect",
        amount=Decimal("10"),
        held=Decimal("20"),
        outstanding=Decimal("10"),
        direction="receivable",
        ended=False,
        read_only=False,
        reason="",
        offset_id=None,
    )
    validate_deposit_record(**(args | overrides))


def test_income_cannot_exceed_gap():
    validate()
    with pytest.raises(BaseBusinessError, match="剩余") as failure:
        validate(amount=Decimal("11"))
    assert failure.value.code == "DEPOSIT_AMOUNT_EXCEEDS_REMAINING"


def test_owner_cannot_record_operator_collection_or_deduct():
    for record_type in ("collect", "deduct"):
        with pytest.raises(BaseBusinessError, match="类型") as failure:
            validate(collector="owner", record_type=record_type)
        assert failure.value.code == "DEPOSIT_RECORD_TYPE_MISMATCH"


def test_deduction_requires_ended_stage_and_target():
    with pytest.raises(BaseBusinessError) as failure:
        validate(record_type="deduct", offset_id="rent")
    assert failure.value.code == "DEPOSIT_OFFSET_NOT_ALLOWED"
    validate(record_type="deduct", ended=True, offset_id="rent")
    with pytest.raises(BaseBusinessError) as failure:
        validate(record_type="deduct", ended=True)
    assert failure.value.code == "DEPOSIT_OFFSET_TARGET_INVALID"


def test_forfeit_requires_reason_and_cannot_exceed_held():
    with pytest.raises(BaseBusinessError) as failure:
        validate(record_type="forfeit", ended=True)
    assert failure.value.code == "FORFEIT_REASON_REQUIRED"
    with pytest.raises(BaseBusinessError) as failure:
        validate(record_type="forfeit", ended=True, reason="损失", amount=Decimal("21"))
    assert failure.value.code == "DEPOSIT_AMOUNT_EXCEEDS_REMAINING"
    validate(record_type="forfeit", ended=True, reason="损失")


def test_renewed_entry_is_read_only():
    with pytest.raises(BaseBusinessError, match="续签") as failure:
        validate(read_only=True)
    assert failure.value.code == "DEPOSIT_ENTRY_CARRIED_FORWARD"
