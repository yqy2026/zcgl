"""Contract tests for the irreversible legacy document schema cleanup."""

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

_MIGRATION_FILE = "20260722_drop_legacy_document_and_prompt_schema.py"
_LEGACY_TABLES = {
    "property_certificate_attachments",
    "pdf_import_session_logs",
    "pdf_import_configurations",
    "pdf_import_sessions",
    "extraction_feedback",
    "prompt_metrics",
    "prompt_versions",
    "prompt_templates",
}


def _load_migration_module() -> ModuleType:
    module_path = (
        Path(__file__).resolve().parents[3] / "alembic" / "versions" / _MIGRATION_FILE
    )
    spec = spec_from_file_location(
        "drop_legacy_document_and_prompt_schema", module_path
    )
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_follows_current_head() -> None:
    module = _load_migration_module()

    assert module.down_revision == "20260714_asset_manager_party_nullable"


def test_upgrade_drops_only_retired_document_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_migration_module()
    dropped_tables: list[str] = []
    dropped_columns: list[tuple[str, str]] = []
    dropped_constraints: list[tuple[str, str, str]] = []
    executed_sql: list[str] = []

    monkeypatch.setattr(module.op, "drop_table", dropped_tables.append)
    monkeypatch.setattr(
        module.op,
        "drop_column",
        lambda table_name, column_name: dropped_columns.append(
            (table_name, column_name)
        ),
    )
    monkeypatch.setattr(
        module.op,
        "drop_constraint",
        lambda name, table_name, type_: dropped_constraints.append(
            (name, table_name, type_)
        ),
    )
    monkeypatch.setattr(
        module.op,
        "execute",
        lambda statement: executed_sql.append(
            str(getattr(statement, "text", statement))
        ),
    )

    module.upgrade()

    assert dropped_tables == [
        "property_certificate_attachments",
        "pdf_import_session_logs",
        "pdf_import_configurations",
        "pdf_import_sessions",
        "extraction_feedback",
        "prompt_metrics",
        "prompt_versions",
        "prompt_templates",
    ]
    assert dropped_columns == [
        ("property_certificates", "extraction_confidence"),
        ("property_certificates", "extraction_source"),
    ]
    assert dropped_constraints == [
        ("fk_prompt_templates_current_version", "prompt_templates", "foreignkey")
    ]
    cleanup_statements = [
        statement for statement in executed_sql if "llm_prompt" in statement
    ]
    assert cleanup_statements == [
        "DELETE FROM permission_grants WHERE permission_id IN "
        "(SELECT id FROM permissions WHERE resource = 'llm_prompt')",
        "DELETE FROM resource_permissions WHERE permission_id IN "
        "(SELECT id FROM permissions WHERE resource = 'llm_prompt')",
        "DELETE FROM role_permissions WHERE permission_id IN "
        "(SELECT id FROM permissions WHERE resource = 'llm_prompt')",
        "DELETE FROM abac_policy_rules WHERE resource_type = 'llm_prompt'",
        "DELETE FROM permissions WHERE resource = 'llm_prompt'",
    ]


def test_downgrade_fails_loudly() -> None:
    module = _load_migration_module()

    with pytest.raises(RuntimeError, match="irreversible"):
        module.downgrade()


@pytest.mark.database
def test_initial_revision_upgrades_without_retired_document_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A new PostgreSQL database must reach the one valid schema head."""
    test_database_url = os.getenv("TEST_DATABASE_URL")
    if test_database_url is None:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL migration coverage")

    base_url = sa.make_url(test_database_url)
    if base_url.database != "zcgl_test":
        raise RuntimeError(
            "refusing to create a migration test database from a non-zcgl_test URL"
        )

    database_name = f"zcgl_test_drop_legacy_document_{uuid.uuid4().hex[:8]}"
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
        assert _LEGACY_TABLES.isdisjoint(inspector.get_table_names())
        assert inspector.has_table("attachments")
        attachment_columns = {
            column["name"] for column in inspector.get_columns("attachments")
        }
        assert {"owner_type", "owner_id", "storage_key"}.issubset(attachment_columns)
        certificate_columns = {
            column["name"] for column in inspector.get_columns("property_certificates")
        }
        assert "extraction_confidence" not in certificate_columns
        assert "extraction_source" not in certificate_columns

        with engine.connect() as connection:
            version_rows = connection.scalars(
                sa.text("SELECT version_num FROM alembic_version")
            ).all()
            assert version_rows == [ScriptDirectory.from_config(config).get_current_head()]
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
