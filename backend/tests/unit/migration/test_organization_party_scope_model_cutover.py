"""Regression tests for the irreversible ADR-0022 model cutover."""

from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest


def _load_migration_module() -> ModuleType:
    module_path = (
        Path(__file__).resolve().parents[3]
        / "alembic"
        / "versions"
        / "20260804_organization_party_scope_model_cutover.py"
    )
    spec = spec_from_file_location(
        "organization_party_scope_model_cutover_migration", module_path
    )
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _FakeResult:
    def __init__(self, value: int = 0) -> None:
        self._value = value

    def scalar_one(self) -> int:
        return self._value


class _FakeBind:
    def __init__(self, violations: dict[str, int] | None = None) -> None:
        self.violations = violations or {}
        self.executed_sql: list[str] = []

    def execute(self, statement: Any) -> _FakeResult:
        sql = str(getattr(statement, "text", statement))
        self.executed_sql.append(sql)
        for gate_name, count in self.violations.items():
            if f"gate:{gate_name}" in sql:
                return _FakeResult(count)
        return _FakeResult()


def _disable_schema_operations(
    module: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    for operation_name in (
        "add_column",
        "alter_column",
        "create_check_constraint",
        "create_foreign_key",
        "create_index",
        "create_unique_constraint",
        "drop_column",
        "drop_constraint",
        "drop_index",
        "drop_table",
    ):
        monkeypatch.setattr(module.op, operation_name, lambda *args, **kwargs: None)


def test_migration_follows_the_current_head() -> None:
    module = _load_migration_module()

    assert module.revision == "20260804_organization_party_scope_model_cutover"
    assert module.down_revision == "20260722_drop_legacy_document_and_prompt_schema"


@pytest.mark.parametrize(
    ("gate_name", "message"),
    [
        ("legacy_organization_parties", "organization Party"),
        ("party_hierarchy_rows", "PartyHierarchy"),
        ("headquarters_bindings", "headquarters"),
        ("users_without_organization", "organization"),
        ("invalid_user_organization_chain", "organization chain"),
        ("invalid_party_codes", "Party code"),
        ("duplicate_organization_codes", "Organization code"),
        ("invalid_metadata_shape", "metadata must be a JSON object"),
        ("invalid_metadata_identifiers", "metadata identifier"),
    ],
)
def test_upgrade_fails_before_ddl_when_source_data_is_unresolved(
    monkeypatch: pytest.MonkeyPatch,
    gate_name: str,
    message: str,
) -> None:
    module = _load_migration_module()
    bind = _FakeBind({gate_name: 1})
    ddl_started = False

    monkeypatch.setattr(module.op, "get_bind", lambda: bind)

    def mark_ddl_started(*args: object, **kwargs: object) -> None:
        nonlocal ddl_started
        ddl_started = True

    monkeypatch.setattr(module.op, "add_column", mark_ddl_started)

    with pytest.raises(RuntimeError, match=message):
        module.upgrade()

    assert ddl_started is False


def test_upgrade_lifts_supported_metadata_identifiers_and_removes_legacy_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_migration_module()
    bind = _FakeBind()
    monkeypatch.setattr(module.op, "get_bind", lambda: bind)
    _disable_schema_operations(module, monkeypatch)

    module.upgrade()

    sql = "\n".join(bind.executed_sql)
    normalized_sql = " ".join(sql.split())
    assert "metadata ->> 'identifier_type'" in sql
    assert "metadata ->> 'identifier_value'" in sql
    assert "regexp_replace" in sql
    assert "identifier_type IS NULL" in sql
    assert "normalized_value IS NULL" in sql
    assert (
        "metadata - 'identifier_type' - 'identifier_value' - 'unified_identifier'"
        in normalized_sql
    )


def test_upgrade_performs_the_irreversible_schema_cutover(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_migration_module()
    bind = _FakeBind()
    added_columns: list[tuple[str, str]] = []
    altered_columns: list[tuple[str, str, dict[str, object]]] = []
    created_checks: list[tuple[str, str]] = []
    dropped_columns: list[tuple[str, str]] = []
    dropped_indexes: list[tuple[str, str | None]] = []
    dropped_tables: list[str] = []

    monkeypatch.setattr(module.op, "get_bind", lambda: bind)
    monkeypatch.setattr(
        module.op,
        "add_column",
        lambda table, column: added_columns.append((table, column.name)),
    )
    monkeypatch.setattr(
        module.op,
        "alter_column",
        lambda table, column, **kwargs: altered_columns.append((table, column, kwargs)),
    )
    monkeypatch.setattr(
        module.op,
        "create_check_constraint",
        lambda name, table, condition: created_checks.append((name, table)),
    )
    monkeypatch.setattr(
        module.op,
        "drop_column",
        lambda table, column: dropped_columns.append((table, column)),
    )
    monkeypatch.setattr(
        module.op,
        "drop_index",
        lambda name, table_name=None: dropped_indexes.append((name, table_name)),
    )
    monkeypatch.setattr(module.op, "drop_table", dropped_tables.append)
    for operation_name in (
        "create_foreign_key",
        "create_index",
        "create_unique_constraint",
        "drop_constraint",
    ):
        monkeypatch.setattr(module.op, operation_name, lambda *args, **kwargs: None)

    module.upgrade()

    assert set(added_columns) >= {
        ("parties", "identifier_type"),
        ("parties", "identifier_value"),
        ("parties", "identifier_fingerprint"),
        ("organizations", "represented_party_id"),
        ("organizations", "represented_party_perspective"),
        ("users", "account_type"),
    }
    assert any(
        table == "users"
        and column == "default_organization_id"
        and options.get("new_column_name") == "organization_id"
        for table, column, options in altered_columns
    )
    assert ("user_party_bindings", "is_primary") in dropped_columns
    assert (
        "uq_user_party_bindings_primary_per_relation",
        "user_party_bindings",
    ) in dropped_indexes
    assert "party_hierarchy" in dropped_tables
    assert set(created_checks) >= {
        ("ck_parties_party_type", "parties"),
        ("ck_parties_metadata_object", "parties"),
        ("ck_organizations_represented_party_pair", "organizations"),
        ("ck_users_account_organization", "users"),
        ("ck_user_party_bindings_relation_type", "user_party_bindings"),
    }


def test_downgrade_fails_loud() -> None:
    module = _load_migration_module()

    with pytest.raises(RuntimeError, match="irreversible"):
        module.downgrade()
