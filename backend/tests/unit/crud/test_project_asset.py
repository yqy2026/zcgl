"""Unit tests for project-asset CRUD helpers."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.crud.project_asset import CRUDProjectAsset


@pytest.mark.asyncio
async def test_bind_asset_adds_record(mock_db) -> None:
    crud = CRUDProjectAsset()

    relation = await crud.bind_asset(
        mock_db,
        obj_in={"project_id": "project-1", "asset_id": "asset-1"},
        commit=False,
    )

    assert relation.project_id == "project-1"
    assert relation.asset_id == "asset-1"
    mock_db.add.assert_called_once()
    mock_db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_unbind_asset_returns_none_when_no_active_binding(mock_db) -> None:
    crud = CRUDProjectAsset()

    scalars_result = MagicMock()
    scalars_result.first.return_value = None
    execute_result = MagicMock()
    execute_result.scalars.return_value = scalars_result
    mock_db.execute = AsyncMock(return_value=execute_result)

    relation = await crud.unbind_asset(
        mock_db,
        project_id="project-1",
        asset_id="asset-1",
        commit=False,
    )

    assert relation is None


@pytest.mark.asyncio
async def test_unbind_asset_sets_valid_to_when_binding_exists(mock_db) -> None:
    crud = CRUDProjectAsset()

    existing = MagicMock()
    existing.valid_to = None
    existing.unbind_reason = None

    scalars_result = MagicMock()
    scalars_result.first.return_value = existing
    execute_result = MagicMock()
    execute_result.scalars.return_value = scalars_result
    mock_db.execute = AsyncMock(return_value=execute_result)

    relation = await crud.unbind_asset(
        mock_db,
        project_id="project-1",
        asset_id="asset-1",
        unbind_reason="手动解绑",
        commit=False,
    )

    assert relation is existing
    assert existing.valid_to is not None
    assert existing.unbind_reason == "手动解绑"
    mock_db.flush.assert_awaited_once()
