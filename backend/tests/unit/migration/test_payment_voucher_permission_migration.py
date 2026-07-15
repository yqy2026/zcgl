"""Tests for the independent payment-voucher download permission migration."""

from __future__ import annotations

import os
import uuid
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType

import pytest
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def _module_path() -> Path:
    return (
        Path(__file__).resolve().parents[3]
        / "alembic"
        / "versions"
        / "20260713_payment_voucher_download_permission.py"
    )


def _load_migration_module() -> ModuleType:
    spec = spec_from_file_location(
        "payment_voucher_download_permission", _module_path()
    )
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_voucher_permission_is_independent_from_ledger_read() -> None:
    module = _load_migration_module()
    source = _module_path().read_text(encoding="utf-8")

    assert module.down_revision == "20260713_payment_voucher_attachments"
    assert 'resource_type="ledger_voucher"' in source
    assert "permission:ledger_voucher:read" in source
    assert "permission:ledger:read" in source
    assert "system_admin" in source
    assert "ops_admin" in source
    assert "reviewer" in source
    assert "executive" in source
    assert "viewer" in source


def test_reviewer_static_permission_has_matching_audit_policy_rule() -> None:
    """The reviewer role is mapped to audit_viewer and needs both authz layers."""
    module = _load_migration_module()

    assert "audit_viewer" in module._POLICY_NAMES


def test_voucher_permission_migration_downgrade_fails_loud() -> None:
    module = _load_migration_module()

    with pytest.raises(RuntimeError, match="voucher download permission"):
        module.downgrade()


@pytest.mark.database
def test_upgrade_executes_on_postgresql_and_grants_voucher_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PostgreSQL must accept the migration's typed ABAC rule parameters."""
    test_database_url = os.getenv("TEST_DATABASE_URL")
    if test_database_url is None:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL migration coverage")

    base_url = sa.make_url(test_database_url)
    if base_url.database != "zcgl_test":
        raise RuntimeError(
            "refusing to create a migration test database from a non-zcgl_test URL"
        )

    database_name = f"zcgl_test_voucher_permission_{uuid.uuid4().hex[:8]}"
    database_url = base_url.set(database=database_name)
    admin_engine = sa.create_engine(
        base_url.set(database="postgres"),
        isolation_level="AUTOCOMMIT",
    )
    engine: sa.Engine | None = None

    try:
        with admin_engine.connect() as connection:
            connection.execute(sa.text(f'CREATE DATABASE "{database_name}"'))

        engine = sa.create_engine(database_url)
        metadata = sa.MetaData()
        abac_action = postgresql.ENUM("read", name="abac_action")
        policies = sa.Table(
            "abac_policies",
            metadata,
            sa.Column("id", sa.String, primary_key=True),
            sa.Column("name", sa.String, nullable=False, unique=True),
        )
        rules = sa.Table(
            "abac_policy_rules",
            metadata,
            sa.Column("id", sa.String, primary_key=True),
            sa.Column("policy_id", sa.String, nullable=False),
            sa.Column("resource_type", sa.String, nullable=False),
            sa.Column("action", abac_action, nullable=False),
            sa.Column("condition_expr", postgresql.JSONB, nullable=False),
            sa.Column("field_mask", postgresql.JSONB),
        )
        permissions = sa.Table(
            "permissions",
            metadata,
            sa.Column("id", sa.String, primary_key=True),
            sa.Column("name", sa.String, nullable=False, unique=True),
            sa.Column("display_name", sa.String, nullable=False),
            sa.Column("description", sa.String, nullable=False),
            sa.Column("resource", sa.String, nullable=False),
            sa.Column("action", sa.String, nullable=False),
            sa.Column("is_system_permission", sa.Boolean, nullable=False),
            sa.Column("requires_approval", sa.Boolean, nullable=False),
            sa.Column("created_at", sa.DateTime, nullable=False),
            sa.Column("updated_at", sa.DateTime, nullable=False),
        )
        roles = sa.Table(
            "roles",
            metadata,
            sa.Column("id", sa.String, primary_key=True),
            sa.Column("name", sa.String, nullable=False, unique=True),
        )
        role_permissions = sa.Table(
            "role_permissions",
            metadata,
            sa.Column("role_id", sa.String, nullable=False),
            sa.Column("permission_id", sa.String, nullable=False),
            sa.Column("created_at", sa.DateTime, nullable=False),
        )
        metadata.create_all(engine)

        module = _load_migration_module()
        with engine.begin() as connection:
            connection.execute(
                policies.insert(),
                [
                    {"id": f"policy:{name}", "name": name}
                    for name in module._POLICY_NAMES
                ],
            )
            connection.execute(
                roles.insert(),
                [
                    {"id": f"role:{name}", "name": name}
                    for name in (
                        "system_admin",
                        "ops_admin",
                        "reviewer",
                        "executive",
                        "viewer",
                    )
                ],
            )
            monkeypatch.setattr(module.op, "get_bind", lambda: connection)

            module.upgrade()

            assert connection.scalar(
                sa.select(sa.func.count()).select_from(rules)
            ) == len(module._POLICY_NAMES)
            assert (
                connection.scalar(sa.select(sa.func.count()).select_from(permissions))
                == 2
            )
            assert (
                connection.scalar(
                    sa.select(sa.func.count()).select_from(role_permissions)
                )
                == 10
            )
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
