"""Tests for Phase4 migration scripts."""

from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType

import pytest


def _load_module(filename: str, module_name: str) -> ModuleType:
    module_path = Path(__file__).resolve().parents[3] / "alembic" / "versions" / filename
    spec = spec_from_file_location(module_name, module_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_set_not_null_module() -> ModuleType:
    return _load_module(
        "20260301_phase4_set_party_columns_not_null.py",
        "phase4_set_party_columns_not_null",
    )


def _load_drop_legacy_module() -> ModuleType:
    return _load_module(
        "20260301_phase4_drop_legacy_party_columns.py",
        "phase4_drop_legacy_party_columns",
    )


class _InspectorStub:
    def __init__(self, columns: dict[str, list[dict[str, object]]]) -> None:
        self._columns = columns

    def has_table(self, table_name: str) -> bool:
        return table_name in self._columns

    def get_columns(self, table_name: str) -> list[dict[str, object]]:
        return self._columns.get(table_name, [])


def _nullable_columns(*column_names: str) -> list[dict[str, object]]:
    return [{"name": column_name, "nullable": True} for column_name in column_names]


def test_phase4_set_not_null_migration_revision_chain() -> None:
    module = _load_set_not_null_module()
    assert module.down_revision == "20260224_backfill_ownership_occupancy_policy_rules"
    assert module.depends_on is None


def test_phase4_drop_legacy_migration_revision_chain() -> None:
    module = _load_drop_legacy_module()
    assert module.down_revision == "20260301_phase4_set_party_columns_not_null"
    assert module.depends_on == "20260301_phase4_set_party_columns_not_null"


def test_set_not_null_upgrade_enforces_tenant_decision_and_skips_tenant_for_b(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_set_not_null_module()
    monkeypatch.setenv("PHASE4_TENANT_NOT_NULL_DECISION", "B")

    inspector = _InspectorStub(
        {
            "assets": _nullable_columns("owner_party_id", "manager_party_id"),
            "rent_contracts": _nullable_columns(
                "owner_party_id",
                "manager_party_id",
                "tenant_party_id",
            ),
            "rent_ledger": _nullable_columns("owner_party_id"),
            "projects": _nullable_columns("manager_party_id"),
        }
    )

    alter_calls: list[tuple[str, str]] = []
    monkeypatch.setattr(module.op, "get_bind", lambda: object())
    monkeypatch.setattr(module.sa, "inspect", lambda _bind: inspector)
    monkeypatch.setattr(module, "_assert_no_null_values", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        module.op,
        "alter_column",
        lambda table_name, column_name, **_kwargs: alter_calls.append(
            (table_name, column_name)
        ),
    )

    module.upgrade()

    assert ("assets", "owner_party_id") in alter_calls
    assert ("assets", "manager_party_id") in alter_calls
    assert ("rent_contracts", "owner_party_id") in alter_calls
    assert ("rent_contracts", "manager_party_id") in alter_calls
    assert ("rent_ledger", "owner_party_id") in alter_calls
    assert ("projects", "manager_party_id") in alter_calls
    assert ("rent_contracts", "tenant_party_id") not in alter_calls


def test_set_not_null_upgrade_hardens_tenant_for_decision_a(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_set_not_null_module()
    monkeypatch.setenv("PHASE4_TENANT_NOT_NULL_DECISION", "A")

    inspector = _InspectorStub(
        {
            "assets": _nullable_columns("owner_party_id", "manager_party_id"),
            "rent_contracts": _nullable_columns(
                "owner_party_id",
                "manager_party_id",
                "tenant_party_id",
            ),
            "rent_ledger": _nullable_columns("owner_party_id"),
            "projects": _nullable_columns("manager_party_id"),
        }
    )

    alter_calls: list[tuple[str, str]] = []
    monkeypatch.setattr(module.op, "get_bind", lambda: object())
    monkeypatch.setattr(module.sa, "inspect", lambda _bind: inspector)
    monkeypatch.setattr(module, "_assert_no_null_values", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        module.op,
        "alter_column",
        lambda table_name, column_name, **_kwargs: alter_calls.append(
            (table_name, column_name)
        ),
    )

    module.upgrade()

    assert ("rent_contracts", "tenant_party_id") in alter_calls


def test_set_not_null_upgrade_rejects_missing_decision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_set_not_null_module()
    monkeypatch.delenv("PHASE4_TENANT_NOT_NULL_DECISION", raising=False)

    with pytest.raises(RuntimeError):
        module.upgrade()


def test_drop_legacy_upgrade_drops_expected_columns_and_tables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_drop_legacy_module()

    inspector = _InspectorStub(
        {
            "assets": _nullable_columns(
                "organization_id",
                "ownership_id",
                "management_entity",
                "project_id",
            ),
            "rent_contracts": _nullable_columns("ownership_id"),
            "rent_ledger": _nullable_columns("ownership_id"),
            "projects": _nullable_columns(
                "organization_id",
                "management_entity",
                "ownership_entity",
            ),
            "property_certificates": _nullable_columns("organization_id"),
            "roles": _nullable_columns("organization_id"),
            "project_ownership_relations": _nullable_columns("id"),
            "property_owners": _nullable_columns("id"),
            "property_certificate_owners": _nullable_columns("certificate_id"),
            "abac_policy_subjects": _nullable_columns("id"),
        }
    )

    dropped_columns: list[tuple[str, str]] = []
    dropped_tables: list[str] = []
    monkeypatch.setattr(module.op, "get_bind", lambda: object())
    monkeypatch.setattr(module.sa, "inspect", lambda _bind: inspector)
    monkeypatch.setattr(
        module.op,
        "drop_column",
        lambda table_name, column_name: dropped_columns.append((table_name, column_name)),
    )
    monkeypatch.setattr(module.op, "drop_table", lambda table_name: dropped_tables.append(table_name))

    module.upgrade()

    assert ("assets", "organization_id") in dropped_columns
    assert ("assets", "ownership_id") in dropped_columns
    assert ("assets", "management_entity") in dropped_columns
    assert ("assets", "project_id") in dropped_columns
    assert ("rent_contracts", "ownership_id") in dropped_columns
    assert ("rent_ledger", "ownership_id") in dropped_columns
    assert ("projects", "organization_id") in dropped_columns
    assert ("projects", "management_entity") in dropped_columns
    assert ("projects", "ownership_entity") in dropped_columns
    assert ("property_certificates", "organization_id") in dropped_columns
    assert ("roles", "organization_id") in dropped_columns

    assert "project_ownership_relations" in dropped_tables
    assert "property_owners" in dropped_tables
    assert "property_certificate_owners" in dropped_tables
    assert "abac_policy_subjects" in dropped_tables
    assert dropped_tables.index("property_certificate_owners") < dropped_tables.index(
        "property_owners"
    )
