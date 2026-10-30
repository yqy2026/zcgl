"""Management fee persistence preserves locking and transaction boundaries."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.dialects import postgresql

from src.crud.management_fee_statement import (
    management_fee_statement_repository as repo,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


async def test_locked_reads_refresh_identity_map_and_owner_order():
    db = MagicMock(execute=AsyncMock(return_value=MagicMock()))
    await repo.get_statement(db, statement_id="st", for_update=True)
    query = db.execute.await_args.args[0]
    assert "FOR UPDATE" in str(query.compile(dialect=postgresql.dialect()))
    assert query.get_execution_options()["populate_existing"] is True
    await repo.list_statements(db, owner_party_id="owner", for_update=True)
    query = db.execute.await_args.args[0]
    sql = str(query.compile(dialect=postgresql.dialect()))
    assert (
        "ORDER BY management_fee_statements.period, management_fee_statements.id" in sql
    )
    assert "FOR UPDATE" in sql
    assert query.get_execution_options()["populate_existing"] is True


async def test_empty_line_list_never_queries():
    db = MagicMock(execute=AsyncMock())
    assert await repo.list_lines(db, statement_ids=[]) == ()
    db.execute.assert_not_awaited()


async def test_adds_leave_flush_and_commit_to_service():
    db = MagicMock()
    row, line = MagicMock(), MagicMock()
    await repo.add_statement(db, statement=row)
    await repo.add_lines(db, lines=[line])
    db.add.assert_called_once_with(row)
    db.add_all.assert_called_once_with([line])
    db.commit.assert_not_called()
    db.flush.assert_not_called()


async def test_ensure_draft_uses_live_partial_index_and_returns_existing_identity():
    existing = MagicMock()
    result = MagicMock()
    result.scalar_one.return_value = existing
    db = MagicMock(execute=AsyncMock(side_effect=[MagicMock(), result]))
    assert (
        await repo.ensure_draft(db, owner_party_id="owner", period="2026-10")
        is existing
    )
    query = db.execute.await_args_list[0].args[0]
    sql = str(query.compile(dialect=postgresql.dialect()))
    assert (
        "ON CONFLICT (owner_party_id, period) WHERE status IS NULL OR status <> 'superseded' DO NOTHING"
        in sql
    )
    params = query.compile(dialect=postgresql.dialect()).params
    assert params["owner_party_id"] == "owner"
    assert params["period"] == "2026-10"
    assert params["statement_number"].startswith("MF-2026-10-")
    assert params["version"] == 1
    assert "base_amount" not in params
    db.commit.assert_not_called()
    db.flush.assert_not_called()
    db.begin_nested.assert_not_called()


async def test_owner_lock_and_bound_owner_filter_management_agreements():
    db = MagicMock(execute=AsyncMock(return_value=MagicMock()))
    await repo.lock_owner(db, owner_party_id="owner")
    sql = str(db.execute.await_args.args[0].compile(dialect=postgresql.dialect()))
    assert "FOR UPDATE" in sql
    await repo.bound_owner(db, terminal_contract_id="terminal")
    query = db.execute.await_args.args[0]
    sql = str(query.compile(dialect=postgresql.dialect()))
    params = query.compile(dialect=postgresql.dialect()).params
    assert "FROM upstream_contracts JOIN terminal_contracts" in sql
    assert (
        "terminal_contracts.lessor_party_id = upstream_contracts.owner_party_id" in sql
    )
    assert "direct_lease" in params.values()
    assert "management_agreement" in params.values()
