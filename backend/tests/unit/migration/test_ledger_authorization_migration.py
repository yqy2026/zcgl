"""Tests for the upgrade-safe ledger authorization backfill."""

from importlib.util import module_from_spec, spec_from_file_location
from inspect import getsource
from pathlib import Path
from types import ModuleType


def _load_migration(filename: str) -> ModuleType:
    module_path = (
        Path(__file__).resolve().parents[3] / "alembic" / "versions" / filename
    )
    spec = spec_from_file_location(filename.removesuffix(".py"), module_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_ledger_authorization_should_be_a_new_head_migration() -> None:
    module = _load_migration("20260710_backfill_ledger_authorization.py")

    assert module.down_revision == "20260706_operations_ledger_foundation"
    assert {item[1] for item in module._PERMISSIONS} == {"create", "update"}
    assert {
        policy_name for policy_name, _actions, _condition in module._POLICY_RULES
    } == {
        "platform_admin",
        "asset_owner_operator",
        "asset_manager_operator",
        "dual_party_viewer",
        "project_manager_operator",
        "audit_viewer",
        "no_data_access",
    }
    assert all(
        condition == module._ALLOW_ALL
        for _policy_name, _actions, condition in module._POLICY_RULES
    )
    assert module._rule_id("platform_admin", "create").startswith("backfill_20260710_")


def test_ledger_authorization_downgrade_should_only_remove_owned_ids() -> None:
    module = _load_migration("20260710_backfill_ledger_authorization.py")
    source = getsource(module.downgrade)

    assert "permission:ledger:create" in source
    assert "permission:ledger:update" in source
    assert "WHERE resource = 'ledger'" not in source


def test_historical_policy_backfill_should_remain_immutable() -> None:
    historical = _load_migration("20260221_backfill_expanded_policy_package_rules.py")

    assert "ledger" not in historical._EXPANDED_RESOURCE_TYPES
