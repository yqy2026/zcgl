"""Regression tests for the derived asset manager nullable migration."""

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
        / "20260714_asset_manager_party_nullable.py"
    )
    spec = spec_from_file_location("asset_manager_party_nullable", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_follows_payment_voucher_download_permission_head() -> None:
    module = _load_migration_module()

    assert module.down_revision == "20260713_payment_voucher_download_permission"


def test_migration_allows_unprojected_assets_without_a_manager_party(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_migration_module()
    alter_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
    monkeypatch.setattr(
        module.op,
        "alter_column",
        lambda *args, **kwargs: alter_calls.append((args, kwargs)),
    )

    module.upgrade()

    assert len(alter_calls) == 1
    args, kwargs = alter_calls[0]
    assert args == ("assets", "manager_party_id")
    assert isinstance(kwargs["existing_type"], module.sa.String)
    assert kwargs["nullable"] is True


def test_migration_downgrade_fails_loud_after_nulls_are_allowed() -> None:
    module = _load_migration_module()

    with pytest.raises(RuntimeError, match="cannot restore"):
        module.downgrade()
