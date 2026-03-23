"""Tests for 20260306 contract ledger entries migration."""

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
        / "20260306_m2_contract_ledger_entries.py"
    )
    spec = spec_from_file_location("contract_ledger_entries_migration", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_should_follow_lifecycle_core_head() -> None:
    module = _load_migration_module()

    assert module.down_revision == "20260306_m2_contract_lifecycle_core"


def test_upgrade_should_create_contract_ledger_entries_table(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_migration_module()
    create_table_calls: list[dict[str, Any]] = []
    create_index_calls: list[dict[str, Any]] = []

    monkeypatch.setattr(
        module.op,
        "create_table",
        lambda table_name, *columns, **_kwargs: create_table_calls.append(
            {"table_name": table_name, "columns": columns}
        ),
    )
    monkeypatch.setattr(
        module.op,
        "create_index",
        lambda index_name, table_name, columns, **_kwargs: create_index_calls.append(
            {
                "index_name": index_name,
                "table_name": table_name,
                "columns": columns,
            }
        ),
    )

    module.upgrade()

    ledger_call = next(
        call for call in create_table_calls if call["table_name"] == "contract_ledger_entries"
    )
    column_names = [
        column.name
        for column in ledger_call["columns"]
        if hasattr(column, "name")
    ]

    assert "entry_id" in column_names
    assert "contract_id" in column_names
    assert "year_month" in column_names
    assert "due_date" in column_names
    assert "amount_due" in column_names
    assert "currency_code" in column_names
    assert "is_tax_included" in column_names
    assert "tax_rate" in column_names
    assert "payment_status" in column_names
    assert "paid_amount" in column_names
    assert "notes" in column_names
    assert "created_at" in column_names
    assert "updated_at" in column_names

    assert {
        "index_name": "ix_contract_ledger_entries_contract_id",
        "table_name": "contract_ledger_entries",
        "columns": ["contract_id"],
    } in create_index_calls
