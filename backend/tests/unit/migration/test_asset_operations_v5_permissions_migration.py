"""Regression tests for asset-operations capability permission seeding."""

from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from inspect import getsource
from pathlib import Path
from types import ModuleType


def _load_migration() -> ModuleType:
    path = (
        Path(__file__).resolve().parents[3]
        / "alembic"
        / "versions"
        / "20261024_asset_operations_v5_permissions.py"
    )
    spec = spec_from_file_location("asset_operations_v5_permissions", path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_asset_operations_permissions_follow_contract_schema_head() -> None:
    module = _load_migration()

    assert module.down_revision == "20261023_asset_operations_v5_contracts"
    assert {item[0] for item in module.PERMISSIONS} == {
        "read",
        "write",
        "report",
        "archive",
        "import",
    }
    assert module.BUILTIN_ROLE_NAMES == ("ops_admin", "system_admin")


def test_asset_operations_permission_downgrade_removes_only_owned_ids() -> None:
    module = _load_migration()
    source = getsource(module.downgrade)

    for action in ("read", "write", "report", "archive", "import"):
        assert f"permission:asset_ops:{action}" in source
    assert "WHERE resource = 'asset_ops'" not in source
