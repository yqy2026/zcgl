"""Fee guards participate in rent transactions and never run on replay."""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace as Row
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.asset_contract import TerminalContract
from src.schemas.rent_commands import (
    ManualRentEntryRequest,
    RentPaymentRequest,
    RentReversalRequest,
    VoidRentEntryRequest,
)
from src.services.asset_operations import rent_payment_command_service as module

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


async def test_new_receipt_for_nonmember_line_rolls_back_after_locked_check(
    setup, monkeypatch
):
    service, db, entry, _, guard, _ = setup
    monkeypatch.setattr(
        module.management_fee_query_service,
        "detail",
        AsyncMock(
            return_value=Row(statement=Row(status=None), projection=Row(lines=()))
        ),
    )
    with pytest.raises(module.ResourceNotFoundError):
        await service.register(
            db,
            entry_id=entry.id,
            request=RentPaymentRequest(
                record_type="owner_reported_receipt",
                amount="10",
                occurred_on="2026-10-01",
                expected_version=1,
            ),
            actor_id="actor",
            scope=Row(),
            idempotency_key="new-key",
            management_fee_statement_id="st",
        )
    guard.before_change.assert_awaited_once()
    module.asset_ledger_repository.add_record.assert_not_awaited()
    db.rollback.assert_awaited_once()


@pytest.mark.parametrize("status", ["confirmed", "superseded"])
async def test_statement_context_is_rechecked_after_owner_guard(
    setup, monkeypatch, status
):
    service, db, entry, _, guard, _ = setup

    async def detail(*args, **kwargs):
        guard.before_change.assert_awaited_once()
        return Row(statement=Row(status=status), projection=None)

    monkeypatch.setattr(module.management_fee_query_service, "detail", detail)
    with pytest.raises(Exception) as caught:
        await service.register(
            db,
            entry_id=entry.id,
            request=RentPaymentRequest(
                record_type="owner_reported_receipt",
                amount="10",
                occurred_on="2026-10-01",
                expected_version=1,
            ),
            actor_id="actor",
            scope=Row(),
            idempotency_key="key",
            management_fee_statement_id="st",
        )
    assert caught.value.code == "MANAGEMENT_FEE_STATEMENT_LOCKED"
    module.asset_ledger_repository.add_record.assert_not_awaited()
    db.rollback.assert_awaited_once()


@pytest.fixture
def setup(monkeypatch):
    entry = Row(
        id="entry",
        contract_kind="terminal",
        contract_id="tm",
        entry_type="owner_receipt_expected",
        version=1,
        due_amount=Decimal("100"),
        voided_at=None,
        origin="manual",
    )
    original = Row(
        id="original",
        ledger_entry_id="entry",
        record_type="owner_reported_receipt",
        amount=Decimal("10"),
        created_by="actor",
        occurred_on=date(2026, 10, 1),
        document_id=None,
        reverses_record_id=None,
        reason=None,
    )
    db = MagicMock(flush=AsyncMock(), commit=AsyncMock(), rollback=AsyncMock())
    service = module.RentPaymentCommandService()
    monkeypatch.setattr(service, "_entry", AsyncMock(return_value=entry))
    monkeypatch.setattr(module, "require_scope", lambda *args: None)
    monkeypatch.setattr(module, "audit", AsyncMock())
    monkeypatch.setattr(module, "receipt", AsyncMock())
    monkeypatch.setattr(module, "contract_snapshot", lambda obj: {})
    guard = Row(before_change=AsyncMock())
    monkeypatch.setattr(module, "management_fee_write_guard", guard, raising=False)
    identity = Row(ensure_bound_contract=AsyncMock())
    monkeypatch.setattr(module, "management_fee_entry_service", identity, raising=False)
    for name, value in (
        ("get_record", original),
        ("get_record_by_idempotency", None),
        ("list_records", ()),
        ("add_record", None),
        ("add_entry", None),
    ):
        monkeypatch.setattr(
            module.asset_ledger_repository, name, AsyncMock(return_value=value)
        )
    monkeypatch.setattr(
        module.asset_contract_repository,
        "get_write_receipt",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        module.rent_command_repository, "find_reversal", AsyncMock(return_value=None)
    )
    monkeypatch.setattr(module.rent_obligation_service, "replan", AsyncMock())
    return service, db, entry, original, guard, identity


