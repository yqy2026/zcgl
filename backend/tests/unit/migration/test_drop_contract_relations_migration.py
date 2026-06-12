"""Tests for dropping the removed contract_relations table."""

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
        / "20260612_drop_contract_relations.py"
    )
    spec = spec_from_file_location("drop_contract_relations_migration", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_upgrade_should_drop_contract_relations_table(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_migration_module()
    added_columns: list[tuple[str, str]] = []
    created_indexes: list[tuple[str, str, list[str], bool]] = []
    created_foreign_keys: list[tuple[str, str, str, list[str], list[str]]] = []
    dropped_tables: list[str] = []

    def fake_add_column(table_name: str, column) -> None:  # type: ignore[no-untyped-def]
        added_columns.append((table_name, column.name))

    def fake_create_index(
        index_name: str, table_name: str, columns: list[str], unique: bool = False
    ) -> None:
        created_indexes.append((index_name, table_name, columns, unique))

    def fake_create_foreign_key(
        constraint_name: str,
        source_table: str,
        referent_table: str,
        local_cols: list[str],
        remote_cols: list[str],
    ) -> None:
        created_foreign_keys.append(
            (constraint_name, source_table, referent_table, local_cols, remote_cols)
        )

    monkeypatch.setattr(module.op, "add_column", fake_add_column)
    monkeypatch.setattr(module.op, "create_index", fake_create_index)
    monkeypatch.setattr(module.op, "create_foreign_key", fake_create_foreign_key)
    monkeypatch.setattr(module.op, "drop_table", dropped_tables.append)

    module.upgrade()

    assert added_columns == [("contracts", "correction_source_contract_id")]
    assert created_indexes == [
        (
            "ix_contracts_correction_source_contract_id",
            "contracts",
            ["correction_source_contract_id"],
            False,
        )
    ]
    assert created_foreign_keys == [
        (
            "fk_contracts_correction_source_contract_id_contracts",
            "contracts",
            "contracts",
            ["correction_source_contract_id"],
            ["contract_id"],
        )
    ]
    assert dropped_tables == ["contract_relations"]


def test_downgrade_should_fail_loudly() -> None:
    module = _load_migration_module()

    with pytest.raises(RuntimeError, match="contract_relations"):
        module.downgrade()
