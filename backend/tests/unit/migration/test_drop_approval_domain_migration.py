"""Tests for retiring the approval workflow domain."""

from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType


def _load_migration_module() -> ModuleType:
    module_path = (
        Path(__file__).resolve().parents[3]
        / "alembic"
        / "versions"
        / "20260611_drop_approval_domain.py"
    )
    spec = spec_from_file_location("drop_approval_domain", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _InspectorStub:
    def __init__(self, tables: set[str]) -> None:
        self._tables = tables

    def has_table(self, table_name: str) -> bool:
        return table_name in self._tables


class _BindStub:
    def __init__(self) -> None:
        self.statements: list[str] = []

    def execute(self, statement) -> None:
        self.statements.append(str(statement))


def test_migration_is_appended_to_current_alembic_head() -> None:
    module = _load_migration_module()

    assert module.revision == "20260611_drop_approval_domain"
    assert module.down_revision == "20260611_encrypt_party_contact_phone"


def test_upgrade_drops_approval_authz_data_before_domain_tables(monkeypatch) -> None:
    module = _load_migration_module()
    bind = _BindStub()
    inspector = _InspectorStub(
        {
            "abac_policy_rules",
            "resource_permissions",
            "permissions",
            "role_permissions",
            "permission_grants",
            "notifications",
            "approval_action_logs",
            "approval_task_snapshots",
            "approval_instances",
        }
    )
    dropped_tables: list[str] = []

    monkeypatch.setattr(module.op, "get_bind", lambda: bind)
    monkeypatch.setattr(module.sa, "inspect", lambda _bind: inspector)
    monkeypatch.setattr(
        module.op,
        "drop_table",
        lambda table_name: dropped_tables.append(table_name),
    )

    module.upgrade()

    assert dropped_tables == [
        "approval_action_logs",
        "approval_task_snapshots",
        "approval_instances",
    ]
    executed_sql = "\n".join(bind.statements)
    assert "resource_type = 'approval'" in executed_sql
    assert "resource = 'approval'" in executed_sql
    assert "type = 'approval_pending'" in executed_sql
    assert "related_entity_type = 'approval'" in executed_sql


def test_upgrade_skips_missing_approval_tables(monkeypatch) -> None:
    module = _load_migration_module()
    bind = _BindStub()
    inspector = _InspectorStub({"permissions"})
    dropped_tables: list[str] = []

    monkeypatch.setattr(module.op, "get_bind", lambda: bind)
    monkeypatch.setattr(module.sa, "inspect", lambda _bind: inspector)
    monkeypatch.setattr(
        module.op,
        "drop_table",
        lambda table_name: dropped_tables.append(table_name),
    )

    module.upgrade()

    assert dropped_tables == []