async def command(setup, action):
    service, db, entry, original, guard, identity = setup
    common = dict(actor_id="actor", scope=Row(), idempotency_key="key")
    if action == "register":
        return await service.register(
            db,
            entry_id=entry.id,
            request=RentPaymentRequest(
                record_type="owner_reported_receipt",
                amount="10",
                occurred_on="2026-10-01",
                expected_version=1,
            ),
            **common,
        )
    if action == "reverse":
        return await service.reverse(
            db,
            record_id=original.id,
            request=RentReversalRequest(reason="误录", expected_version=1),
            **common,
        )
    return await service.void_manual(
        db,
        entry_id=entry.id,
        request=VoidRentEntryRequest(reason="误录", expected_version=1),
        **common,
    )


@pytest.mark.parametrize("action", ["register", "reverse", "void"])
async def test_owner_rent_changes_guard_before_writing(setup, action):
    _, db, entry, original, guard, _ = setup
    await command(setup, action)
    expected = {"entry": entry}
    if action == "reverse":
        expected["reversing_record_id"] = original.id
    guard.before_change.assert_awaited_once_with(db, **expected)
    db.commit.assert_awaited_once()


@pytest.mark.parametrize("action", ["register", "reverse", "void"])
async def test_guard_rejection_rolls_back_without_appending_rent(setup, action):
    _, db, entry, _, guard, _ = setup
    guard.before_change.side_effect = RuntimeError("statement locked")
    with pytest.raises(RuntimeError, match="statement locked"):
        await command(setup, action)
    module.asset_ledger_repository.add_record.assert_not_awaited()
    assert entry.voided_at is None
    db.commit.assert_not_awaited()
    db.rollback.assert_awaited_once()


async def test_payment_replay_does_not_touch_fee_version(setup, monkeypatch):
    _, db, _, original, guard, _ = setup
    monkeypatch.setattr(
        module.asset_ledger_repository,
        "get_record_by_idempotency",
        AsyncMock(return_value=original),
    )
    result = await command(setup, "register")
    assert result.idempotent is True
    guard.before_change.assert_not_awaited()
    module.asset_ledger_repository.add_record.assert_not_awaited()
    db.commit.assert_not_awaited()


async def test_manual_owner_obligation_ensures_statement_after_flush(
    setup, monkeypatch
):
    service, db, _, _, _, identity = setup
    contract = TerminalContract(
        id="tm",
        contract_mode="direct_lease",
        start_date=date(2026, 10, 1),
        end_date=date(2026, 10, 31),
        version=1,
    )
    monkeypatch.setattr(module, "scoped_contract", AsyncMock(return_value=contract))
    monkeypatch.setattr(
        module.asset_contract_repository,
        "list_rent_schedules",
        AsyncMock(
            return_value=(
                Row(
                    stage_start=date(2026, 10, 1),
                    stage_end=date(2026, 10, 31),
                    payment_cycle="custom",
                ),
            )
        ),
    )
    monkeypatch.setattr(
        module.asset_contract_repository,
        "list_lifecycle_events",
        AsyncMock(return_value=()),
    )
    await service.create_manual(
        db,
        request=ManualRentEntryRequest(
            contract_kind="terminal",
            contract_id="tm",
            origin="manual",
            period_start="2026-10-01",
            period_end="2026-10-31",
            due_date="2026-10-15",
            amount="100",
            basis_note="合同约定",
        ),
        actor_id="actor",
        scope=Row(),
        idempotency_key="manual-key",
    )
    identity.ensure_bound_contract.assert_awaited_once_with(
        db, terminal_contract_id="tm"
    )
    db.commit.assert_awaited_once()
