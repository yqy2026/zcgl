"""Replanning preserves locked facts and reuses voided rows."""

from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.crud.asset_ledger import AssetLedgerRepository
from src.models.asset_contract import (
    ContractLifecycleEvent,
    ContractRentSchedule,
    TerminalContract,
    UpstreamContract,
)
from src.models.asset_ledger import RentLedgerEntry, RentPaymentRecord
from src.services.asset_operations.rent_obligation_service import RentObligationService

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_direct_rent_replan_ensures_statements_before_final_flush(
    setup, monkeypatch
):
    from src.services.asset_operations import rent_obligation_service as module

    service, repo, db = setup
    repo.contract = TerminalContract(
        id="contract",
        contract_mode="direct_lease",
        upstream_contract_id="up-1",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 3, 31),
        version=1,
    )
    fees = MagicMock(reconcile=AsyncMock())
    owner = AsyncMock(return_value="owner-1")
    monkeypatch.setattr(module, "management_fee_entry_service", fees)
    monkeypatch.setattr(
        module.management_fee_statement_repository, "bound_owner", owner
    )
    await service.replan(
        db,
        contract_kind="terminal",
        contract_id="contract",
        actor_id="actor",
        correlation_id="new",
    )
    fees.reconcile.assert_awaited_once()
    assert fees.reconcile.await_args.kwargs["owner_party_id"] == "owner-1"
    assert fees.reconcile.await_args.kwargs["new_periods"] == (
        "2026-01",
        "2026-02",
        "2026-03",
    )
    db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_fee_creation_error_is_not_swallowed_by_rent_replan(setup, monkeypatch):
    from src.services.asset_operations import rent_obligation_service as module

    service, repo, db = setup
    repo.contract = TerminalContract(
        id="contract",
        contract_mode="direct_lease",
        upstream_contract_id="up-1",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 3, 31),
        version=1,
    )
    monkeypatch.setattr(
        module.management_fee_statement_repository,
        "bound_owner",
        AsyncMock(return_value="owner-1"),
    )
    monkeypatch.setattr(
        module,
        "management_fee_entry_service",
        MagicMock(reconcile=AsyncMock(side_effect=RuntimeError("fee write failed"))),
    )
    with pytest.raises(RuntimeError, match="fee write failed"):
        await service.replan(
            db,
            contract_kind="terminal",
            contract_id="contract",
            actor_id="actor",
            correlation_id="new",
        )
    db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_binding_upstream_after_generation_creates_missing_fee_statement(
    setup, monkeypatch
):
    from src.services.asset_operations import rent_obligation_service as module

    service, repo, db = setup
    repo.contract = TerminalContract(
        id="contract",
        contract_mode="direct_lease",
        upstream_contract_id=None,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 3, 31),
        version=1,
    )
    owner = AsyncMock(return_value=None)
    fees = MagicMock(reconcile=AsyncMock())
    monkeypatch.setattr(
        module.management_fee_statement_repository, "bound_owner", owner
    )
    monkeypatch.setattr(module, "management_fee_entry_service", fees)
    kwargs = dict(
        contract_kind="terminal",
        contract_id="contract",
        actor_id="actor",
        correlation_id="binding",
    )
    await service.replan(db, **kwargs)
    fees.reconcile.assert_not_awaited()
    repo.contract.upstream_contract_id = "up-1"
    owner.return_value = "owner-1"
    plan = await service.replan(db, **kwargs)
    assert len(plan.updated) == 3
    assert plan.created == []
    assert fees.reconcile.await_args.kwargs["new_periods"] == (
        "2026-01",
        "2026-02",
        "2026-03",
    )


class Repository(AssetLedgerRepository):
    def __init__(self):
        self.contract = UpstreamContract(
            id="contract",
            contract_type="lease",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
            version=1,
        )
        self.schedules = [
            ContractRentSchedule(
                id="stage",
                contract_kind="upstream",
                contract_id="contract",
                stage_start=date(2026, 1, 1),
                stage_end=date(2026, 3, 31),
                actual_monthly_rent=Decimal("1000"),
                payment_cycle="monthly",
                due_day=25,
            )
        ]
        self.entries = []
        self.records = []
        self.events = []

    async def load_contract_facts(self, db, **kwargs):
        return self.contract, tuple(self.schedules), tuple(self.events)

    async def list_entries(self, db, **kwargs):
        return tuple(self.entries)

    async def list_records(self, db, **kwargs):
        return tuple(self.records)

    async def add_entry(self, db, *, entry):
        self.entries.append(entry)


@pytest.fixture
def setup(monkeypatch):
    from src.services.asset_operations import rent_obligation_service as module

    monkeypatch.setattr(module, "record_contract_change", AsyncMock())
    repo = Repository()
    db = MagicMock(flush=AsyncMock())
    return RentObligationService(repository=repo), repo, db


