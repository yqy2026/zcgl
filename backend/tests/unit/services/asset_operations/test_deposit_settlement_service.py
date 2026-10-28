from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.core.exception_handler import BaseBusinessError
from src.services.asset_operations.deposit_settlement_service import (
    choose_offsets,
    deposit_settlement_service,
)

pytestmark = pytest.mark.unit


async def test_preview_allocates_not_yet_created_obligation_with_stable_key(
    monkeypatch,
):
    from src.models.asset_contract import TerminalContract
    from src.schemas.asset_operations import TerminalContractTerminationProposal
    from src.services.asset_operations import deposit_settlement_service as module
    from src.services.asset_operations.rent_obligation_rules import ObligationTarget
    from src.services.asset_operations.rent_obligation_service import RentObligationPlan

    contract = TerminalContract(id="contract", contract_mode="sublease")
    proposal = TerminalContractTerminationProposal.model_validate(
        {
            "effective_date": "2026-06-30",
            "termination_type": "early",
            "handover_status": "pending",
            "deposit_settlement_status": "pending",
            "reason": "提前退租",
        }
    )
    monkeypatch.setattr(
        module.deposit_ledger_repository,
        "get_by_contract",
        AsyncMock(return_value=SimpleNamespace(id="deposit", collector="operator")),
    )
    monkeypatch.setattr(
        module.deposit_query_service,
        "get",
        AsyncMock(return_value=SimpleNamespace(version=1, held_amount=Decimal("100"))),
    )
    monkeypatch.setattr(
        module.asset_ledger_repository, "list_entries", AsyncMock(return_value=())
    )
    monkeypatch.setattr(
        module.asset_ledger_repository, "list_records", AsyncMock(return_value=())
    )
    target = ObligationTarget(
        "2026-05", date(2026, 5, 1), date(2026, 5, 31), date(2026, 5, 1), Decimal("150")
    )
    monkeypatch.setattr(
        module.rent_obligation_service,
        "preview",
        AsyncMock(return_value=RentObligationPlan(created=[target])),
    )
    monkeypatch.setattr(module, "business_today", lambda: date(2026, 6, 1))
    result = await deposit_settlement_service.preview(
        AsyncMock(), contract=contract, scope=SimpleNamespace(), proposal=proposal
    )
    assert result["offsets"] == [
        {"ledger_entry_id": "generated:2026-05-01", "amount": "100"}
    ]
    assert result["refundable_amount"] == "0"


async def test_prelock_locks_all_units_before_any_contract(monkeypatch):
    from src.schemas.asset_operations import TerminalContractTerminationProposal
    from src.services.asset_operations import deposit_settlement_service as module

    order = []
    monkeypatch.setattr(module, "scoped_contract", AsyncMock())
    monkeypatch.setattr(
        module.asset_ledger_repository,
        "get_entry",
        AsyncMock(
            return_value=SimpleNamespace(
                contract_kind="terminal", contract_id="ancestor"
            )
        ),
    )
    monkeypatch.setattr(
        module.asset_contract_repository,
        "list_terminal_coverages",
        AsyncMock(
            side_effect=[
                (SimpleNamespace(asset_unit_id="u2"),),
                (SimpleNamespace(asset_unit_id="u1"),),
            ]
        ),
    )

    async def lock_units(db, *, unit_ids, scope):
        order.append(("units", unit_ids))
        return [SimpleNamespace(id=key) for key in unit_ids]

    async def lock_contract(db, *, contract_id, scope, for_update):
        assert for_update is True
        order.append(("contract", contract_id))
        return object()

    monkeypatch.setattr(module.asset_unit_repository, "lock_for_write", lock_units)
    monkeypatch.setattr(module.asset_contract_repository, "get_terminal", lock_contract)
    proposal = TerminalContractTerminationProposal.model_validate(
        {
            "effective_date": "2026-06-30",
            "termination_type": "early",
            "handover_status": "pending",
            "deposit_settlement_status": "pending",
            "deposit_offset_mode": "manual",
            "deposit_offsets": [{"ledger_entry_id": "rent", "amount": "10"}],
            "reason": "提前退租",
        }
    )
    await deposit_settlement_service.prelock(
        AsyncMock(), contract_id="current", scope=SimpleNamespace(), proposal=proposal
    )
    assert order == [
        ("units", ["u1", "u2"]),
        ("contract", "ancestor"),
        ("contract", "current"),
    ]


