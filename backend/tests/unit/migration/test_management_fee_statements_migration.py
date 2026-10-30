"""Management fee DDL agrees with model storage contracts without a database."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace

import pytest
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql, sqlite

from src.models.management_fee_statement import (
    ManagementFeeStatement,
    ManagementFeeStatementLine,
)

pytestmark = pytest.mark.unit


def _migration():
    path = (
        Path(__file__).resolve().parents[3]
        / "alembic/versions/20261029_management_fee_statements.py"
    )
    spec = spec_from_file_location("management_fee_statements_migration", path)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _checks(table):
    return {
        str(c.sqltext) for c in table.constraints if isinstance(c, sa.CheckConstraint)
    }


def _uniques(table):
    return {
        tuple(c.columns.keys())
        for c in table.constraints
        if isinstance(c, sa.UniqueConstraint)
    }


def _indexes(table):
    return {
        (
            idx.name,
            tuple(idx.columns.keys()),
            idx.unique,
            str(idx.dialect_options["postgresql"]["where"]),
            str(idx.dialect_options["sqlite"]["where"]),
        )
        for idx in table.indexes
    }


def test_migration_matches_model_and_expands_receipt_commands(monkeypatch):
    module = _migration()
    metadata = sa.MetaData()
    changes = []

    def create_table(name, *items):
        return sa.Table(name, metadata, *items)

    def create_index(name, table_name, columns, **kwargs):
        table = metadata.tables[table_name]
        sa.Index(name, *(table.c[column] for column in columns), **kwargs)

    monkeypatch.setattr(
        module,
        "op",
        SimpleNamespace(
            create_table=create_table,
            create_index=create_index,
            drop_constraint=lambda *args, **kwargs: changes.append(
                ("drop", args, kwargs)
            ),
            alter_column=lambda *args, **kwargs: changes.append(
                ("alter", args, kwargs)
            ),
            create_check_constraint=lambda *args, **kwargs: changes.append(
                ("check", args, kwargs)
            ),
        ),
    )
    module.upgrade()
    assert module.down_revision == "20261028_termination_receipts"
    assert len(module.revision) <= 32
    for model in (ManagementFeeStatement, ManagementFeeStatementLine):
        expected = model.__table__
        actual = metadata.tables[expected.name]
        assert set(actual.columns.keys()) == set(expected.columns.keys())
        for name, column in expected.columns.items():
            migrated = actual.c[name]
            assert migrated.nullable == column.nullable
            assert migrated.primary_key == column.primary_key
            for dialect in (postgresql.dialect(), sqlite.dialect()):
                assert str(migrated.type.compile(dialect)) == str(
                    column.type.compile(dialect)
                )
            if isinstance(column.type, sa.JSON):
                assert migrated.type.none_as_null == column.type.none_as_null
            assert {fk.target_fullname for fk in migrated.foreign_keys} == {
                fk.target_fullname for fk in column.foreign_keys
            }
        assert _checks(actual) == _checks(expected)
        assert _uniques(actual) == _uniques(expected)
        assert _indexes(actual) == _indexes(expected)
    assert [item[0] for item in changes] == ["drop", "alter", "check"]
    _, args, kwargs = changes[1]
    assert args == ("asset_contract_write_receipts", "command_kind")
    assert kwargs["existing_type"].length == 30
    assert kwargs["type_"].length == 64
    assert kwargs["existing_nullable"] is False
    for command in (
        "defer_management_fee_line",
        "confirm_management_fee_statement",
        "supersede_management_fee_statement",
    ):
        assert f"'{command}'" in changes[2][1][2]


def test_downgrade_refuses_to_destroy_confirmation_facts():
    with pytest.raises(RuntimeError, match="append-only"):
        _migration().downgrade()
