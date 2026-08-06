"""Regression tests for the Organization Party scope receipt migration."""

from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType
from typing import Any


def _load_migration_module() -> ModuleType:
    module_path = (
        Path(__file__).resolve().parents[3]
        / "alembic"
        / "versions"
        / "20260804_organization_party_scope_commit_receipts.py"
    )
    spec = spec_from_file_location("organization_party_scope_receipts_migration", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Result:
    def __init__(self, rows: list[tuple[Any, ...]] | None = None) -> None:
        self.rows = rows or []

    def first(self) -> tuple[Any, ...] | None:
        return self.rows[0] if self.rows else None

    def fetchall(self) -> list[tuple[Any, ...]]:
        return self.rows


class _Bind:
    def __init__(self) -> None:
        self.statements: list[str] = []
        self.parameters: list[dict[str, Any] | None] = []

    def execute(self, statement: Any, params: dict[str, Any] | None = None) -> _Result:
        sql = str(getattr(statement, "text", statement))
        self.statements.append(sql)
        self.parameters.append(params)
        if "SELECT id FROM permissions" in sql:
            return _Result()
        if "SELECT id FROM roles" in sql:
            return _Result([("role-system",), ("role-perm",)])
        return _Result()


def test_migration_follows_party_scope_cutover() -> None:
    module = _load_migration_module()

    assert module.revision == "20260804_organization_party_scope_commit_receipts"
    assert module.down_revision == "20260804_organization_party_scope_model_cutover"


def test_upgrade_creates_receipt_table_and_seeds_dedicated_permission(monkeypatch) -> None:
    module = _load_migration_module()
    bind = _Bind()
    created_tables: list[str] = []
    created_indexes: list[str] = []

    monkeypatch.setattr(module.op, "create_table", lambda name, *args: created_tables.append(name))
    monkeypatch.setattr(
        module.op,
        "create_index",
        lambda name, table_name, columns: created_indexes.append(name),
    )
    monkeypatch.setattr(module.op, "get_bind", lambda: bind)

    module.upgrade()

    assert created_tables == ["organization_party_scope_commits"]
    assert created_indexes == [
        "ix_organization_party_scope_commits_organization_id"
    ]
    assert any(
        params is not None
        and params.get("name") == "organization:manage_party_scope"
        for params in bind.parameters
    )
