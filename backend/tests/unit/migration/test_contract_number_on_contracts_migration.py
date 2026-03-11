"""Tests for 20260307 contract_number migration on contracts."""

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
        / "20260307_m2_contract_number_on_contracts.py"
    )
    spec = spec_from_file_location("contract_number_on_contracts_migration", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_upgrade_should_backfill_before_enforcing_not_null(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_migration_module()
    add_column_calls: list[dict[str, Any]] = []
    alter_column_calls: list[dict[str, Any]] = []
    create_index_calls: list[dict[str, Any]] = []
    execute_calls: list[str] = []

    class FakeInspector:
        def has_table(self, table_name: str) -> bool:
            return table_name == "contracts"

        def get_columns(self, table_name: str):  # type: ignore[no-untyped-def]
            if table_name != "contracts":
                return []
            return []

    monkeypatch.setattr(
        module.op,
        "add_column",
        lambda table_name, column: add_column_calls.append(
            {"table_name": table_name, "column": column}
        ),
    )
    monkeypatch.setattr(
        module.op,
        "execute",
        lambda statement: execute_calls.append(str(getattr(statement, "text", statement))),
    )
    monkeypatch.setattr(
        module.op,
        "alter_column",
        lambda table_name, column_name, **kwargs: alter_column_calls.append(
            {
                "table_name": table_name,
                "column_name": column_name,
                **kwargs,
            }
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
    monkeypatch.setattr(module.op, "get_bind", lambda: object())
    monkeypatch.setattr(module.sa, "inspect", lambda _bind: FakeInspector())

    module.upgrade()

    assert add_column_calls[0]["table_name"] == "contracts"
    assert add_column_calls[0]["column"].name == "contract_number"
    assert add_column_calls[0]["column"].nullable is True
    assert any("UPDATE contracts" in sql for sql in execute_calls)
    assert any("AUTO-" in sql for sql in execute_calls)
    assert len(alter_column_calls) == 1
    assert alter_column_calls[0]["table_name"] == "contracts"
    assert alter_column_calls[0]["column_name"] == "contract_number"
    assert isinstance(alter_column_calls[0]["existing_type"], module.sa.String)
    assert alter_column_calls[0]["existing_type"].length == 100
    assert alter_column_calls[0]["nullable"] is False
    assert create_index_calls == [
        {
            "index_name": "ix_contracts_contract_number",
            "table_name": "contracts",
            "columns": ["contract_number"],
            "unique": True,
        }
    ]
