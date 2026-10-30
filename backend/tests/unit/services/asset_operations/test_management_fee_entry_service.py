"""Statement creation routes late rent without owning the rent transaction."""

from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock, MagicMock

import pytest

from src.models.management_fee_statement import ManagementFeeStatement
from src.services.asset_operations.management_fee_entry_service import (
    ManagementFeeEntryService,
)

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_late_rent_never_routes_into_an_earlier_backfill_draft():
    repo = MagicMock(
        lock_owner=AsyncMock(),
        list_statements=AsyncMock(
            return_value=[row("2026-08"), row("2026-09", "confirmed")]
        ),
        ensure_draft=AsyncMock(return_value=row("2026-10")),
    )
    await ManagementFeeEntryService(repository=repo).reconcile(
        MagicMock(),
        owner_party_id="owner",
        new_periods=("2026-09",),
        changed_periods=(),
    )
    repo.ensure_draft.assert_awaited_once_with(
        ANY, owner_party_id="owner", period="2026-10"
    )


@pytest.mark.asyncio
async def test_upstream_binding_discovers_paid_entries_but_not_confirmed_members(
    monkeypatch,
):
    from src.services.asset_operations import management_fee_entry_service as module

    entries = (
        SimpleNamespace(
            id="paid",
            period="2026-08",
            entry_type="owner_receipt_expected",
            voided_at=None,
        ),
        SimpleNamespace(
            id="listed",
            period="2026-07",
            entry_type="owner_receipt_expected",
            voided_at=None,
        ),
        SimpleNamespace(
            id="voided",
            period="2026-06",
            entry_type="owner_receipt_expected",
            voided_at="void",
        ),
    )
    monkeypatch.setattr(
        module.asset_ledger_repository, "list_entries", AsyncMock(return_value=entries)
    )
    repo = MagicMock(
        bound_owner=AsyncMock(return_value="owner"),
        list_statements=AsyncMock(return_value=[row("2026-07", "confirmed")]),
        list_lines=AsyncMock(
            return_value=[SimpleNamespace(rent_ledger_entry_id="listed")]
        ),
    )
    service = ManagementFeeEntryService(repository=repo)
    service.reconcile = AsyncMock()
    db = MagicMock()
    await service.ensure_bound_contract(db, terminal_contract_id="tm")
    service.reconcile.assert_awaited_once_with(
        db, owner_party_id="owner", new_periods=("2026-08",), changed_periods=()
    )
    db.commit.assert_not_called()


def row(period, status=None):
    return ManagementFeeStatement(
        id=period, owner_party_id="owner", period=period, status=status, version=1
    )


@pytest.mark.asyncio
async def test_late_new_obligation_uses_earliest_open_statement():
    existing = [row("2026-09", "confirmed"), row("2026-10"), row("2026-11")]
    repo = MagicMock(
        lock_owner=AsyncMock(),
        list_statements=AsyncMock(return_value=existing),
        ensure_draft=AsyncMock(),
    )
    db = MagicMock()
    await ManagementFeeEntryService(repository=repo).reconcile(
        db,
        owner_party_id="owner",
        new_periods=("2026-09",),
        changed_periods=("2026-09",),
    )
    repo.ensure_draft.assert_not_awaited()
    assert existing[1].version == 2
    assert existing[2].version == 1
    db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_late_new_obligation_creates_month_after_latest_confirmation():
    repo = MagicMock(
        lock_owner=AsyncMock(),
        list_statements=AsyncMock(return_value=[row("2026-09", "confirmed")]),
        ensure_draft=AsyncMock(return_value=row("2026-10")),
    )
    await ManagementFeeEntryService(repository=repo).reconcile(
        MagicMock(),
        owner_party_id="owner",
        new_periods=("2026-09",),
        changed_periods=(),
    )
    repo.ensure_draft.assert_awaited_once_with(
        ANY,
        owner_party_id="owner",
        period="2026-10",
    )


@pytest.mark.asyncio
async def test_future_obligation_uses_its_own_month_and_keeps_draft_amounts_empty():
    created = row("2026-12")
    repo = MagicMock(
        lock_owner=AsyncMock(),
        list_statements=AsyncMock(return_value=[]),
        ensure_draft=AsyncMock(return_value=created),
    )
    await ManagementFeeEntryService(repository=repo).reconcile(
        MagicMock(),
        owner_party_id="owner",
        new_periods=("2026-12", "2026-12"),
        changed_periods=(),
    )
    assert repo.ensure_draft.await_count == 1
    assert created.base_amount is None
    assert created.status is None


@pytest.mark.asyncio
async def test_earlier_month_without_statement_is_created_in_its_own_month():
    repo = MagicMock(
        lock_owner=AsyncMock(),
        list_statements=AsyncMock(
            return_value=[row("2026-09", "confirmed"), row("2026-10")]
        ),
        ensure_draft=AsyncMock(return_value=row("2026-08")),
    )
    await ManagementFeeEntryService(repository=repo).reconcile(
        MagicMock(),
        owner_party_id="owner",
        new_periods=("2026-08",),
        changed_periods=(),
    )
    repo.ensure_draft.assert_awaited_once_with(
        ANY, owner_party_id="owner", period="2026-08"
    )
