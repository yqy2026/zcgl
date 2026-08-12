"""Tests for the project backfill maintenance script."""

from __future__ import annotations

import ast
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _script_path() -> Path:
    return (
        Path(__file__).resolve().parents[3]
        / "scripts"
        / "maintenance"
        / "seed_projects_from_assets.py"
    )


def _load_module() -> ModuleType:
    script_path = _script_path()
    spec = spec_from_file_location("seed_projects_from_assets", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_manager_party_id_is_required_and_validated() -> None:
    module = _load_module()
    parser = module._build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args([])
    with pytest.raises(SystemExit):
        parser.parse_args(["--manager-party-id", "not-a-uuid"])

    args = parser.parse_args(
        ["--manager-party-id", "27EF9966-98F4-4A27-A221-978F744F9DB7"]
    )
    assert args.manager_party_id == "27ef9966-98f4-4a27-a221-978f744f9db7"


def test_script_keeps_sqlalchemy_and_models_behind_crud() -> None:
    tree = ast.parse(_script_path().read_text(encoding="utf-8"))
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    direct_db_calls = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in {"add", "execute"}
    }

    assert all(not module.startswith("sqlalchemy") for module in imported_modules)
    assert all(not module.startswith("src.models") for module in imported_modules)
    assert direct_db_calls == set()


@pytest.mark.asyncio
async def test_main_reuses_existing_projects_and_active_links() -> None:
    module = _load_module()
    manager_party_id = "27ef9966-98f4-4a27-a221-978f744f9db7"
    db = MagicMock()
    db.commit = AsyncMock()
    session_context = MagicMock()
    session_context.__aenter__ = AsyncMock(return_value=db)
    session_context.__aexit__ = AsyncMock(return_value=False)

    existing_project = SimpleNamespace(id="project-1", project_code="PRJ-EXISTING")
    created_project = SimpleNamespace(id="project-2", project_code="PRJ-CREATED")
    project_service = MagicMock()
    project_service.create_project = AsyncMock(return_value=created_project)

    grouped_assets = {
        "Existing Project": ["asset-1"],
        "New Project": ["asset-2", "asset-3"],
    }
    existing_link = SimpleNamespace(id="link-1")

    with (
        patch.object(module, "async_session_scope", return_value=session_context),
        patch.object(module, "ProjectService", return_value=project_service),
        patch.object(
            module.project_asset_crud,
            "get_asset_ids_grouped_by_project_name",
            new=AsyncMock(return_value=grouped_assets),
        ) as get_groups,
        patch.object(
            module.project_crud,
            "get_by_name",
            new=AsyncMock(side_effect=[existing_project, None]),
        ),
        patch.object(
            module.project_asset_crud,
            "get_active_by_asset_id",
            new=AsyncMock(side_effect=[existing_link, None, None]),
        ),
        patch.object(
            module.project_asset_crud,
            "create_active",
            new=AsyncMock(),
        ) as create_active,
    ):
        summary = await module.main(manager_party_id=manager_party_id)

    get_groups.assert_awaited_once_with(db)
    project_service.create_project.assert_awaited_once()
    project_create_call = project_service.create_project.await_args
    project_create = project_create_call.kwargs["obj_in"]
    assert project_create.manager_party_id == manager_party_id
    assert project_create_call.kwargs["commit"] is False
    assert create_active.await_count == 2
    assert [call.kwargs for call in create_active.await_args_list] == [
        {"db": db, "project_id": "project-2", "asset_id": "asset-2"},
        {"db": db, "project_id": "project-2", "asset_id": "asset-3"},
    ]
    db.commit.assert_awaited_once_with()
    assert summary == {
        "project_names": 2,
        "projects_created": 1,
        "projects_existing": 1,
        "asset_links_created": 2,
        "asset_links_existing": 1,
        "detail": [
            {
                "project_name": "Existing Project",
                "project_code": "PRJ-EXISTING",
                "assets": 1,
                "links_created": 0,
            },
            {
                "project_name": "New Project",
                "project_code": "PRJ-CREATED",
                "assets": 2,
                "links_created": 2,
            },
        ],
    }


@pytest.mark.asyncio
async def test_main_does_not_commit_partial_results_after_link_failure() -> None:
    module = _load_module()
    db = MagicMock()
    db.commit = AsyncMock()
    session_context = MagicMock()
    session_context.__aenter__ = AsyncMock(return_value=db)
    session_context.__aexit__ = AsyncMock(return_value=False)
    project_service = MagicMock()
    project_service.create_project = AsyncMock(
        return_value=SimpleNamespace(id="project-1", project_code="PRJ-CREATED")
    )

    with (
        patch.object(module, "async_session_scope", return_value=session_context),
        patch.object(module, "ProjectService", return_value=project_service),
        patch.object(
            module.project_asset_crud,
            "get_asset_ids_grouped_by_project_name",
            new=AsyncMock(return_value={"New Project": ["asset-1"]}),
        ),
        patch.object(
            module.project_crud, "get_by_name", new=AsyncMock(return_value=None)
        ),
        patch.object(
            module.project_asset_crud,
            "get_active_by_asset_id",
            new=AsyncMock(return_value=None),
        ),
        patch.object(
            module.project_asset_crud,
            "create_active",
            new=AsyncMock(side_effect=RuntimeError("link failed")),
        ),
    ):
        with pytest.raises(RuntimeError, match="link failed"):
            await module.main(manager_party_id="27ef9966-98f4-4a27-a221-978f744f9db7")

    assert project_service.create_project.await_args.kwargs["commit"] is False
    db.commit.assert_not_awaited()
