"""Deferral marks are source facts with mandatory reasons and unique rows."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import create_engine, insert
from sqlalchemy.exc import IntegrityError

from src.crud.management_fee_deferral import management_fee_deferral_repository
from src.models.management_fee_deferral import ManagementFeeDeferral

pytestmark = pytest.mark.unit


def values(**changes):
    result = dict(
        id="mark-1",
        statement_id="st-1",
        rent_ledger_entry_id="rent-1",
        reason="下月补齐",
        created_by="actor",
        created_at=datetime.now(UTC),
    )
    result.update(changes)
    return result


@pytest.mark.parametrize("reason", [None, "", "  "])
def test_reason_must_be_present_and_nonblank(reason):
    table = ManagementFeeDeferral.__table__
    engine = create_engine("sqlite://")
    table.create(engine)
    with engine.begin() as conn, pytest.raises(IntegrityError):
        conn.execute(insert(table).values(**values(reason=reason)))


def test_statement_entry_mark_is_unique_but_next_statement_may_mark_again():
    table = ManagementFeeDeferral.__table__
    engine = create_engine("sqlite://")
    table.create(engine)
    with engine.begin() as conn:
        conn.execute(insert(table).values(**values()))
        conn.execute(insert(table).values(**values(id="mark-2", statement_id="st-2")))
        with pytest.raises(IntegrityError):
            conn.execute(insert(table).values(**values(id="mark-3")))


@pytest.mark.asyncio
async def test_repository_scopes_marks_and_never_owns_transaction():
    mark = ManagementFeeDeferral(**values())
    result = MagicMock()
    result.scalars.return_value.all.return_value = [mark]
    db = MagicMock(execute=AsyncMock(return_value=result))
    assert await management_fee_deferral_repository.list_marks(
        db, statement_id="st-1"
    ) == (mark,)
    query = db.execute.await_args.args[0]
    assert "statement_id" in str(query)
    assert "st-1" in query.compile().params.values()
    await management_fee_deferral_repository.add_mark(db, mark=mark)
    db.add.assert_called_once_with(mark)
    db.flush.assert_not_called()
    db.commit.assert_not_called()
