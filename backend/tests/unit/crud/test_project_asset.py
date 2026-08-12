"""Unit tests for project-asset binding CRUD helpers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.crud.project_asset import CRUDProjectAsset
from src.models.project_asset import ProjectAsset

pytestmark = pytest.mark.asyncio


async def test_grouped_asset_ids_excludes_empty_project_names() -> None:
    db = MagicMock()
    execute_result = MagicMock()
    execute_result.all.return_value = [
        ("Alpha", "asset-2"),
        ("Alpha", "asset-1"),
        ("Beta", "asset-3"),
    ]
    db.execute = AsyncMock(return_value=execute_result)

    result = await CRUDProjectAsset().get_asset_ids_grouped_by_project_name(db)

    assert result == {
        "Alpha": ["asset-2", "asset-1"],
        "Beta": ["asset-3"],
    }
    stmt = db.execute.await_args.args[0]
    sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))
    assert "assets.project_name IS NOT NULL" in sql
    assert "assets.project_name != ''" in sql
    assert "ORDER BY assets.project_name, assets.id" in sql


async def test_get_active_by_asset_id_filters_current_binding() -> None:
    binding = SimpleNamespace(id="binding-1")
    db = MagicMock()
    execute_result = MagicMock()
    execute_result.scalars.return_value.first.return_value = binding
    db.execute = AsyncMock(return_value=execute_result)

    result = await CRUDProjectAsset().get_active_by_asset_id(
        db,
        asset_id="asset-1",
    )

    assert result is binding
    stmt = db.execute.await_args.args[0]
    sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))
    assert "project_assets.asset_id = 'asset-1'" in sql
    assert "project_assets.valid_to IS NULL" in sql


async def test_create_active_flushes_without_committing() -> None:
    db = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    result = await CRUDProjectAsset().create_active(
        db,
        project_id="project-1",
        asset_id="asset-1",
    )

    assert isinstance(result, ProjectAsset)
    assert result.project_id == "project-1"
    assert result.asset_id == "asset-1"
    db.add.assert_called_once_with(result)
    db.flush.assert_awaited_once_with()
    db.commit.assert_not_awaited()
