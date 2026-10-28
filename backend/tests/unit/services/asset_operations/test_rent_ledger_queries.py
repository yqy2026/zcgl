"""Ledger views exclude void amounts, retain partial facts and fail closed."""

from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from src.core.exception_handler import PartyScopeForbiddenError
from src.crud.rent_ledger_queries import RentQueryFacts
from src.models.asset_contract import (
    ContractLifecycleEvent,
    ContractRentSchedule,
    TerminalContract,
)
from src.models.asset_ledger import RentLedgerEntry, RentPaymentRecord
from src.services.asset_operations.rent_ledger_query_service import (
    RentLedgerQueryService,
)
from src.services.party_scope_resolver import EffectivePartyScope

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


@pytest.mark.parametrize(
    "origin,reverse_termination", [("manual", False), ("clawback", True)]
)
async def test_locked_non_generated_entry_exposes_lifecycle_mismatch(
    origin, reverse_termination
):
    contract = TerminalContract(
        id="contract",
        contract_number="TM-001",
        start_date=date(2026, 10, 1),
        end_date=date(2026, 10, 31),
    )
    entry = RentLedgerEntry(
        id="entry",
        contract_kind="terminal",
        contract_id="contract",
        entry_type="terminal_receivable",
        period="2026-10",
        period_start=date(2026, 10, 15),
        period_end=date(2026, 10, 15),
        due_date=date(2026, 10, 15),
        due_amount=Decimal("100"),
        currency="CNY",
        origin=origin,
        basis_note="已签补充条款",
        locked_source={"lifecycle_event_id": "termination"},
        voided_at=None,
        version=1,
    )
    payment = RentPaymentRecord(
        id="payment",
        ledger_entry_id="entry",
        record_type="receipt",
        amount=Decimal("40"),
        occurred_on=date(2026, 10, 15),
        created_by="actor",
        created_at=datetime.now(UTC),
        reverses_record_id=None,
    )
    termination = ContractLifecycleEvent(
        id="termination",
        contract_kind="terminal",
        contract_id="contract",
        event_type="terminated",
        termination_type="early",
        effective_date=date(2026, 10, 15),
    )
    events = (termination,)
    if reverse_termination:
        events += (
            ContractLifecycleEvent(
                id="reversal",
                contract_kind="terminal",
                contract_id="contract",
                event_type="reversed",
                effective_date=date(2026, 10, 16),
                reversed_event_id="termination",
            ),
        )
    facts = RentQueryFacts((contract,), (entry,), (payment,), (), events)
    views, warnings = RentLedgerQueryService._views(facts, today=date(2026, 10, 20))
    assert views["entry"].remaining_amount == Decimal("60")
    assert views["entry"].warnings == ["RENT_LEDGER_PLAN_MISMATCH"]
    assert "RENT_LEDGER_PLAN_MISMATCH" in warnings["contract"]


async def test_matrix_totals_ignore_void_and_keep_partial():
    contract = TerminalContract(
        id="contract",
        contract_number="TM-001",
        start_date=date(2026, 10, 1),
        end_date=date(2026, 10, 31),
    )
    entry = RentLedgerEntry(
        id="entry",
        contract_kind="terminal",
        contract_id="contract",
        entry_type="terminal_receivable",
        period="2026-10",
        period_start=date(2026, 10, 1),
        period_end=date(2026, 10, 31),
        due_date=date(2026, 10, 25),
        due_amount=Decimal("100"),
        currency="CNY",
        origin="generated",
        basis_note=None,
        locked_source={},
        voided_at=None,
        version=1,
    )
    voided = RentLedgerEntry(
        id="void",
        contract_kind="terminal",
        contract_id="contract",
        entry_type="terminal_receivable",
        period="2026-10",
        period_start=date(2026, 10, 1),
        period_end=date(2026, 10, 31),
        due_date=date(2026, 10, 25),
        due_amount=Decimal("999"),
        currency="CNY",
        origin="manual",
        basis_note="历史手工义务",
        locked_source={},
        voided_at=datetime.now(UTC),
        version=1,
    )
    record = RentPaymentRecord(
        id="record",
        ledger_entry_id="entry",
        record_type="receipt",
        amount=Decimal("40"),
        occurred_on=date(2026, 10, 20),
        created_by="actor",
        created_at=datetime.now(UTC),
        reverses_record_id=None,
    )
    schedule = ContractRentSchedule(
        id="stage",
        contract_kind="terminal",
        contract_id="contract",
        stage_start=date(2026, 10, 1),
        stage_end=date(2026, 10, 31),
        actual_monthly_rent=Decimal("200"),
        payment_cycle="monthly",
        due_day=25,
    )
    repository = AsyncMock()
    repository.matrix_facts.return_value = RentQueryFacts(
        (contract,), (entry, voided), (record,), (schedule,), ()
    )
    view = await RentLedgerQueryService(repository=repository).matrix(
        None,
        scope=EffectivePartyScope(
            user_id="actor", source="explicit", scope_mode="unrestricted"
        ),
        ledger_type="terminal_rent",
        year=2026,
        today=date(2026, 10, 20),
    )
    assert view.total_due_amount == Decimal("100")
    assert view.total_paid_amount == Decimal("40")
    assert view.total_remaining_amount == Decimal("60")
    assert view.rows[0].months[9].entries[0].status == "partial"
    assert view.rows[0].warnings == ["RENT_LEDGER_PLAN_MISMATCH"]
    repository.matrix_facts.assert_awaited_once()


async def test_missing_scope_does_not_query_or_return_empty():
    repository = AsyncMock()
    with pytest.raises(PartyScopeForbiddenError):
        await RentLedgerQueryService(repository=repository).matrix(
            None,
            scope=EffectivePartyScope(
                user_id="actor",
                source="explicit",
                scope_mode="manager",
                owner_party_ids=["wrong-axis"],
            ),
            ledger_type="terminal_rent",
            year=2026,
        )
    repository.matrix_facts.assert_not_called()
