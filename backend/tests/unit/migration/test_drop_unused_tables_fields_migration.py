"""Contract tests for the irreversible unused-tables/fields cleanup migration.

Covers the P0/P1 cleanup agreed in docs/issues/2026-08-04-unused-db-fields-audit.md:
- Drop 4 never-written tables (asset_documents, party_role_defs,
  party_role_bindings, asset_management_history)
- Drop 5 groups of dead columns on live tables (audit_logs.user_organization,
  abac_role_policies.priority_override/params_override,
  certificate_party_relations.share_ratio, assets.asset_form/spatial_level/
  business_usage, project_assets.bind_reason/unbind_reason)
"""

from __future__ import annotations

import os
import uuid
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType

import pytest
import sqlalchemy as sa
from alembic.config import Config
from alembic.script import ScriptDirectory

from alembic import command

_MIGRATION_FILE = "20260808_drop_unused_tables_fields.py"
_DROPPED_TABLES = {
    "asset_documents",
    "party_role_defs",
    "party_role_bindings",
    "asset_management_history",
}
_DROPPED_COLUMNS = {
    ("audit_logs", "user_organization"),
    ("abac_role_policies", "priority_override"),
    ("abac_role_policies", "params_override"),
    ("certificate_party_relations", "share_ratio"),
    ("assets", "asset_form"),
    ("assets", "spatial_level"),
    ("assets", "business_usage"),
    ("project_assets", "bind_reason"),
    ("project_assets", "unbind_reason"),
}


def _load_migration_module() -> ModuleType:
    module_path = (
        Path(__file__).resolve().parents[3] / "alembic" / "versions" / _MIGRATION_FILE
    )
    spec = spec_from_file_location("drop_unused_tables_fields", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _InspectorStub:
    """Minimal inspector stub mirroring tests/unit/migration/test_phase4_migrations.py."""

    def __init__(self, tables: set[str], columns: dict[str, set[str]]) -> None:
        self._tables = tables
        self._columns = columns

    def has_table(self, table_name: str) -> bool:
        return table_name in self._tables

    def get_columns(self, table_name: str) -> list[dict[str, object]]:
        return [
            {"name": column_name}
            for column_name in self._columns.get(table_name, set())
        ]


def test_migration_follows_current_head() -> None:
    module = _load_migration_module()

    assert module.down_revision == "20260806_user_party_scope_batch_commit_receipts"


def test_upgrade_drops_only_target_tables_and_columns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_migration_module()

    inspector = _InspectorStub(
        tables=set(_DROPPED_TABLES)
        | {
            "assets",
            "audit_logs",
            "abac_role_policies",
            "certificate_party_relations",
            "project_assets",
        },
        columns={
            "audit_logs": {"user_id", "user_organization", "action"},
            "abac_role_policies": {
                "id",
                "priority_override",
                "params_override",
                "policy_id",
            },
            "certificate_party_relations": {"certificate_id", "share_ratio"},
            "assets": {"id", "asset_form", "spatial_level", "business_usage"},
            "project_assets": {"project_id", "bind_reason", "unbind_reason"},
            **{table_name: {"id"} for table_name in _DROPPED_TABLES},
        },
    )
    dropped_tables: list[str] = []
    dropped_columns: list[tuple[str, str]] = []

    monkeypatch.setattr(module.op, "get_bind", lambda: object())
    monkeypatch.setattr(module.sa, "inspect", lambda _bind: inspector)
    monkeypatch.setattr(module.op, "drop_table", dropped_tables.append)
    monkeypatch.setattr(
        module.op,
        "drop_column",
        lambda table_name, column_name: dropped_columns.append(
            (table_name, column_name)
        ),
    )

    module.upgrade()

    assert set(dropped_tables) == _DROPPED_TABLES
    assert set(dropped_columns) == _DROPPED_COLUMNS


def test_downgrade_fails_loudly() -> None:
    module = _load_migration_module()

    with pytest.raises(RuntimeError, match="irreversible"):
        module.downgrade()


@pytest.mark.database
def test_head_upgrades_without_unused_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A fresh PostgreSQL database must reach the one valid schema head."""
    test_database_url = os.getenv("TEST_DATABASE_URL")
    if test_database_url is None:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL migration coverage")

    base_url = sa.make_url(test_database_url)
    if base_url.database != "zcgl_test":
        raise RuntimeError(
            "refusing to create a migration test database from a non-zcgl_test URL"
        )

    database_name = f"zcgl_test_drop_unused_{uuid.uuid4().hex[:8]}"
    database_url = base_url.set(database=database_name)
    admin_engine = sa.create_engine(
        base_url.set(database="postgres"),
        isolation_level="AUTOCOMMIT",
    )
    engine: sa.Engine | None = None

    try:
        with admin_engine.connect() as connection:
            connection.execute(sa.text(f'CREATE DATABASE "{database_name}"'))

        monkeypatch.setenv(
            "DATABASE_URL", database_url.render_as_string(hide_password=False)
        )
        config = Config(str(Path(__file__).resolve().parents[3] / "alembic.ini"))
        command.upgrade(config, "head")

        engine = sa.create_engine(database_url)
        inspector = sa.inspect(engine)
        assert _DROPPED_TABLES.isdisjoint(inspector.get_table_names())
        # Live tables must still exist after the cleanup.
        assert inspector.has_table("assets")
        assert inspector.has_table("audit_logs")
        assert inspector.has_table("project_assets")

        def _column_names(table_name: str) -> set[str]:
            return {column["name"] for column in inspector.get_columns(table_name)}

        assert "user_organization" not in _column_names("audit_logs")
        assert not {"priority_override", "params_override"} & _column_names(
            "abac_role_policies"
        )
        assert "share_ratio" not in _column_names("certificate_party_relations")
        assert not {"asset_form", "spatial_level", "business_usage"} & _column_names(
            "assets"
        )
        assert not {"bind_reason", "unbind_reason"} & _column_names("project_assets")

        with engine.connect() as connection:
            version_rows = connection.scalars(
                sa.text("SELECT version_num FROM alembic_version")
            ).all()
            assert version_rows == [
                ScriptDirectory.from_config(config).get_current_head()
            ]
    finally:
        if engine is not None:
            engine.dispose()
        with admin_engine.connect() as connection:
            connection.execute(
                sa.text(
                    "SELECT pg_terminate_backend(pid) "
                    "FROM pg_stat_activity "
                    "WHERE datname = :database AND pid <> pg_backend_pid()"
                ),
                {"database": database_name},
            )
            connection.execute(sa.text(f'DROP DATABASE IF EXISTS "{database_name}"'))
        admin_engine.dispose()