@pytest.mark.asyncio
async def test_replan_voids_unpaid_past_rows_but_keeps_registered_and_restores_same_ids(
    setup,
):
    service, repo, db = setup
    kwargs = dict(contract_kind="upstream", contract_id="contract", actor_id="actor")
    await service.replan(db, correlation_id="initial", **kwargs)
    assert len(repo.entries) == 3
    original_ids = [entry.id for entry in repo.entries]
    repo.records.append(
        RentPaymentRecord(
            id="payment",
            ledger_entry_id=repo.entries[-1].id,
            record_type="payment",
            amount=Decimal("100"),
            reverses_record_id=None,
        )
    )
    repo.events.append(
        ContractLifecycleEvent(
            id="exit", event_type="exited", effective_date=date(2026, 2, 1)
        )
    )
    plan = await service.replan(db, correlation_id="exit", **kwargs)
    assert plan.voided == [repo.entries[1].id]
    assert plan.mismatched == [repo.entries[2].id]
    assert repo.entries[1].voided_at is not None
    assert repo.entries[2].voided_at is None
    repo.events.append(
        ContractLifecycleEvent(
            id="reversal", event_type="reversed", reversed_event_id="exit"
        )
    )
    plan = await service.replan(db, correlation_id="reversal", **kwargs)
    assert plan.restored == [repo.entries[1].id]
    assert [entry.id for entry in repo.entries] == original_ids
    assert all(entry.voided_at is None for entry in repo.entries)


@pytest.mark.asyncio
async def test_schedule_correction_only_replans_current_or_explicit_gap_periods(setup):
    service, repo, db = setup
    kwargs = dict(contract_kind="upstream", contract_id="contract", actor_id="actor")
    await service.replan(db, correlation_id="initial", **kwargs)
    repo.schedules[0].actual_monthly_rent = Decimal("2000")
    plan = await service.replan(
        db,
        correlation_id="correction",
        replan_from=date(2026, 3, 1),
        supplemental_ranges=[(date(2026, 2, 15), date(2026, 2, 28))],
        **kwargs,
    )
    assert plan.updated == [repo.entries[1].id, repo.entries[2].id]
    assert [entry.due_amount for entry in repo.entries] == [
        Decimal("1000"),
        Decimal("2000"),
        Decimal("2000"),
    ]


@pytest.mark.asyncio
async def test_manual_rows_restore_only_when_their_termination_is_reversed(setup):
    service, repo, db = setup
    kwargs = dict(contract_kind="upstream", contract_id="contract", actor_id="actor")
    manual = RentLedgerEntry(
        id="manual",
        contract_kind="upstream",
        contract_id="contract",
        period_start=date(2026, 3, 1),
        period_end=date(2026, 3, 31),
        origin="manual",
        voided_at=None,
    )
    independently_voided = RentLedgerEntry(
        id="manual-voided",
        contract_kind="upstream",
        contract_id="contract",
        period_start=date(2026, 3, 1),
        period_end=date(2026, 3, 31),
        origin="manual",
        voided_at=datetime.now(UTC),
        void_correlation_id="user-void",
    )
    repo.entries.extend([manual, independently_voided])
    repo.events.append(
        ContractLifecycleEvent(
            id="exit", event_type="exited", effective_date=date(2026, 2, 1)
        )
    )
    await service.replan(db, correlation_id="exit", **kwargs)
    assert manual.void_correlation_id == "exit"
    repo.events.append(
        ContractLifecycleEvent(
            id="reversal", event_type="reversed", reversed_event_id="exit"
        )
    )
    plan = await service.replan(db, correlation_id="reverse", **kwargs)
    assert "manual" in plan.restored
    assert independently_voided.voided_at is not None


@pytest.mark.asyncio
async def test_locked_midmonth_row_blocks_overlapping_full_month_replacement(setup):
    service, repo, db = setup
    repo.contract.end_date = date(2026, 1, 31)
    repo.schedules[0].stage_start = date(2026, 1, 15)
    repo.schedules[0].stage_end = date(2026, 1, 31)
    kwargs = dict(contract_kind="upstream", contract_id="contract", actor_id="actor")
    await service.replan(db, correlation_id="initial", **kwargs)
    original = repo.entries[0]
    repo.records.append(
        RentPaymentRecord(
            id="registered",
            ledger_entry_id=original.id,
            record_type="payment",
            amount=Decimal("100"),
            reverses_record_id=None,
        )
    )
    repo.schedules[0].stage_start = date(2026, 1, 1)
    plan = await service.replan(
        db,
        correlation_id="correction",
        supplemental_ranges=[(date(2026, 1, 1), date(2026, 1, 14))],
        **kwargs,
    )
    assert plan.created == []
    assert plan.mismatched == [original.id]
    assert len(repo.entries) == 1
    repo.records.append(
        RentPaymentRecord(
            id="reversed",
            ledger_entry_id=original.id,
            record_type="reversal",
            amount=Decimal("100"),
            reverses_record_id="registered",
        )
    )
    plan = await service.replan(db, correlation_id="reversal", **kwargs)
    assert len(plan.created) == 1
    assert original.voided_at is not None
    assert repo.entries[-1].period_start == date(2026, 1, 1)


@pytest.mark.asyncio
async def test_same_money_new_source_refreshes_unlocked_snapshot_only(setup):
    service, repo, db = setup
    kwargs = dict(contract_kind="upstream", contract_id="contract", actor_id="actor")
    await service.replan(db, correlation_id="initial", **kwargs)
    locked = repo.entries[0]
    repo.records.append(
        RentPaymentRecord(
            id="registered",
            ledger_entry_id=locked.id,
            record_type="payment",
            amount=Decimal("100"),
            reverses_record_id=None,
        )
    )
    repo.schedules[0].id = "new-stage-id"
    plan = await service.replan(db, correlation_id="correction", **kwargs)
    assert locked.id not in plan.updated
    assert locked.locked_source["rent_schedules"][0]["id"] == "stage"
    assert len(plan.updated) == 2
    assert repo.entries[1].locked_source["rent_schedules"][0]["id"] == "new-stage-id"
