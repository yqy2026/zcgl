"""Tests for Phase 3 role redefinition migration."""

from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType

import sqlalchemy as sa


def _load_module() -> ModuleType:
    module_path = (
        Path(__file__).resolve().parents[3]
        / "alembic"
        / "versions"
        / "20260408_phase3_role_redefinition.py"
    )
    spec = spec_from_file_location("phase3_role_redefinition", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _create_connection() -> sa.engine.Connection:
    engine = sa.create_engine("sqlite+pysqlite:///:memory:", future=True)
    connection = engine.connect()
    connection.info["_test_engine"] = engine
    return connection


def _close_connection(connection: sa.engine.Connection) -> None:
    engine = connection.info.pop("_test_engine")
    connection.close()
    engine.dispose()


def _bootstrap_schema(connection: sa.engine.Connection) -> None:
    connection.execute(
        sa.text(
            """
            CREATE TABLE roles (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                description TEXT,
                level INTEGER NOT NULL,
                category TEXT,
                is_system_role BOOLEAN NOT NULL,
                is_active BOOLEAN NOT NULL,
                party_id TEXT,
                scope TEXT NOT NULL,
                scope_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                created_by TEXT,
                updated_by TEXT
            )
            """
        )
    )
    connection.execute(
        sa.text(
            """
            CREATE TABLE user_role_assignments (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                role_id TEXT NOT NULL,
                assigned_by TEXT,
                assigned_at TEXT,
                is_active BOOLEAN NOT NULL,
                updated_at TEXT
            )
            """
        )
    )


def test_migration_revision_chain() -> None:
    module = _load_module()
    assert module.down_revision == "20260402_req_apr_001_approval_domain"


def test_upgrade_should_redefine_legacy_roles_and_assignments() -> None:
    module = _load_module()
    connection = _create_connection()
    try:
        _bootstrap_schema(connection)
        now = "2026-04-08T00:00:00"
        legacy_roles = [
            ("r-admin", "admin"),
            ("r-manager", "manager"),
            ("r-user", "user"),
            ("r-viewer", "viewer"),
            ("r-asset-manager", "asset_manager"),
            ("r-project-manager", "project_manager"),
            ("r-auditor", "auditor"),
        ]
        for role_id, role_name in legacy_roles:
            connection.execute(
                sa.text(
                    """
                    INSERT INTO roles (
                        id, name, display_name, description, level, category, is_system_role,
                        is_active, party_id, scope, scope_id, created_at, updated_at, created_by, updated_by
                    ) VALUES (
                        :id, :name, :display_name, '', 1, 'legacy', 1, 1, NULL, 'global', NULL,
                        :created_at, :updated_at, 'seed', 'seed'
                    )
                    """
                ),
                {
                    "id": role_id,
                    "name": role_name,
                    "display_name": role_name,
                    "created_at": now,
                    "updated_at": now,
                },
            )

        assignments = [
            ("a1", "u1", "r-admin"),
            ("a2", "u2", "r-manager"),
            ("a3", "u3", "r-user"),
            ("a4", "u4", "r-asset-manager"),
            ("a5", "u5", "r-project-manager"),
            ("a6", "u6", "r-auditor"),
            ("a7", "u7", "r-viewer"),
        ]
        for assignment_id, user_id, role_id in assignments:
            connection.execute(
                sa.text(
                    """
                    INSERT INTO user_role_assignments (
                        id, user_id, role_id, assigned_by, assigned_at, is_active, updated_at
                    ) VALUES (
                        :id, :user_id, :role_id, 'seed', :assigned_at, 1, :updated_at
                    )
                    """
                ),
                {
                    "id": assignment_id,
                    "user_id": user_id,
                    "role_id": role_id,
                    "assigned_at": now,
                    "updated_at": now,
                },
            )

        module._apply_role_redefinition(connection)

        role_names = set(
            connection.execute(sa.text("SELECT name FROM roles")).scalars().all()
        )
        assert {
            "system_admin",
            "ops_admin",
            "perm_admin",
            "reviewer",
            "executive",
            "viewer",
        }.issubset(role_names)

        inactive_legacy = set(
            connection.execute(
                sa.text(
                    """
                    SELECT name FROM roles
                    WHERE name IN ('manager', 'user', 'asset_manager', 'project_manager', 'auditor')
                      AND is_active = 0
                    """
                )
            )
            .scalars()
            .all()
        )
        assert inactive_legacy == {
            "manager",
            "user",
            "asset_manager",
            "project_manager",
            "auditor",
        }

        assignment_rows = connection.execute(
            sa.text(
                """
                SELECT ura.user_id, r.name
                FROM user_role_assignments AS ura
                JOIN roles AS r ON r.id = ura.role_id
                WHERE ura.is_active = 1
                ORDER BY ura.user_id
                """
            )
        ).fetchall()
        assert assignment_rows == [
            ("u1", "system_admin"),
            ("u2", "executive"),
            ("u3", "viewer"),
            ("u4", "ops_admin"),
            ("u5", "ops_admin"),
            ("u6", "viewer"),
            ("u7", "viewer"),
        ]
    finally:
        _close_connection(connection)
