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


@pytest.mark.parametrize(
    "held,clawback,additional,refundable",
    [
        ("100", "0", "50", "0"),
        ("100", "20", "70", "0"),
        ("200", "20", "0", "30"),
    ],
)
async def test_preview_allocates_not_yet_created_obligation_with_stable_key(
    monkeypatch,
    held,
    clawback,
    additional,
    refundable,
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
            "clawback_amount": clawback,
            "clawback_basis": "优惠免租补收",
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
        AsyncMock(return_value=SimpleNamespace(version=1, held_amount=Decimal(held))),
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
    assert result["offsets"][0]["ledger_entry_id"] == "generated:2026-05-01"
    assert result["refundable_amount"] == refundable
    assert result["additional_due_amount"] == additional


@pytest.mark.parametrize(
    "mode,termination_type,basis",
    [
        ("direct_lease", "early", "依据"),
        ("sublease", "expiry", "依据"),
        ("sublease", "early", ""),
    ],
)
async def test_ineligible_clawback_returns_contract_error(
    monkeypatch, mode, termination_type, basis
):
    from src.models.asset_contract import TerminalContract
    from src.schemas.asset_operations import TerminalContractTerminationProposal
    from src.services.asset_operations import deposit_settlement_service as module

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
    contract = TerminalContract(id="contract", contract_mode=mode)
    proposal = TerminalContractTerminationProposal.model_validate(
        {
            "effective_date": "2026-06-30",
            "termination_type": termination_type,
            "handover_status": "pending",
            "deposit_settlement_status": "pending",
            "reason": "退租",
            "clawback_amount": "20",
            "clawback_basis": basis,
        }
    )
    with pytest.raises(BaseBusinessError) as error:
        await deposit_settlement_service.preview(
            AsyncMock(), contract=contract, scope=SimpleNamespace(), proposal=proposal
        )
    assert error.value.code == "RENT_LEDGER_MANUAL_ENTRY_NOT_ALLOWED"
    assert error.value.status_code == 409


@pytest.mark.parametrize("mode", ["manual", "auto"])
async def test_prelock_locks_all_units_before_any_contract(monkeypatch, mode):
    from src.schemas.asset_operations import TerminalContractTerminationProposal
    from src.services.asset_operations import deposit_settlement_service as module

    order = []
    monkeypatch.setattr(
        deposit_settlement_service,
        "_visible_ancestors",
        AsyncMock(return_value=["ancestor"]),
        raising=False,
    )
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
            "deposit_offset_mode": mode,
            "deposit_offsets": [{"ledger_entry_id": "rent", "amount": "10"}]
            if mode == "manual"
            else [],
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


async def test_auto_preview_prefers_ancestor_arrears(monkeypatch):
    from src.models.asset_contract import TerminalContract
    from src.schemas.asset_operations import TerminalContractTerminationProposal
    from src.services.asset_operations import deposit_settlement_service as module
    from src.services.asset_operations.rent_obligation_service import RentObligationPlan

    contract = TerminalContract(
        id="current", contract_mode="sublease", renewed_from_id="parent"
    )
    monkeypatch.setattr(
        deposit_settlement_service,
        "_visible_ancestors",
        AsyncMock(return_value=["parent"]),
        raising=False,
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

    async def entries(db, *, contract_kind, contract_id):
        month, amount = (4, "100") if contract_id == "parent" else (5, "50")
        return [
            SimpleNamespace(
                id=contract_id,
                contract_id=contract_id,
                entry_type="terminal_receivable",
                voided_at=None,
                period_start=date(2026, month, 1),
                period_end=date(2026, month, 28),
                due_date=date(2026, month, 1),
                due_amount=Decimal(amount),
                version=1,
            )
        ]

    monkeypatch.setattr(module.asset_ledger_repository, "list_entries", entries)
    monkeypatch.setattr(
        module.asset_ledger_repository, "list_records", AsyncMock(return_value=())
    )
    monkeypatch.setattr(
        module.rent_obligation_service,
        "preview",
        AsyncMock(return_value=RentObligationPlan()),
    )
    monkeypatch.setattr(module, "business_today", lambda: date(2026, 6, 1))
    proposal = TerminalContractTerminationProposal.model_validate(
        dict(
            effective_date="2026-06-30",
            termination_type="early",
            handover_status="pending",
            deposit_settlement_status="pending",
            reason="退租",
        )
    )
    result = await deposit_settlement_service.preview(
        AsyncMock(), contract=contract, scope=SimpleNamespace(), proposal=proposal
    )
    assert result["offsets"] == [{"ledger_entry_id": "parent", "amount": "100"}]
    assert result["refundable_amount"] == "0"
    assert result["additional_due_amount"] == "50"


@pytest.mark.parametrize("visible,active", [(True, True), (False, True), (True, False)])
async def test_ancestors_require_visible_unrevoked_renewal(
    monkeypatch, visible, active
):
    from src.models.asset_contract import TerminalContract
    from src.services.asset_operations import deposit_settlement_service as module

    parent = TerminalContract(id="parent", contract_mode="sublease")
    contract = TerminalContract(
        id="current", contract_mode="sublease", renewed_from_id="parent"
    )
    facts = SimpleNamespace(
        contracts=(parent, contract),
        events=(
            SimpleNamespace(
                id="renewal",
                event_type="renewed",
                contract_id="parent",
                successor_contract_id="current",
            ),
        )
        if active
        else (),
    )
    monkeypatch.setattr(module, "scoped_contract", AsyncMock(return_value=contract))
    monkeypatch.setattr(
        module.deposit_query_repository, "load_facts", AsyncMock(return_value=facts)
    )
    monkeypatch.setattr(
        module.asset_contract_repository,
        "get_terminal",
        AsyncMock(return_value=parent if visible else None),
    )
    assert await deposit_settlement_service._visible_ancestors(
        AsyncMock(), contract_id="current", scope=SimpleNamespace()
    ) == (["parent"] if visible and active else [])
