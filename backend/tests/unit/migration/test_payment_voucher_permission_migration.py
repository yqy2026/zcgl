"""Tests for the independent payment-voucher download permission migration."""

from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType

import pytest


def _module_path() -> Path:
    return (
        Path(__file__).resolve().parents[3]
        / "alembic"
        / "versions"
        / "20260713_payment_voucher_download_permission.py"
    )


def _load_migration_module() -> ModuleType:
    spec = spec_from_file_location("payment_voucher_download_permission", _module_path())
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_voucher_permission_is_independent_from_ledger_read() -> None:
    module = _load_migration_module()
    source = _module_path().read_text(encoding="utf-8")

    assert module.down_revision == "20260713_payment_voucher_attachments"
    assert 'resource_type="ledger_voucher"' in source
    assert "permission:ledger_voucher:read" in source
    assert "permission:ledger:read" in source
    assert "system_admin" in source
    assert "ops_admin" in source
    assert "reviewer" in source
    assert "executive" in source
    assert "viewer" in source


def test_reviewer_static_permission_has_matching_audit_policy_rule() -> None:
    """The reviewer role is mapped to audit_viewer and needs both authz layers."""
    module = _load_migration_module()

    assert "audit_viewer" in module._POLICY_NAMES


def test_voucher_permission_migration_downgrade_fails_loud() -> None:
    module = _load_migration_module()

    with pytest.raises(RuntimeError, match="voucher download permission"):
        module.downgrade()
