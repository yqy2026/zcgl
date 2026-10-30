"""Owner rent mutations lock counted facts and invalidate open fee versions."""

from types import SimpleNamespace as Row
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.services.asset_operations.management_fee_write_guard import (
    ManagementFeeWriteGuard,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


def setup_guard(statements=(), lines=()):
    repo = MagicMock(
        bound_owner=AsyncMock(return_value="owner"),
        lock_owner=AsyncMock(),
        list_statements=AsyncMock(return_value=statements),
        list_lines=AsyncMock(return_value=lines),
        ensure_draft=AsyncMock(
            return_value=Row(id="new", period="2026-11", status=None, version=1)
        ),
    )
    return ManagementFeeWriteGuard(repository=repo), repo, MagicMock()


async def test_confirmed_receipt_reversal_is_locked_before_any_version_change():
    statement = Row(id="confirmed", period="2026-10", status="confirmed", version=2)
    service, repo, db = setup_guard(
        (statement,), (Row(statement_id="confirmed", counted_record_ids=["receipt"]),)
    )
    with pytest.raises(Exception) as caught:
        await service.before_change(
            db,
            entry=Row(contract_id="tm", period="2026-10", id="rent"),
            reversing_record_id="receipt",
        )
    assert caught.value.code == "MANAGEMENT_FEE_STATEMENT_LOCKED"
    assert statement.version == 2
    repo.ensure_draft.assert_not_awaited()
    db.commit.assert_not_called()


async def test_current_draft_version_changes_with_its_rent_fact():
    statement = Row(id="draft", period="2026-10", status=None, version=2)
    service, repo, db = setup_guard((statement,))
    await service.before_change(
        db, entry=Row(contract_id="tm", period="2026-10", id="rent")
    )
    assert statement.version == 3
    db.commit.assert_not_called()


async def test_new_receipt_after_confirmation_invalidates_next_open_statement():
    old = Row(id="confirmed", period="2026-10", status="confirmed", version=2)
    following = Row(id="following", period="2026-11", status=None, version=3)
    service, repo, db = setup_guard((old, following))
    await service.before_change(
        db, entry=Row(contract_id="tm", period="2026-10", id="rent")
    )
    assert following.version == 4
    assert old.version == 2


async def test_no_binding_does_not_create_a_fee_statement():
    service, repo, db = setup_guard()
    repo.bound_owner.return_value = None
    await service.before_change(
        db, entry=Row(contract_id="tm", period="2026-10", id="rent")
    )
    repo.lock_owner.assert_not_awaited()
    repo.ensure_draft.assert_not_awaited()


async def test_missing_next_statement_is_created_after_latest_confirmation():
    service, repo, db = setup_guard(
        (Row(id="old", period="2026-10", status="confirmed", version=1),)
    )
    await service.before_change(
        db, entry=Row(contract_id="tm", period="2026-10", id="rent")
    )
    repo.ensure_draft.assert_awaited_once_with(
        db, owner_party_id="owner", period="2026-11"
    )


async def test_superseded_snapshot_no_longer_locks_its_counted_receipt():
    old = Row(id="old", period="2026-10", status="superseded", version=2)
    successor = Row(id="new", period="2026-10", status=None, version=1)
    service, repo, db = setup_guard((old, successor))
    await service.before_change(
        db,
        entry=Row(contract_id="tm", period="2026-10", id="rent"),
        reversing_record_id="receipt",
    )
    repo.list_lines.assert_awaited_once_with(db, statement_ids=[])
    assert successor.version == 2
    assert old.version == 2
