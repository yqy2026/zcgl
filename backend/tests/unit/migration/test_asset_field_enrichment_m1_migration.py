"""Tests for 20260305 asset field enrichment migration."""

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
        / "20260305_asset_field_enrichment_m1.py"
    )
    spec = spec_from_file_location("asset_field_enrichment_m1", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_should_follow_previous_head() -> None:
    module = _load_migration_module()

    assert module.down_revision == "20260304_rename_asset_business_model_to_revenue_mode"


def test_upgrade_should_not_backfill_address_detail_from_legacy_address(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_migration_module()
    executed_sql: list[str] = []

    monkeypatch.setattr(module.op, "alter_column", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(module.op, "add_column", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(module.op, "create_index", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        module.op,
        "execute",
        lambda sql: executed_sql.append(str(sql)),
    )

    module.upgrade()

    normalized_sql = " ".join(" ".join(executed_sql).lower().split())
    assert "address_detail = left(address, 200)" not in normalized_sql
