"""Deferral migration retains the source model's constraints."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace

import pytest
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from src.models.management_fee_deferral import ManagementFeeDeferral

pytestmark = pytest.mark.unit


def migration():
    path = (
        Path(__file__).resolve().parents[3]
        / "alembic/versions/20261029_management_fee_deferrals.py"
    )
    spec = spec_from_file_location("fee_deferral_migration", path)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_matches_deferral_model(monkeypatch):
    module = migration()
    metadata = sa.MetaData()
    monkeypatch.setattr(
        module,
        "op",
        SimpleNamespace(
            create_table=lambda name, *items: sa.Table(name, metadata, *items)
        ),
    )
    module.upgrade()
    assert module.down_revision == "20261029_management_fees"
    assert len(module.revision) <= 32
    expected = ManagementFeeDeferral.__table__
    actual = metadata.tables[expected.name]
    assert set(actual.c.keys()) == set(expected.c.keys())
    for name, column in expected.c.items():
        other = actual.c[name]
        assert other.nullable == column.nullable
        assert other.primary_key == column.primary_key
        assert str(other.type.compile(postgresql.dialect())) == str(
            column.type.compile(postgresql.dialect())
        )
        assert {fk.target_fullname for fk in other.foreign_keys} == {
            fk.target_fullname for fk in column.foreign_keys
        }
    for kind in (sa.CheckConstraint, sa.UniqueConstraint):

        def signature(table):
            return {
                (
                    c.name,
                    str(c.sqltext)
                    if isinstance(c, sa.CheckConstraint)
                    else tuple(c.columns.keys()),
                )
                for c in table.constraints
                if isinstance(c, kind)
            }

        assert signature(actual) == signature(expected)


def test_downgrade_cannot_destroy_deferral_decisions():
    with pytest.raises(RuntimeError, match="append-only"):
        migration().downgrade()
