"""Regression tests for the first asset-operations v5 schema migration."""

from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType

import pytest


def _load_migration_module() -> ModuleType:
    module_path = (
        Path(__file__).resolve().parents[3]
        / "alembic"
        / "versions"
        / "20261023_asset_operations_v5_asset_units.py"
    )
    spec = spec_from_file_location("asset_operations_v5_asset_units", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_follows_current_head() -> None:
    module = _load_migration_module()

    assert module.down_revision == "20260808_drop_unused_tables_fields"


def test_migration_creates_asset_unit_tables_with_named_constraints(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_migration_module()
    table_calls: dict[str, tuple[object, ...]] = {}
    index_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
    monkeypatch.setattr(
        module.op,
        "create_table",
        lambda name, *items, **_kwargs: table_calls.setdefault(name, items),
    )
    monkeypatch.setattr(
        module.op,
        "create_index",
        lambda *args, **kwargs: index_calls.append((args, kwargs)),
    )

    module.upgrade()

    assert set(table_calls) == {
        "asset_units",
        "asset_unit_boundary_changes",
        "asset_unit_boundary_sources",
        "property_certificate_asset_units",
    }
    asset_items = table_calls["asset_units"]
    asset_column_names = {
        item.name for item in asset_items if isinstance(item, module.sa.Column)
    }
    asset_constraint_names = {
        item.name
        for item in asset_items
        if isinstance(item, module.sa.Constraint) and item.name is not None
    }
    assert {
        "unit_code",
        "project_id",
        "owner_party_id",
        "building_area",
        "rentable_area",
        "managed_from",
        "predecessor_unit_ids",
        "version",
    } <= asset_column_names
    assert {
        "ck_asset_units_acquisition_mode",
        "ck_asset_units_rentable_area_valid",
        "uq_asset_units_unit_code",
    } <= asset_constraint_names
    assert any(args[0] == "ix_asset_units_project_id" for args, _ in index_calls)
    assert any(args[0] == "ix_asset_units_owner_party_id" for args, _ in index_calls)
    boundary_items = table_calls["asset_unit_boundary_changes"]
    boundary_column_names = {
        item.name for item in boundary_items if isinstance(item, module.sa.Column)
    }
    boundary_constraint_names = {
        item.name
        for item in boundary_items
        if isinstance(item, module.sa.Constraint) and item.name is not None
    }
    assert {"request_fingerprint", "result_data"} <= boundary_column_names
    assert "uq_asset_unit_boundary_changes_actor_request" in (boundary_constraint_names)
    boundary_source_items = table_calls["asset_unit_boundary_sources"]
    boundary_source_constraint_names = {
        item.name
        for item in boundary_source_items
        if isinstance(item, module.sa.Constraint) and item.name is not None
    }
    assert "uq_asset_unit_boundary_sources_unit" in boundary_source_constraint_names


def test_migration_downgrade_fails_loud() -> None:
    module = _load_migration_module()

    with pytest.raises(RuntimeError, match="irreversible"):
        module.downgrade()
