"""Tests for Party review_status reversed -> rejected migration."""

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
        / "20260620_party_rejected_review_status.py"
    )
    spec = spec_from_file_location(
        "party_rejected_review_status_migration", module_path
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
        return table_name == "parties"

    def get_columns(self, table_name: str) -> list[dict[str, str]]:
        if table_name == "parties":
            return [{"name": "id"}, {"name": "review_status"}]
        return []


def test_migration_should_follow_contract_snapshot_head() -> None:
    module = _load_migration_module()

    assert module.down_revision == "20260620_contract_party_name_snapshots"


def test_upgrade_should_rename_reversed_to_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_migration_module()
    bind = FakeBind()
    monkeypatch.setattr(module.op, "get_bind", lambda: bind)
    monkeypatch.setattr(module.sa, "inspect", lambda _bind: FakeInspector())

    module.upgrade()

    joined_sql = "\n".join(bind.executed_sql)
    assert "SET review_status = 'rejected'" in joined_sql
    assert "WHERE review_status = 'reversed'" in joined_sql


def test_downgrade_is_fail_loud() -> None:
    module = _load_migration_module()

    with pytest.raises(RuntimeError, match="not downgraded"):
        module.downgrade()
