"""Tests for the legacy contract backfill migration."""

from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType

import pytest


def _load_migration_module() -> ModuleType:
    module_path = (
        Path(__file__).resolve().parents[3]
        / "alembic"
        / "versions"
        / "20260306_m2_legacy_contract_backfill.py"
    )
    spec = spec_from_file_location("legacy_contract_backfill_migration", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_collection_fk_module() -> ModuleType:
    module_path = (
        Path(__file__).resolve().parents[3]
        / "alembic"
        / "versions"
        / "20260307_m2_collection_records_contract_fk.py"
    )
    spec = spec_from_file_location("collection_records_contract_fk_migration", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_backfill_migration_should_be_inserted_before_collection_fk() -> None:
    module = _load_migration_module()
    collection_fk_module = _load_collection_fk_module()

    assert module.down_revision == "20260306_m2_contract_ledger_entries"
    assert collection_fk_module.down_revision == module.revision


def test_upgrade_should_backfill_legacy_contract_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_migration_module()
    executed_sql: list[str] = []

    class FakeInspector:
        def has_table(self, table_name: str) -> bool:
            return table_name in {
                "rent_contracts",
                "rent_contract_assets",
                "rent_terms",
                "rent_ledger",
                "collection_records",
                "contract_groups",
                "contracts",
                "contract_assets",
                "contract_group_assets",
                "lease_contract_details",
                "agency_agreement_details",
                "contract_relations",
                "contract_rent_terms",
                "contract_ledger_entries",
            }

    class FakeConnection:
        def execute(self, statement, *args, **kwargs):  # type: ignore[no-untyped-def]
            sql_text = str(getattr(statement, "text", statement))
            executed_sql.append(sql_text)
            if "SELECT COUNT(*)" in sql_text:
                return type("FakeResult", (), {"scalar": lambda self: 0})()
            return None

    monkeypatch.setattr(module.op, "get_bind", lambda: FakeConnection())
    monkeypatch.setattr(module.sa, "inspect", lambda _bind: FakeInspector())

    module.upgrade()

    joined_sql = "\n".join(executed_sql)
    assert "INSERT INTO contract_groups" in joined_sql
    assert "INSERT INTO contracts" in joined_sql
    assert "INSERT INTO lease_contract_details" in joined_sql
    assert "INSERT INTO agency_agreement_details" in joined_sql
    assert "INSERT INTO contract_assets" in joined_sql
    assert "INSERT INTO contract_group_assets" in joined_sql
    assert "INSERT INTO contract_rent_terms" in joined_sql
    assert "INSERT INTO contract_ledger_entries" in joined_sql
    assert "INSERT INTO contract_relations" in joined_sql
    assert "THEN 'DIRECT_LEASE'" in joined_sql
    assert "THEN 'AGENCY_DIRECT'" in joined_sql
    assert "legacy-group-" in joined_sql
    assert "MIG-" in joined_sql


def test_upgrade_should_fail_closed_when_agency_backfill_keeps_invalid_relation_types(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_migration_module()

    class FakeInspector:
        def has_table(self, table_name: str) -> bool:
            return table_name in {
                "rent_contracts",
                "rent_contract_assets",
                "rent_terms",
                "rent_ledger",
                "collection_records",
                "contract_groups",
                "contracts",
                "contract_assets",
                "contract_group_assets",
                "lease_contract_details",
                "agency_agreement_details",
                "contract_relations",
                "contract_rent_terms",
                "contract_ledger_entries",
            }

    class FakeConnection:
        def execute(self, statement, *args, **kwargs):  # type: ignore[no-untyped-def]
            sql_text = str(getattr(statement, "text", statement))
            if "group_relation_type NOT IN ('ENTRUSTED', 'DIRECT_LEASE')" in sql_text:
                return type("FakeResult", (), {"scalar": lambda self: 1})()
            if "SELECT COUNT(*)" in sql_text:
                return type("FakeResult", (), {"scalar": lambda self: 0})()
            return None

    monkeypatch.setattr(module.op, "get_bind", lambda: FakeConnection())
    monkeypatch.setattr(module.sa, "inspect", lambda _bind: FakeInspector())

    with pytest.raises(RuntimeError, match="legacy agency groups"):
        module.upgrade()


def test_upgrade_sql_should_cast_case_results_to_enum_types(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_migration_module()
    executed_sql: list[str] = []

    class FakeInspector:
        def has_table(self, table_name: str) -> bool:
            return table_name in {
                "rent_contracts",
                "rent_contract_assets",
                "rent_terms",
                "rent_ledger",
                "collection_records",
                "contract_groups",
                "contracts",
                "contract_assets",
                "contract_group_assets",
                "lease_contract_details",
                "agency_agreement_details",
                "contract_relations",
                "contract_rent_terms",
                "contract_ledger_entries",
            }

    class FakeConnection:
        def execute(self, statement, *args, **kwargs):  # type: ignore[no-untyped-def]
            sql_text = str(getattr(statement, "text", statement))
            executed_sql.append(sql_text)
            if "SELECT COUNT(*)" in sql_text:
                return type("FakeResult", (), {"scalar": lambda self: 0})()
            return None

    monkeypatch.setattr(module.op, "get_bind", lambda: FakeConnection())
    monkeypatch.setattr(module.sa, "inspect", lambda _bind: FakeInspector())

    module.upgrade()

    joined_sql = "\n".join(executed_sql)
    assert "END::revenuemode AS revenue_mode" in joined_sql
    assert "END::contractdirection AS contract_direction" in joined_sql
    assert "END::grouprelationtype AS group_relation_type" in joined_sql
    assert "END::contractlifecyclestatus AS status" in joined_sql
    assert "END::contractreviewstatus AS review_status" in joined_sql
    assert "END::contractrelationtype AS relation_type" in joined_sql
