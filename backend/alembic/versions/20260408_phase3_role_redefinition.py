"""Phase 3: migrate legacy 7-role RBAC model to the 6-role target set.

Revision ID: 20260408_phase3_role_redefinition
Revises: 20260402_req_apr_001_approval_domain
Create Date: 2026-04-08
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260408_phase3_role_redefinition"
down_revision = "20260402_req_apr_001_approval_domain"
branch_labels = None
depends_on = None


TARGET_ROLE_DEFINITIONS: dict[str, dict[str, Any]] = {
    "system_admin": {
        "display_name": "系统管理员",
        "description": "系统超级管理员，拥有全局权限",
        "level": 1,
        "category": "system",
    },
    "ops_admin": {
        "display_name": "运营管理员",
        "description": "运营管理员，负责业务域全量管理",
        "level": 2,
        "category": "operations",
    },
    "perm_admin": {
        "display_name": "权限管理员",
        "description": "权限管理员，仅管理用户/角色/权限/策略",
        "level": 2,
        "category": "security",
    },
    "reviewer": {
        "display_name": "审核员",
        "description": "负责审批与审核处理",
        "level": 3,
        "category": "review",
    },
    "executive": {
        "display_name": "业务经办",
        "description": "负责日常业务录入与维护",
        "level": 4,
        "category": "business",
    },
    "viewer": {
        "display_name": "只读用户",
        "description": "只读查看业务数据",
        "level": 5,
        "category": "read_only",
    },
}

LEGACY_TO_TARGET_ROLE_NAME = {
    "admin": "system_admin",
    "manager": "executive",
    "user": "viewer",
    "viewer": "viewer",
    "asset_manager": "ops_admin",
    "project_manager": "ops_admin",
    "auditor": "viewer",
}


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _table_exists(connection: sa.engine.Connection, table_name: str) -> bool:
    return sa.inspect(connection).has_table(table_name)


def _roles_by_name(connection: sa.engine.Connection) -> dict[str, dict[str, Any]]:
    rows = (
        connection.execute(
            sa.text(
                """
                SELECT id, name, display_name, is_active
                FROM roles
                """
            )
        )
        .mappings()
        .all()
    )
    return {str(row["name"]): dict(row) for row in rows}


def _upsert_target_role(
    connection: sa.engine.Connection,
    *,
    role_name: str,
    now: datetime,
) -> str:
    role_definition = TARGET_ROLE_DEFINITIONS[role_name]
    roles = _roles_by_name(connection)
    existing = roles.get(role_name)
    if existing is not None:
        connection.execute(
            sa.text(
                """
                UPDATE roles
                SET display_name = :display_name,
                    description = :description,
                    level = :level,
                    category = :category,
                    is_system_role = :is_system_role,
                    is_active = :is_active,
                    scope = 'global',
                    scope_id = NULL,
                    updated_at = :updated_at,
                    updated_by = 'alembic:20260408_phase3_role_redefinition'
                WHERE id = :role_id
                """
            ),
            {
                "role_id": str(existing["id"]),
                "display_name": role_definition["display_name"],
                "description": role_definition["description"],
                "level": role_definition["level"],
                "category": role_definition["category"],
                "is_system_role": True,
                "is_active": True,
                "updated_at": now,
            },
        )
        return str(existing["id"])

    new_role_id = str(uuid.uuid4())
    connection.execute(
        sa.text(
            """
            INSERT INTO roles (
                id, name, display_name, description, level, category,
                is_system_role, is_active, party_id, scope, scope_id,
                created_at, updated_at, created_by, updated_by
            ) VALUES (
                :id, :name, :display_name, :description, :level, :category,
                :is_system_role, :is_active, NULL, 'global', NULL,
                :created_at, :updated_at, 'alembic:20260408_phase3_role_redefinition',
                'alembic:20260408_phase3_role_redefinition'
            )
            """
        ),
        {
            "id": new_role_id,
            "name": role_name,
            "display_name": role_definition["display_name"],
            "description": role_definition["description"],
            "level": role_definition["level"],
            "category": role_definition["category"],
            "is_system_role": True,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        },
    )
    return new_role_id


def _reassign_user_roles(
    connection: sa.engine.Connection,
    *,
    target_role_ids: dict[str, str],
    now: datetime,
) -> None:
    rows = (
        connection.execute(
            sa.text(
                """
                SELECT ura.id, ura.user_id, ura.role_id, r.name AS role_name
                FROM user_role_assignments AS ura
                JOIN roles AS r ON r.id = ura.role_id
                WHERE ura.is_active = true
                """
            )
        )
        .mappings()
        .all()
    )

    for row in rows:
        role_name = str(row["role_name"])
        target_role_name = LEGACY_TO_TARGET_ROLE_NAME.get(role_name)
        if target_role_name is None:
            continue

        target_role_id = target_role_ids[target_role_name]
        if str(row["role_id"]) == target_role_id:
            continue

        duplicate_exists = connection.execute(
            sa.text(
                """
                SELECT 1
                FROM user_role_assignments
                WHERE user_id = :user_id
                  AND role_id = :role_id
                  AND is_active = true
                LIMIT 1
                """
            ),
            {
                "user_id": str(row["user_id"]),
                "role_id": target_role_id,
            },
        ).scalar_one_or_none()

        if duplicate_exists:
            connection.execute(
                sa.text(
                    """
                    UPDATE user_role_assignments
                    SET is_active = false,
                        updated_at = :updated_at
                    WHERE id = :assignment_id
                    """
                ),
                {
                    "assignment_id": str(row["id"]),
                    "updated_at": now,
                },
            )
            continue

        connection.execute(
            sa.text(
                """
                UPDATE user_role_assignments
                SET role_id = :target_role_id,
                    updated_at = :updated_at
                WHERE id = :assignment_id
                """
            ),
            {
                "target_role_id": target_role_id,
                "assignment_id": str(row["id"]),
                "updated_at": now,
            },
        )


def _rename_admin_role_if_needed(
    connection: sa.engine.Connection,
    *,
    now: datetime,
) -> None:
    roles = _roles_by_name(connection)
    if "admin" not in roles or "system_admin" in roles:
        return

    definition = TARGET_ROLE_DEFINITIONS["system_admin"]
    connection.execute(
        sa.text(
            """
            UPDATE roles
            SET name = 'system_admin',
                display_name = :display_name,
                description = :description,
                level = :level,
                category = :category,
                is_system_role = true,
                is_active = true,
                scope = 'global',
                scope_id = NULL,
                updated_at = :updated_at,
                updated_by = 'alembic:20260408_phase3_role_redefinition'
            WHERE name = 'admin'
            """
        ),
        {
            "display_name": definition["display_name"],
            "description": definition["description"],
            "level": definition["level"],
            "category": definition["category"],
            "updated_at": now,
        },
    )


def _deactivate_legacy_roles(connection: sa.engine.Connection, *, now: datetime) -> None:
    connection.execute(
        sa.text(
            """
            UPDATE roles
            SET is_active = false,
                updated_at = :updated_at,
                updated_by = 'alembic:20260408_phase3_role_redefinition'
            WHERE name IN (
                'manager', 'user', 'asset_manager', 'project_manager', 'auditor'
            )
            """
        ),
        {"updated_at": now},
    )


def _apply_role_redefinition(connection: sa.engine.Connection) -> None:
    if not _table_exists(connection, "roles") or not _table_exists(
        connection, "user_role_assignments"
    ):
        return

    now = _utcnow_naive()
    _rename_admin_role_if_needed(connection, now=now)

    target_role_ids = {
        role_name: _upsert_target_role(connection, role_name=role_name, now=now)
        for role_name in TARGET_ROLE_DEFINITIONS
    }
    _reassign_user_roles(connection, target_role_ids=target_role_ids, now=now)
    _deactivate_legacy_roles(connection, now=now)


def upgrade() -> None:
    connection = op.get_bind()
    _apply_role_redefinition(connection)


def downgrade() -> None:
    # No automatic rollback for role migration; keep data as-is.
    return None
