"""Tests for business_model -> revenue_mode migration safety."""

from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType
from unittest.mock import Mock

import pytest


def _load_migration_module() -> ModuleType:
    module_path = (
        Path(__file__).resolve().parents[3]
        / "alembic"
        / "versions"
        / "20260304_rename_asset_business_model_to_revenue_mode.py"
    )
    spec = spec_from_file_location("rename_asset_business_model", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_with_columns(
    module: ModuleType,
    *,
    columns: list[str],
    operation: str,
) -> Mock:
    inspector = Mock()
    inspector.has_table.return_value = True
    inspector.get_columns.return_value = [{"name": name} for name in columns]

    alter_column_mock = Mock()
    module.inspect = Mock(return_value=inspector)
    module.op.get_bind = Mock(return_value=object())
    module.op.alter_column = alter_column_mock

    if operation == "upgrade":
        module.upgrade()
    else:
        module.downgrade()

    return alter_column_mock


def test_migration_should_follow_current_head() -> None:
    module = _load_migration_module()

    assert module.down_revision == "20260224_backfill_ownership_occupancy_policy_rules"


def test_upgrade_should_rename_business_model_to_revenue_mode() -> None:
    module = _load_migration_module()

    alter_column_mock = _run_with_columns(
        module,
        columns=["id", "business_model"],
        operation="upgrade",
    )

    alter_column_mock.assert_called_once_with(
        "assets",
        "business_model",
        new_column_name="revenue_mode",
    )


def test_upgrade_should_fail_when_both_columns_exist() -> None:
    module = _load_migration_module()

    with pytest.raises(RuntimeError, match="Expected exactly one"):
        _run_with_columns(
            module,
            columns=["id", "business_model", "revenue_mode"],
            operation="upgrade",
        )


def test_upgrade_should_noop_when_revenue_mode_already_exists() -> None:
    module = _load_migration_module()

    alter_column_mock = _run_with_columns(
        module,
        columns=["id", "revenue_mode"],
        operation="upgrade",
    )

    alter_column_mock.assert_not_called()


def test_downgrade_should_rename_revenue_mode_back_to_business_model() -> None:
    module = _load_migration_module()

    alter_column_mock = _run_with_columns(
        module,
        columns=["id", "revenue_mode"],
        operation="downgrade",
    )

    alter_column_mock.assert_called_once_with(
        "assets",
        "revenue_mode",
        new_column_name="business_model",
    )


def test_downgrade_should_fail_when_both_columns_exist() -> None:
    module = _load_migration_module()

    with pytest.raises(RuntimeError, match="Expected exactly one"):
        _run_with_columns(
            module,
            columns=["id", "business_model", "revenue_mode"],
            operation="downgrade",
        )