def test_default_offsets_use_due_order_and_never_exceed_balance():
    candidates = [
        {
            "ledger_entry_id": "later",
            "due_date": date(2026, 4, 1),
            "remaining": Decimal("80"),
        },
        {
            "ledger_entry_id": "first",
            "due_date": date(2026, 3, 1),
            "remaining": Decimal("80"),
        },
    ]
    assert choose_offsets(candidates, Decimal("100"), "auto", []) == [
        {"ledger_entry_id": "first", "amount": Decimal("80")},
        {"ledger_entry_id": "later", "amount": Decimal("20")},
    ]


def test_manual_offsets_reject_duplicates_and_excess():
    candidates = [
        {
            "ledger_entry_id": "rent",
            "due_date": date(2026, 1, 1),
            "remaining": Decimal("20"),
        }
    ]
    for offsets in [
        [{"ledger_entry_id": "rent", "amount": Decimal("21")}],
        [{"ledger_entry_id": "rent", "amount": Decimal("1")}] * 2,
    ]:
        with pytest.raises(BaseBusinessError) as error:
            choose_offsets(candidates, Decimal("50"), "manual", offsets)
        assert error.value.code == "DEPOSIT_OFFSET_TARGET_INVALID"


def test_none_mode_preserves_deposit():
    assert choose_offsets([], Decimal("100"), "none", []) == []


def test_manual_total_cannot_exceed_held_amount():
    candidates = [
        {
            "ledger_entry_id": "rent",
            "due_date": date(2026, 1, 1),
            "remaining": Decimal("20"),
        }
    ]
    with pytest.raises(BaseBusinessError) as error:
        choose_offsets(
            candidates,
            Decimal("10"),
            "manual",
            [{"ledger_entry_id": "rent", "amount": Decimal("11")}],
        )
    assert error.value.code == "DEPOSIT_AMOUNT_EXCEEDS_REMAINING"


def test_none_mode_cannot_hide_manual_allocations():
    with pytest.raises(BaseBusinessError) as error:
        choose_offsets(
            [],
            Decimal("100"),
            "none",
            [{"ledger_entry_id": "rent", "amount": Decimal("1")}],
        )
    assert error.value.code == "DEPOSIT_OFFSET_NOT_ALLOWED"


async def test_event_reversal_only_reverses_outstanding_pairs_without_committing(
    monkeypatch,
):
    from src.services.asset_operations import deposit_settlement_service as module
    from src.services.asset_operations.deposit_command_service import (
        deposit_command_service,
    )

    records = [
        SimpleNamespace(id="first", deposit_entry_id="deposit"),
        SimpleNamespace(id="second", deposit_entry_id="deposit"),
    ]
    monkeypatch.setattr(
        module.deposit_settlement_repository,
        "event_deductions",
        AsyncMock(return_value=records),
    )
    monkeypatch.setattr(
        module.deposit_ledger_repository,
        "find_reversal",
        AsyncMock(side_effect=[object(), None]),
    )
    monkeypatch.setattr(
        module.deposit_query_service,
        "get",
        AsyncMock(return_value=SimpleNamespace(version=3)),
    )
    reverse = AsyncMock()
    monkeypatch.setattr(deposit_command_service, "reverse", reverse)
    db = AsyncMock()
    scope = SimpleNamespace(user_id="actor")
    await deposit_settlement_service.reverse(
        db, event_id="event", actor_id="actor", scope=scope, reason="录错"
    )
    assert reverse.await_count == 1
    assert reverse.await_args.kwargs["record_id"] == "second"
    assert reverse.await_args.kwargs["commit"] is False
    assert reverse.await_args.kwargs["request"].expected_version == 3
    db.commit.assert_not_awaited()
