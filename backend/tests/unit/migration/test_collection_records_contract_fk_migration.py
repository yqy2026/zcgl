"""Tests for 20260307 collection_records contract FK migration."""

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
        / "20260307_m2_collection_records_contract_fk.py"
    )
    spec = spec_from_file_location("collection_records_contract_fk_migration", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_upgrade_should_validate_backfilled_rows_before_creating_fks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_migration_module()
    call_order: list[str] = []

    monkeypatch.setattr(
        module,
        "_drop_fk_if_points_to",
        lambda *_args, **_kwargs: call_order.append("drop"),
    )
    monkeypatch.setattr(
        module,
        "_rewrite_legacy_collection_references",
        lambda: call_order.append("rewrite"),
    )
    monkeypatch.setattr(
        module,
        "_assert_backfilled_references_exist",
        lambda: call_order.append("validate"),
    )
    monkeypatch.setattr(
        module.op,
        "create_foreign_key",
        lambda *_args, **_kwargs: call_order.append("create_fk"),
    )

    module.upgrade()

    assert "validate" in call_order
    assert "rewrite" in call_order
    assert call_order.index("validate") < call_order.index("create_fk")
