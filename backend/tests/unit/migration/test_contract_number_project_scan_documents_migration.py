"""Tests for contract-number per-project and scan-document migration."""

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
        / "20260620_contract_number_project_scan_documents.py"
    )
    spec = spec_from_file_location(
        "contract_number_project_scan_documents_migration",
        module_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeResult:
    def __init__(self, first_value: Any = None) -> None:
        self._first_value = first_value

    def first(self) -> Any:
        return self._first_value


class FakeBind:
    def __init__(self, conflict: Any = None, missing_project: Any = None) -> None:
        self.conflict = conflict
        self.missing_project = missing_project
        self.executed_sql: list[str] = []

    def execute(self, statement: Any) -> FakeResult:
        sql = str(getattr(statement, "text", statement))
        self.executed_sql.append(sql)
        if "SELECT contract_id, contract_number" in sql:
            return FakeResult(self.missing_project)
        if "HAVING COUNT(*) > 1" in sql:
            return FakeResult(self.conflict)
        return FakeResult()


class FakeInspector:
    def has_table(self, table_name: str) -> bool:
        return table_name in {"contracts", "contract_groups", "projects"}

    def get_columns(self, table_name: str) -> list[dict[str, str]]:
        if table_name == "contracts":
            return [
                {"name": "contract_id"},
                {"name": "contract_number"},
                {"name": "contract_group_id"},
                {"name": "data_status"},
            ]
        return []

    def get_indexes(self, table_name: str) -> list[dict[str, str]]:
        if table_name == "contracts":
            return [{"name": "ix_contracts_contract_number"}]
        return []

    def get_unique_constraints(self, table_name: str) -> list[dict[str, str]]:
        return []

    def get_check_constraints(self, table_name: str) -> list[dict[str, str]]:
        return []


def test_migration_is_appended_to_current_alembic_head() -> None:
    module = _load_migration_module()

    assert module.down_revision == "20260619_drop_contract_review_workflow"


def test_upgrade_adds_project_unique_and_scan_document_tables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_migration_module()
    bind = FakeBind()
    add_column_calls: list[dict[str, Any]] = []
    create_index_calls: list[dict[str, Any]] = []
    drop_index_calls: list[dict[str, Any]] = []
    create_unique_calls: list[dict[str, Any]] = []
    create_check_calls: list[dict[str, Any]] = []
    create_table_calls: list[dict[str, Any]] = []

    monkeypatch.setattr(module.op, "get_bind", lambda: bind)
    monkeypatch.setattr(module.sa, "inspect", lambda _bind: FakeInspector())
    monkeypatch.setattr(
        module.op,
        "add_column",
        lambda table_name, column: add_column_calls.append(
            {"table_name": table_name, "column": column}
        ),
    )
    monkeypatch.setattr(
        module.op,
        "create_index",
        lambda index_name, table_name, columns, **kwargs: create_index_calls.append(
            {
                "index_name": index_name,
                "table_name": table_name,
                "columns": columns,
                **kwargs,
            }
        ),
    )
    monkeypatch.setattr(
        module.op,
        "drop_index",
        lambda index_name, **kwargs: drop_index_calls.append(
            {"index_name": index_name, **kwargs}
        ),
    )
    monkeypatch.setattr(
        module.op,
        "create_unique_constraint",
        lambda constraint_name, table_name, columns: create_unique_calls.append(
            {
                "constraint_name": constraint_name,
                "table_name": table_name,
                "columns": columns,
            }
        ),
    )
    monkeypatch.setattr(
        module.op,
        "create_check_constraint",
        lambda constraint_name, table_name, condition: create_check_calls.append(
            {
                "constraint_name": constraint_name,
                "table_name": table_name,
                "condition": condition,
            }
        ),
    )
    monkeypatch.setattr(
        module.op,
        "create_table",
        lambda table_name, *columns, **kwargs: create_table_calls.append(
            {"table_name": table_name, "columns": columns, **kwargs}
        ),
    )

    module.upgrade()

    assert add_column_calls[0]["table_name"] == "contracts"
    assert add_column_calls[0]["column"].name == "project_id"
    assert any("UPDATE contracts AS c" in sql for sql in bind.executed_sql)
    assert drop_index_calls == [
        {
            "index_name": "ix_contracts_contract_number",
            "table_name": "contracts",
        }
    ]
    assert create_unique_calls == [
        {
            "constraint_name": "uq_contract_number_project",
            "table_name": "contracts",
            "columns": ["contract_number", "project_id"],
        }
    ]
    assert create_check_calls == [
        {
            "constraint_name": "ck_contracts_active_project_id_required",
            "table_name": "contracts",
            "condition": "data_status <> '正常' OR project_id IS NOT NULL",
        }
    ]
    assert {call["table_name"] for call in create_table_calls} == {
        "contract_scan_documents",
        "contract_scan_document_links",
    }
    assert {call["index_name"] for call in create_index_calls} >= {
        "ix_contracts_project_id",
        "ix_contract_scan_documents_storage_key",
        "ix_contract_scan_documents_checksum_sha256",
    }


def test_upgrade_fails_loud_on_project_contract_number_conflict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_migration_module()
    bind = FakeBind(conflict=("HT-001", "project-1", 2))
    monkeypatch.setattr(module.op, "get_bind", lambda: bind)

    with pytest.raises(RuntimeError, match="Duplicate contract_number within project"):
        module._assert_no_project_contract_number_conflicts()

    conflict_sql = bind.executed_sql[-1]
    assert "project_id IS NOT NULL" in conflict_sql
    assert "data_status = '正常'" not in conflict_sql


def test_upgrade_fails_loud_when_active_contract_still_lacks_project(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_migration_module()
    bind = FakeBind(missing_project=("contract-1", "HT-001"))
    monkeypatch.setattr(module.op, "get_bind", lambda: bind)

    with pytest.raises(RuntimeError, match="Active contract without project_id"):
        module._assert_no_active_contract_missing_project_id()

    missing_project_sql = bind.executed_sql[-1]
    assert "data_status = '正常'" in missing_project_sql
    assert "project_id IS NULL" in missing_project_sql
