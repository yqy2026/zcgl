"""Tests for frozen ledger attribution backfill migration."""

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
        / "20260618_backfill_ledger_frozen_attribution.py"
    )
    spec = spec_from_file_location("ledger_frozen_attribution_backfill", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_should_follow_frozen_attribution_head() -> None:
    module = _load_migration_module()

    assert module.down_revision == "20260618_ledger_frozen_attribution"


def test_upgrade_should_backfill_rent_ledgers_then_service_fee_ledgers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_migration_module()
    executed_sql: list[str] = []

    class _ScalarResult:
        @staticmethod
        def scalar() -> int:
            return 0

    class _Bind:
        @staticmethod
        def execute(sql_text: Any) -> _ScalarResult:
            executed_sql.append(str(sql_text))
            return _ScalarResult()

    class _Inspector:
        @staticmethod
        def has_table(table_name: str) -> bool:
            return table_name in module.REQUIRED_TABLES

        @staticmethod
        def get_columns(table_name: str) -> list[dict[str, str]]:
            if table_name in {"contract_ledger_entries", "service_fee_ledgers"}:
                return [
                    {"name": "attributed_project_id"},
                    {"name": "attributed_owner_party_id"},
                    {"name": "attributed_operator_party_id"},
                    {"name": "attributed_asset_ids"},
                ]
            return []

    monkeypatch.setattr(module.op, "get_bind", lambda: _Bind())
    monkeypatch.setattr(module.sa, "inspect", lambda _bind: _Inspector())

    module.upgrade()

    joined_sql = "\n".join(executed_sql)
    assert len(executed_sql) == 4
    assert "UPDATE contract_ledger_entries AS cle" in executed_sql[0]
    assert "COALESCE(contract_assets.asset_ids, group_assets.asset_ids)" in joined_sql
    assert "attributed_project_id = COALESCE" in joined_sql
    assert "attributed_owner_party_id = COALESCE" in joined_sql
    assert "attributed_operator_party_id = COALESCE" in joined_sql
    assert "attributed_asset_ids = COALESCE" in joined_sql
    assert "UPDATE service_fee_ledgers AS sfl" in executed_sql[1]
    assert "sfl.source_ledger_id = cle.entry_id" in executed_sql[1]
    assert "FROM contract_ledger_entries" in executed_sql[2]
    assert "FROM service_fee_ledgers" in executed_sql[3]


def test_upgrade_should_skip_when_attribution_columns_are_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_migration_module()
    executed_sql: list[str] = []

    class _Inspector:
        @staticmethod
        def has_table(table_name: str) -> bool:
            return table_name in module.REQUIRED_TABLES

        @staticmethod
        def get_columns(table_name: str) -> list[dict[str, str]]:
            return []

    monkeypatch.setattr(
        module.op,
        "get_bind",
        lambda: type("_Bind", (), {"execute": executed_sql.append})(),
    )
    monkeypatch.setattr(module.sa, "inspect", lambda _bind: _Inspector())

    module.upgrade()

    assert executed_sql == []


def test_upgrade_should_fail_loudly_when_backfill_leaves_missing_attribution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_migration_module()

    class _ScalarResult:
        def __init__(self, value: int) -> None:
            self.value = value

        def scalar(self) -> int:
            return self.value

    class _Bind:
        calls = 0

        @classmethod
        def execute(cls, sql_text: Any) -> _ScalarResult:
            cls.calls += 1
            if "SELECT COUNT(*)" in str(sql_text):
                return _ScalarResult(1)
            return _ScalarResult(0)

    class _Inspector:
        @staticmethod
        def has_table(table_name: str) -> bool:
            return table_name in module.REQUIRED_TABLES

        @staticmethod
        def get_columns(table_name: str) -> list[dict[str, str]]:
            if table_name in {"contract_ledger_entries", "service_fee_ledgers"}:
                return [
                    {"name": "attributed_project_id"},
                    {"name": "attributed_owner_party_id"},
                    {"name": "attributed_operator_party_id"},
                    {"name": "attributed_asset_ids"},
                ]
            return []

    monkeypatch.setattr(module.op, "get_bind", lambda: _Bind())
    monkeypatch.setattr(module.sa, "inspect", lambda _bind: _Inspector())

    with pytest.raises(RuntimeError, match="contract_ledger_entries"):
        module.upgrade()
