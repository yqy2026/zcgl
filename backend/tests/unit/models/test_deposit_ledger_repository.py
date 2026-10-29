"""Repository row locking and transaction boundaries."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.dialects import postgresql

from src.crud.deposit_ledger import deposit_ledger_repository


@pytest.mark.asyncio
async def test_deposit_for_update_refreshes_existing_identity_map():
    db = MagicMock(execute=AsyncMock())
    await deposit_ledger_repository.get_by_contract(
        db, contract_kind="terminal", contract_id="contract", for_update=True
    )
    statement = db.execute.await_args.args[0]
    assert "FOR UPDATE" in str(statement.compile(dialect=postgresql.dialect()))
    assert statement.get_execution_options()["populate_existing"] is True
    db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_empty_record_batch_does_not_query_database():
    db = MagicMock(execute=AsyncMock())
    assert await deposit_ledger_repository.list_records(db, entry_ids=[]) == ()
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_appending_record_does_not_commit_or_mutate_other_records():
    db = MagicMock()
    record = MagicMock()
    await deposit_ledger_repository.add_record(db, record=record)
    db.add.assert_called_once_with(record)
    db.commit.assert_not_called()
    db.flush.assert_not_called()
    db.delete.assert_not_called()
