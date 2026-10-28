from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.services.asset_operations.deposit_entry_service import DepositEntryService

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


@pytest.mark.parametrize(
    ("kind", "fields", "collector"),
    [
        ("upstream", {"contract_type": "lease"}, "owner"),
        ("terminal", {"contract_mode": "sublease"}, "operator"),
        ("terminal", {"contract_mode": "direct_lease"}, "owner"),
    ],
)
async def test_confirmation_creates_one_entry_without_committing(
    kind, fields, collector
):
    repository = SimpleNamespace(
        get_by_contract=AsyncMock(return_value=None), add_entry=AsyncMock()
    )
    db = AsyncMock()
    service = DepositEntryService(repository=repository)
    entry = await service.ensure_entry(
        db, contract_kind=kind, contract=SimpleNamespace(id="contract", **fields)
    )
    assert entry.contract_id == "contract"
    assert entry.contract_kind == kind
    assert entry.collector == collector
    repository.add_entry.assert_awaited_once_with(db, entry=entry)
    db.commit.assert_not_called()


async def test_ensure_entry_replays_existing_without_writing():
    existing = object()
    repository = SimpleNamespace(
        get_by_contract=AsyncMock(return_value=existing), add_entry=AsyncMock()
    )
    entry = await DepositEntryService(repository=repository).ensure_entry(
        AsyncMock(),
        contract_kind="terminal",
        contract=SimpleNamespace(id="successor", contract_mode="sublease"),
    )
    assert entry is existing
    repository.add_entry.assert_not_called()


async def test_management_agreement_has_no_deposit_entry():
    repository = SimpleNamespace(get_by_contract=AsyncMock(), add_entry=AsyncMock())
    result = await DepositEntryService(repository=repository).ensure_entry(
        AsyncMock(),
        contract_kind="upstream",
        contract=SimpleNamespace(id="agreement", contract_type="management_agreement"),
    )
    assert result is None
    repository.get_by_contract.assert_not_called()
    repository.add_entry.assert_not_called()
