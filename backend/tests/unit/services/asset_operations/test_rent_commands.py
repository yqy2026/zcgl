"""Rent writes preserve source records and historical schedule facts."""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from src.core.exception_handler import BaseBusinessError
from src.schemas.asset_operations import ContractRentScheduleInput
from src.schemas.rent_commands import RentPaymentRequest
from src.services.asset_operations.rent_payment_command_service import (
    RentPaymentCommandService,
    validate_payment,
)
from src.services.asset_operations.rent_schedule_correction_service import (
    validate_history,
)
from src.services.party_scope_resolver import EffectivePartyScope


def stage(start: str, end: str, rent: str = "100") -> ContractRentScheduleInput:
    return ContractRentScheduleInput(
        stage_start=start,
        stage_end=end,
        base_monthly_rent=rent,
        actual_monthly_rent=rent,
        payment_cycle="monthly",
        due_day=25,
    )


def test_payment_cannot_overpay_or_use_inapplicable_record_type():
    with pytest.raises(BaseBusinessError) as error:
        validate_payment(
            entry_type="terminal_receivable",
            record_type="receipt",
            amount=Decimal("51"),
            remaining=Decimal("50"),
            voided=False,
        )
    assert error.value.code == "PAYMENT_AMOUNT_EXCEEDS_REMAINING"
    with pytest.raises(BaseBusinessError) as error:
        validate_payment(
            entry_type="owner_receipt_expected",
            record_type="receipt",
            amount=Decimal("10"),
            remaining=Decimal("50"),
            voided=False,
        )
    assert error.value.code == "RENT_RECORD_TYPE_MISMATCH"


def test_history_cannot_change_existing_past_days_but_allows_gaps():
    old = [stage("2026-01-01", "2026-01-31")]
    with pytest.raises(BaseBusinessError) as error:
        validate_history(
            old, [stage("2026-01-01", "2026-01-31", "101")], date(2026, 3, 1)
        )
    assert error.value.code == "RENT_SCHEDULE_HISTORY_IMMUTABLE"
    gaps = validate_history(
        old,
        [stage("2026-01-01", "2026-01-31"), stage("2026-02-01", "2026-02-28")],
        date(2026, 3, 1),
    )
    assert gaps == ((date(2026, 2, 1), date(2026, 2, 28)),)


def test_history_allows_splitting_an_unchanged_stage_at_current_month():
    old = [stage("2026-01-01", "2026-12-31")]
    proposed = [
        stage("2026-01-01", "2026-02-28"),
        stage("2026-03-01", "2026-12-31", "110"),
    ]
    assert validate_history(old, proposed, date(2026, 3, 1)) == ()


@pytest.mark.parametrize(
    "field", ["status", "effective_paid_amount", "remaining_amount"]
)
def test_write_schema_rejects_derived_fields_with_business_code(field):
    with pytest.raises(BaseBusinessError) as error:
        RentPaymentRequest.model_validate(
            {
                "record_type": "receipt",
                "amount": "10",
                "occurred_on": "2026-01-01",
                "expected_version": 1,
                field: "paid",
            }
        )
    assert error.value.code == "DERIVED_FIELD_NOT_WRITABLE"


def test_void_and_deposit_offset_cannot_be_registered_directly():
    with pytest.raises(BaseBusinessError) as error:
        validate_payment(
            entry_type="terminal_receivable",
            record_type="receipt",
            amount=Decimal("1"),
            remaining=Decimal("20"),
            voided=True,
        )
    assert error.value.code == "RENT_LEDGER_ENTRY_VOIDED"
    with pytest.raises(BaseBusinessError) as error:
        validate_payment(
            entry_type="terminal_receivable",
            record_type="deposit_offset",
            amount=Decimal("1"),
            remaining=Decimal("20"),
            voided=False,
        )
    assert error.value.code == "RENT_RECORD_TYPE_MISMATCH"


@pytest.mark.parametrize("replacement", [[], [stage("2026-01-01", "2026-01-30")]])
def test_history_does_not_allow_removing_existing_past_coverage(replacement):
    with pytest.raises(BaseBusinessError) as error:
        validate_history(
            [stage("2026-01-01", "2026-01-31")], replacement, date(2026, 3, 1)
        )
    assert error.value.code == "RENT_SCHEDULE_HISTORY_IMMUTABLE"


@pytest.mark.asyncio
async def test_entry_lock_follows_unit_and_contract_locks(monkeypatch):
    from src.services.asset_operations import rent_payment_command_service as module

    calls = []
    row = SimpleNamespace(id="entry", contract_kind="terminal", contract_id="contract")

    async def get_entry(db, *, entry_id, for_update=False):
        calls.append("entry_lock" if for_update else "entry_lookup")
        return row

    async def contract(db, **kwargs):
        assert kwargs["lock"]
        calls.append("units_and_contract_lock")

    monkeypatch.setattr(module.asset_ledger_repository, "get_entry", get_entry)
    monkeypatch.setattr(module, "scoped_contract", contract)
    await RentPaymentCommandService()._entry(
        None,
        entry_id="entry",
        scope=EffectivePartyScope(
            user_id="actor", source="explicit", scope_mode="unrestricted"
        ),
        lock=True,
    )
    assert calls == ["entry_lookup", "units_and_contract_lock", "entry_lock"]
