"""Tests for operations ledger foundation migration."""

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
        / "20260706_operations_ledger_foundation.py"
    )
    spec = spec_from_file_location("operations_ledger_foundation", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _ExecutionResult:
    def __init__(self, bind: _RecordingBind) -> None:
        self.bind = bind

    def scalar(self) -> Any:
        if self.bind.scalar_results:
            return self.bind.scalar_results.pop(0)
        return 0

    def first(self) -> Any:
        if self.bind.first_results:
            return self.bind.first_results.pop(0)
        return None


class _RecordingBind:
    def __init__(
        self,
        *,
        scalar_results: list[Any] | None = None,
        first_results: list[Any] | None = None,
    ) -> None:
        self.sql: list[str] = []
        self.scalar_results = scalar_results or []
        self.first_results = first_results or []

    def execute(self, statement: Any) -> _ExecutionResult:
        self.sql.append(str(statement))
        return _ExecutionResult(self)


class _Inspector:
    def __init__(
        self, *, tables: set[str], columns: dict[str, list[str]] | None = None
    ) -> None:
        self.tables = tables
        self.columns = columns or {}

    def has_table(self, table_name: str) -> bool:
        return table_name in self.tables

    def get_columns(self, table_name: str) -> list[dict[str, str]]:
        return [{"name": name} for name in self.columns.get(table_name, [])]

    def get_unique_constraints(self, _table_name: str) -> list[dict[str, str]]:
        return []

    def get_check_constraints(self, _table_name: str) -> list[dict[str, str]]:
        return []

    def get_foreign_keys(self, _table_name: str) -> list[dict[str, str]]:
        return []


def test_migration_should_follow_notification_permission_head() -> None:
    module = _load_migration_module()

    assert module.down_revision == "20260623_notification_create_perm"


def test_create_payment_tables_should_define_flow_and_allocation_tables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_migration_module()
    create_table_calls: list[dict[str, Any]] = []
    create_index_calls: list[dict[str, Any]] = []

    class _Inspector:
        @staticmethod
        def has_table(table_name: str) -> bool:
            return False

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

    module._create_payment_tables(_Inspector())

    table_names = {call["table_name"] for call in create_table_calls}
    assert table_names == {"operational_payment_flows", "payment_allocations"}

    flow_columns = {
        column.name
        for call in create_table_calls
        if call["table_name"] == "operational_payment_flows"
        for column in call["columns"]
        if hasattr(column, "name")
    }
    allocation_columns = {
        column.name
        for call in create_table_calls
        if call["table_name"] == "payment_allocations"
        for column in call["columns"]
        if hasattr(column, "name")
    }

    assert {
        "flow_id",
        "flow_type",
        "occurred_on",
        "amount",
        "registered_by",
        "status",
    }.issubset(flow_columns)
    assert {
        "allocation_id",
        "flow_id",
        "target_type",
        "target_id",
        "year_month",
        "amount",
    }.issubset(allocation_columns)
    assert {call["index_name"] for call in create_index_calls} >= {
        "ix_operational_payment_flows_flow_type",
        "ix_payment_allocations_flow_id",
        "ix_payment_allocations_target_id",
    }


def test_backfill_ledger_views_should_fail_loud_when_active_rows_remain_unmapped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_migration_module()
    bind = _RecordingBind(scalar_results=[1])
    monkeypatch.setattr(module.op, "get_bind", lambda: bind)

    with pytest.raises(RuntimeError, match="without ledger_views"):
        module._backfill_ledger_views()


def test_service_fee_backfill_should_aggregate_legacy_source_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_migration_module()
    bind = _RecordingBind(first_results=[None, None, None])
    monkeypatch.setattr(module.op, "get_bind", lambda: bind)
    inspector = _Inspector(
        tables={"service_fee_ledgers"},
        columns={"service_fee_ledgers": ["source_ledger_id"]},
    )

    module._backfill_service_fee_ledgers(inspector)

    sql = "\n".join(bind.sql)
    assert "SUM(cle.paid_amount) AS calculation_base_amount" in sql
    assert "SUM(sfl.paid_amount) AS paid_amount" in sql
    assert "TO_JSONB(ARRAY_AGG(DISTINCT sfl.source_ledger_id))" in sql
    assert "DELETE FROM service_fee_ledgers AS sfl" in sql


def test_service_fee_backfill_should_fail_loud_for_invalid_entrusted_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_migration_module()
    bind = _RecordingBind(first_results=[{"contract_group_id": "group-1"}])
    monkeypatch.setattr(module.op, "get_bind", lambda: bind)
    inspector = _Inspector(tables={"service_fee_ledgers"})

    with pytest.raises(RuntimeError, match="exactly one entrusted contract"):
        module._backfill_service_fee_ledgers(inspector)


def test_service_fee_backfill_should_fail_loud_for_missing_source_ledger(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_migration_module()
    bind = _RecordingBind(first_results=[None, {"service_fee_entry_id": "fee-1"}])
    monkeypatch.setattr(module.op, "get_bind", lambda: bind)
    inspector = _Inspector(
        tables={"service_fee_ledgers"},
        columns={"service_fee_ledgers": ["source_ledger_id"]},
    )

    with pytest.raises(RuntimeError, match="missing source ledger"):
        module._backfill_service_fee_ledgers(inspector)


def test_payment_allocation_backfill_should_fail_loud_for_unallocated_rent_paid_amount(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_migration_module()
    bind = _RecordingBind(scalar_results=[1])
    monkeypatch.setattr(module.op, "get_bind", lambda: bind)
    inspector = _Inspector(tables=set())

    with pytest.raises(RuntimeError, match="contract_ledger_entries"):
        module._backfill_payment_allocations(inspector)


def test_payment_allocation_backfill_should_fail_loud_for_unallocated_service_fee_paid_amount(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_migration_module()
    bind = _RecordingBind(scalar_results=[0, 1])
    monkeypatch.setattr(module.op, "get_bind", lambda: bind)
    inspector = _Inspector(tables={"service_fee_ledgers"})

    with pytest.raises(RuntimeError, match="service_fee_ledgers"):
        module._backfill_payment_allocations(inspector)


def test_downgrade_is_fail_loud() -> None:
    module = _load_migration_module()

    with pytest.raises(RuntimeError, match="operations ledger foundation"):
        module.downgrade()
