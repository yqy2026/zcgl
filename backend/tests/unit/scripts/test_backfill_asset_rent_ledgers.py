from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from scripts import backfill_asset_rent_ledgers as script

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


@pytest.mark.parametrize("apply", [False, True])
async def test_backfill_uses_repository_and_commits_only_when_requested(
    monkeypatch, apply
):
    db = AsyncMock()
    db.__aenter__.return_value = db
    engine = MagicMock(dispose=AsyncMock())
    monkeypatch.setattr(script, "create_async_engine", lambda *_: engine)
    monkeypatch.setattr(script, "async_sessionmaker", lambda *_, **__: lambda: db)
    contract = SimpleNamespace(id="contract", contract_number="test")
    repository = SimpleNamespace(
        list_contracts=AsyncMock(return_value=[("terminal", contract)]),
        lock_contract=AsyncMock(),
    )
    monkeypatch.setattr(script, "rent_backfill_repository", repository)
    monkeypatch.setattr(
        script,
        "UserCRUD",
        lambda: SimpleNamespace(get_async=AsyncMock(return_value=object())),
    )
    plan = SimpleNamespace(targets={}, gaps=(), summary=lambda: {})
    obligations = SimpleNamespace(
        preview=AsyncMock(return_value=plan), replan=AsyncMock()
    )
    monkeypatch.setattr(script, "rent_obligation_service", obligations)
    await script.run(apply=apply, actor_id="actor" if apply else None)
    repository.list_contracts.assert_awaited_once_with(db)
    assert repository.lock_contract.await_count == int(apply)
    assert obligations.replan.await_count == int(apply)
    assert db.commit.await_count == int(apply)
    assert db.rollback.await_count == int(not apply)
    db.execute.assert_not_called()
    db.refresh.assert_not_called()
    db.get.assert_not_called()
    engine.dispose.assert_awaited_once()
