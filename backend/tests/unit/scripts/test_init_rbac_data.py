"""Tests for RBAC seed script role definitions."""

from __future__ import annotations

import re
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType, SimpleNamespace


def _load_module() -> ModuleType:
    module_path = (
        Path(__file__).resolve().parents[3]
        / "scripts"
        / "setup"
        / "init_rbac_data.py"
    )
    spec = spec_from_file_location("init_rbac_data", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _discover_api_authz_pairs() -> set[tuple[str, str]]:
    api_root = Path(__file__).resolve().parents[3] / "src" / "api" / "v1"
    pattern = re.compile(
        r'require_authz\([\s\S]*?action\s*=\s*["\']([^"\']+)["\'][\s\S]*?resource_type\s*=\s*["\']([^"\']+)["\']'
    )
    pairs: set[tuple[str, str]] = set()
    for py_file in api_root.rglob("*.py"):
        source = py_file.read_text(encoding="utf-8")
        for match in pattern.finditer(source):
            action, resource = match.group(1), match.group(2)
            pairs.add((resource, action))
    return pairs


def test_target_system_roles_should_match_six_role_model() -> None:
    module = _load_module()
    role_names = [item[0] for item in module.TARGET_SYSTEM_ROLE_DEFINITIONS]

    assert role_names == [
        "system_admin",
        "ops_admin",
        "perm_admin",
        "reviewer",
        "executive",
        "viewer",
    ]


def test_role_permission_matrix_should_cover_all_target_roles() -> None:
    module = _load_module()
    role_names = {item[0] for item in module.TARGET_SYSTEM_ROLE_DEFINITIONS}

    assert set(module.ROLE_PERMISSION_MATRIX.keys()) == role_names


def test_legacy_roles_should_not_appear_in_target_definitions() -> None:
    module = _load_module()
    target_names = {item[0] for item in module.TARGET_SYSTEM_ROLE_DEFINITIONS}

    assert module.LEGACY_SYSTEM_ROLE_NAMES.isdisjoint(target_names)


def test_test_user_assignments_should_use_new_role_names() -> None:
    module = _load_module()
    assigned_role_names = {role_name for _, role_name in module.TEST_USER_ROLE_ASSIGNMENTS}

    assert assigned_role_names == {"ops_admin", "executive", "viewer"}


def test_role_permission_matrix_should_keep_perm_admin_off_business_resources() -> None:
    module = _load_module()
    permissions = [
        SimpleNamespace(resource="asset", action="read"),
        SimpleNamespace(resource="user", action="read"),
        SimpleNamespace(resource="role", action="update"),
        SimpleNamespace(resource="permission_grant", action="assign"),
        SimpleNamespace(resource="analytics", action="read"),
    ]

    resolved = module.ROLE_PERMISSION_MATRIX["perm_admin"](permissions)
    resolved_pairs = {(item.resource, item.action) for item in resolved}

    assert ("user", "read") in resolved_pairs
    assert ("role", "update") in resolved_pairs
    assert ("permission_grant", "assign") in resolved_pairs
    assert ("asset", "read") not in resolved_pairs
    assert ("analytics", "read") not in resolved_pairs


def test_permission_seed_should_use_analytics_not_statistics() -> None:
    module = _load_module()
    flattened = repr(module.BASIC_PERMISSIONS_DATA)

    assert "('analytics', 'read'" in flattened
    assert "('analytics', 'export'" in flattened
    assert "('statistics', 'read'" not in flattened


def test_permission_seed_should_use_contract_resources_and_crud_actions() -> None:
    module = _load_module()
    flattened = repr(module.BASIC_PERMISSIONS_DATA)

    assert "('contract', 'read'" in flattened
    assert "('contract', 'create'" in flattened
    assert "('contract_group', 'read'" in flattened
    assert "('excel_config', 'write'" not in flattened


def test_permission_seed_should_cover_current_api_authz_pairs() -> None:
    module = _load_module()
    seed_pairs = {(resource, action) for resource, action, *_ in module.BASIC_PERMISSIONS_DATA}
    api_pairs = _discover_api_authz_pairs()

    missing_pairs = sorted(api_pairs - seed_pairs)
    assert missing_pairs == []
