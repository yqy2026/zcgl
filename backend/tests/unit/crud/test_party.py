"""Unit tests for party CRUD helpers."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.crud.party import CRUDParty


@pytest.mark.asyncio
async def test_create_party_adds_and_refreshes(mock_db) -> None:
    crud = CRUDParty()

    result = await crud.create_party(
        mock_db,
        obj_in={"party_type": "organization", "name": "总部", "code": "HQ"},
        commit=False,
    )

    assert result.name == "总部"
    mock_db.add.assert_called_once()
    mock_db.flush.assert_awaited_once()
    mock_db.refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_descendants_returns_recursive_ids(mock_db) -> None:
    crud = CRUDParty()
    execute_result = MagicMock()
    execute_result.fetchall.return_value = [("child-1",), ("child-2",)]
    mock_db.execute = AsyncMock(return_value=execute_result)

    descendants = await crud.get_descendants(
        mock_db,
        party_id="root-1",
        include_self=True,
    )

    assert descendants == ["root-1", "child-1", "child-2"]


@pytest.mark.asyncio
async def test_remove_hierarchy_returns_deleted_count(mock_db) -> None:
    crud = CRUDParty()
    mock_db.execute = AsyncMock(return_value=SimpleNamespace(rowcount=1))

    deleted = await crud.remove_hierarchy(
        mock_db,
        parent_party_id="p-1",
        child_party_id="p-2",
        commit=False,
    )

    assert deleted == 1
    mock_db.flush.assert_awaited_once()
