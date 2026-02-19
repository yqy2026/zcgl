"""Unit tests for authz CRUD helpers."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.crud.authz import CRUDAuthz


@pytest.mark.asyncio
async def test_create_policy_adds_and_flushes(mock_db) -> None:
    crud = CRUDAuthz()

    policy = await crud.create_policy(
        mock_db,
        obj_in={"name": "asset_read", "effect": "allow", "priority": 10},
        commit=False,
    )

    assert policy.name == "asset_read"
    mock_db.add.assert_called_once()
    mock_db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_unbind_role_policy_returns_deleted_count(mock_db) -> None:
    crud = CRUDAuthz()
    mock_db.execute = AsyncMock(return_value=SimpleNamespace(rowcount=2))

    deleted = await crud.unbind_role_policy(
        mock_db,
        role_id="role-1",
        policy_id="policy-1",
        commit=False,
    )

    assert deleted == 2
    mock_db.flush.assert_awaited_once()
