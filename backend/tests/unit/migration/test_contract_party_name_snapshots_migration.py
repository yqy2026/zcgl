"""Tests for contract party-name snapshot migration."""

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
        / "20260620_contract_party_name_snapshots.py"
    )
    spec = spec_from_file_location(
        "contract_party_name_snapshots_migration", module_path
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
    def __init__(self) -> None:
        self._contract_columns = {
            "contract_id",
            "lessor_party_id",
            "lessee_party_id",
        }

    def has_table(self, table_name: str) -> bool:
        return table_name in {"contracts", "parties", "lease_contract_details"}

    def get_columns(self, table_name: str) -> list[dict[str, str]]:
        if table_name == "contracts":
            columns = set(self._contract_columns)
            columns.update({"lessor_name_snapshot", "lessee_name_snapshot"})
            return [{"name": column} for column in sorted(columns)]
        if table_name == "lease_contract_details":
            return [{"name": "contract_id"}, {"name": "tenant_name"}]
        return [{"name": "id"}, {"name": "name"}]


def test_migration_should_follow_ledger_status_derivation_head() -> None:
    module = _load_migration_module()

    assert module.down_revision == "20260620_derive_ledger_payment_status"


def test_upgrade_should_add_snapshot_columns_and_backfill_names(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_migration_module()
    bind = FakeBind()
    add_column_calls: list[dict[str, Any]] = []

    class FirstInspector(FakeInspector):
        def get_columns(self, table_name: str) -> list[dict[str, str]]:
            if table_name == "contracts":
                return [
                    {"name": "contract_id"},
                    {"name": "lessor_party_id"},
                    {"name": "lessee_party_id"},
                ]
            return super().get_columns(table_name)

    inspectors = [FirstInspector(), FakeInspector()]

    monkeypatch.setattr(module.op, "get_bind", lambda: bind)
    monkeypatch.setattr(module.sa, "inspect", lambda _bind: inspectors.pop(0))
    monkeypatch.setattr(
        module.op,
        "add_column",
        lambda table_name, column: add_column_calls.append(
            {"table_name": table_name, "column": column}
        ),
    )

    module.upgrade()

    assert [call["column"].name for call in add_column_calls] == [
        "lessor_name_snapshot",
        "lessee_name_snapshot",
    ]
    joined_sql = "\n".join(bind.executed_sql)
    assert "SET lessor_name_snapshot = p.name" in joined_sql
    assert "SET lessee_name_snapshot = p.name" in joined_sql
    assert "SET tenant_name = c.lessee_name_snapshot" in joined_sql


def test_downgrade_is_fail_loud() -> None:
    module = _load_migration_module()

    with pytest.raises(RuntimeError, match="not downgraded"):
        module.downgrade()
