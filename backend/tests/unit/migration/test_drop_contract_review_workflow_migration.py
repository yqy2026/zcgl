"""Tests for retiring contract review workflow database residue."""

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
        / "20260619_drop_contract_review_workflow.py"
    )
    spec = spec_from_file_location(
        "drop_contract_review_workflow_migration", module_path
    )
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeBind:
    def __init__(self) -> None:
        self.executed_sql: list[str] = []

    def execute(self, statement: Any) -> None:
        self.executed_sql.append(str(getattr(statement, "text", statement)))


class FakeInspector:
    def has_table(self, table_name: str) -> bool:
        return table_name in {"contracts", "contract_audit_logs"}

    def get_columns(self, table_name: str) -> list[dict[str, str]]:
        if table_name == "contracts":
            return [
                {"name": "status"},
                {"name": "review_status"},
                {"name": "review_by"},
                {"name": "reviewed_at"},
                {"name": "review_reason"},
            ]
        if table_name == "contract_audit_logs":
            return [
                {"name": "review_status_old"},
                {"name": "review_status_new"},
            ]
        return []


class FakeEnum:
    created_labels: list[tuple[str, ...]] = []
    dropped_names: list[str] = []

    def __init__(
        self,
        *labels: str,
        name: str,
        create_type: bool = True,
    ) -> None:
        self.labels = labels
        self.name = name
        self.create_type = create_type

    def create(self, _bind: FakeBind, checkfirst: bool = True) -> None:
        _ = checkfirst
        self.created_labels.append(self.labels)

    def drop(self, _bind: FakeBind, checkfirst: bool = True) -> None:
        _ = checkfirst
        self.dropped_names.append(self.name)


class FakeBatchAlter:
    def __init__(self) -> None:
        self.alter_calls: list[dict[str, Any]] = []

    def __enter__(self) -> FakeBatchAlter:
        return self

    def __exit__(self, *args: object) -> None:
        _ = args

    def alter_column(self, column_name: str, **kwargs: Any) -> None:
        self.alter_calls.append({"column_name": column_name, **kwargs})


def test_upgrade_converts_retired_lifecycle_values_and_rebuilds_status_enum(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_migration_module()
    bind = FakeBind()
    batch = FakeBatchAlter()
    dropped_columns: list[tuple[str, str]] = []
    altered_columns: list[tuple[str, str, dict[str, Any]]] = []
    FakeEnum.created_labels = []
    FakeEnum.dropped_names = []

    monkeypatch.setattr(module.op, "get_bind", lambda: bind)
    monkeypatch.setattr(module.sa, "inspect", lambda _bind: FakeInspector())
    monkeypatch.setattr(module.postgresql, "ENUM", FakeEnum)
    monkeypatch.setattr(module.op, "batch_alter_table", lambda _table_name: batch)
    monkeypatch.setattr(
        module.op,
        "alter_column",
        lambda table_name, column_name, **kwargs: altered_columns.append(
            (table_name, column_name, kwargs)
        ),
    )
    monkeypatch.setattr(
        module.op,
        "drop_column",
        lambda table_name, column_name: dropped_columns.append(
            (table_name, column_name)
        ),
    )

    module.upgrade()

    joined_sql = "\n".join(bind.executed_sql)
    assert "WHEN status = 'PENDING_REVIEW' THEN 'ACTIVE'" in joined_sql
    assert "WHEN status = 'EXPIRED' THEN 'ACTIVE'" in joined_sql
    assert FakeEnum.created_labels == [("DRAFT", "ACTIVE", "TERMINATED")]
    assert FakeEnum.dropped_names == ["contractlifecyclestatus"]
    assert [column_name for _table, column_name, _kwargs in altered_columns] == [
        "status",
        "status",
    ]
    assert batch.alter_calls[0]["column_name"] == "status"
    assert {column_name for _table, column_name in dropped_columns} == {
        "review_status",
        "review_by",
        "reviewed_at",
        "review_reason",
        "review_status_old",
        "review_status_new",
    }
    assert "DROP TYPE IF EXISTS contractreviewstatus" in joined_sql


def test_downgrade_is_fail_loud() -> None:
    module = _load_migration_module()

    with pytest.raises(RuntimeError, match="contract review workflow was retired"):
        module.downgrade()
