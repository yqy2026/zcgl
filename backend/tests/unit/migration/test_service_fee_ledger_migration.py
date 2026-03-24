"""Tests for service fee ledger migration."""

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
        / "20260324_req_rnt_006_service_fee_ledger_m3.py"
    )
    spec = spec_from_file_location("service_fee_ledger_migration", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_should_follow_current_head() -> None:
    module = _load_migration_module()

    assert module.down_revision == "20260312_party_soft_delete_review_log"


def test_upgrade_should_create_service_fee_ledgers_table(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_migration_module()
    create_table_calls: list[dict[str, Any]] = []
    create_index_calls: list[dict[str, Any]] = []

    class _Inspector:
        @staticmethod
        def has_table(table_name: str) -> bool:
            return False

        @staticmethod
        def get_indexes(table_name: str) -> list[dict[str, Any]]:
            return []

    monkeypatch.setattr(module.op, "get_bind", lambda: object())
    monkeypatch.setattr(module.sa, "inspect", lambda _bind: _Inspector())

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
        call for call in create_table_calls if call["table_name"] == "service_fee_ledgers"
    )
    column_names = [
        column.name
        for column in ledger_call["columns"]
        if hasattr(column, "name")
    ]

    assert "service_fee_entry_id" in column_names
    assert "contract_group_id" in column_names
    assert "agency_contract_id" in column_names
    assert "source_ledger_id" in column_names
    assert "year_month" in column_names
    assert "amount_due" in column_names
    assert "paid_amount" in column_names
    assert "payment_status" in column_names
    assert "currency_code" in column_names
    assert "service_fee_ratio" in column_names
    assert "created_at" in column_names
    assert "updated_at" in column_names

    assert {
        "index_name": "ix_service_fee_ledgers_contract_group_id",
        "table_name": "service_fee_ledgers",
        "columns": ["contract_group_id"],
    } in create_index_calls


def test_upgrade_should_skip_create_when_service_fee_ledgers_already_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_migration_module()
    create_table_calls: list[str] = []
    create_index_calls: list[dict[str, Any]] = []

    class _Inspector:
        @staticmethod
        def has_table(table_name: str) -> bool:
            return table_name == "service_fee_ledgers"

        @staticmethod
        def get_indexes(table_name: str) -> list[dict[str, Any]]:
            assert table_name == "service_fee_ledgers"
            return []

    monkeypatch.setattr(module.op, "get_bind", lambda: object())
    monkeypatch.setattr(module.sa, "inspect", lambda _bind: _Inspector())
    monkeypatch.setattr(
        module.op,
        "create_table",
        lambda table_name, *columns, **_kwargs: create_table_calls.append(table_name),
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

    assert create_table_calls == []
    assert {
        "index_name": "ix_service_fee_ledgers_contract_group_id",
        "table_name": "service_fee_ledgers",
        "columns": ["contract_group_id"],
    } in create_index_calls
