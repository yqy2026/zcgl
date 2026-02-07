"""add unified permission_grants and backfill legacy grants

Revision ID: 20260207_unify_permission_grants
Revises: 4f9b3b2d6e91
Create Date: 2026-02-07 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260207_unify_permission_grants"
down_revision: str | None = "4f9b3b2d6e91"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _table_exists(conn: sa.Connection, table_name: str) -> bool:
    inspector = sa.inspect(conn)
    return inspector.has_table(table_name)


def _create_permission_grants_table() -> None:
    op.create_table(
        "permission_grants",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("permission_id", sa.String(), nullable=False),
        sa.Column("grant_type", sa.String(length=50), nullable=False, server_default="direct"),
        sa.Column("effect", sa.String(length=10), nullable=False, server_default="allow"),
        sa.Column("scope", sa.String(length=50), nullable=False, server_default="global"),
        sa.Column("scope_id", sa.String(), nullable=True),
        sa.Column("conditions", sa.JSON(), nullable=True),
        sa.Column("starts_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("source_type", sa.String(length=50), nullable=True),
        sa.Column("source_id", sa.String(), nullable=True),
        sa.Column("granted_by", sa.String(length=100), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_by", sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_permission_grants_user_id",
        "permission_grants",
        ["user_id"],
    )
    op.create_index(
        "ix_permission_grants_permission_id",
        "permission_grants",
        ["permission_id"],
    )
    op.create_index(
        "ix_permission_grants_scope",
        "permission_grants",
        ["scope"],
    )
    op.create_index(
        "ix_permission_grants_scope_id",
        "permission_grants",
        ["scope_id"],
    )
    op.create_index(
        "ix_permission_grants_is_active",
        "permission_grants",
        ["is_active"],
    )
    op.create_index(
        "ix_permission_grants_source_type",
        "permission_grants",
        ["source_type"],
    )
    op.create_index(
        "ix_permission_grants_source_id",
        "permission_grants",
        ["source_id"],
    )
    op.create_index(
        "ix_permission_grants_expires_at",
        "permission_grants",
        ["expires_at"],
    )
    op.create_index(
        "ix_permission_grants_starts_at",
        "permission_grants",
        ["starts_at"],
    )
    op.create_index(
        "ux_permission_grants_source_permission",
        "permission_grants",
        ["source_type", "source_id", "permission_id"],
        unique=True,
    )


def _backfill_from_resource_permissions(conn: sa.Connection) -> None:
    if not _table_exists(conn, "resource_permissions"):
        return

    conn.execute(
        sa.text(
            """
            INSERT INTO permission_grants (
                id, user_id, permission_id, grant_type, effect, scope, scope_id, conditions,
                starts_at, expires_at, priority, is_active, source_type, source_id,
                granted_by, reason, created_at, updated_at
            )
            SELECT
                concat('rp', chr(58), rp.id, chr(58), 'direct') AS id,
                rp.user_id,
                rp.permission_id,
                'resource',
                'allow',
                CASE WHEN rp.resource_id IS NULL THEN 'global' ELSE rp.resource_type END,
                rp.resource_id,
                rp.conditions,
                rp.granted_at,
                rp.expires_at,
                100,
                rp.is_active,
                'resource_permission',
                rp.id,
                rp.granted_by,
                rp.reason,
                COALESCE(rp.created_at, CURRENT_TIMESTAMP),
                COALESCE(rp.updated_at, CURRENT_TIMESTAMP)
            FROM resource_permissions rp
            WHERE rp.user_id IS NOT NULL
              AND rp.permission_id IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1 FROM permission_grants pg
                  WHERE pg.source_type = 'resource_permission'
                    AND pg.source_id = rp.id
                    AND pg.permission_id = rp.permission_id
              )
            """
        )
    )

    # 对历史仅存 permission_level 的记录，按权限级别展开为具体 action
    conn.execute(
        sa.text(
            """
            INSERT INTO permission_grants (
                id, user_id, permission_id, grant_type, effect, scope, scope_id, conditions,
                starts_at, expires_at, priority, is_active, source_type, source_id,
                granted_by, reason, created_at, updated_at
            )
            SELECT
                concat('rp', chr(58), rp.id, chr(58), p.action) AS id,
                rp.user_id,
                p.id,
                'resource',
                'allow',
                CASE WHEN rp.resource_id IS NULL THEN 'global' ELSE rp.resource_type END,
                rp.resource_id,
                rp.conditions,
                rp.granted_at,
                rp.expires_at,
                100,
                rp.is_active,
                'resource_permission',
                rp.id,
                rp.granted_by,
                rp.reason,
                COALESCE(rp.created_at, CURRENT_TIMESTAMP),
                COALESCE(rp.updated_at, CURRENT_TIMESTAMP)
            FROM resource_permissions rp
            JOIN permissions p
              ON p.resource = rp.resource_type
             AND (
                 (rp.permission_level = 'read' AND p.action IN ('read', 'view'))
                 OR (rp.permission_level = 'write' AND p.action IN ('read', 'view', 'write', 'create', 'update', 'edit'))
                 OR (rp.permission_level = 'delete' AND p.action IN ('read', 'view', 'write', 'create', 'update', 'edit', 'delete'))
                 OR (rp.permission_level = 'admin')
             )
            WHERE rp.user_id IS NOT NULL
              AND rp.permission_id IS NULL
              AND NOT EXISTS (
                  SELECT 1 FROM permission_grants pg
                  WHERE pg.source_type = 'resource_permission'
                    AND pg.source_id = rp.id
                    AND pg.permission_id = p.id
              )
            """
        )
    )


def _backfill_from_dynamic_tables(conn: sa.Connection) -> None:
    if _table_exists(conn, "dynamic_permissions"):
        conn.execute(
            sa.text(
                """
                INSERT INTO permission_grants (
                    id, user_id, permission_id, grant_type, effect, scope, scope_id, conditions,
                    starts_at, expires_at, priority, is_active, source_type, source_id,
                    granted_by, reason, created_at, updated_at
                )
                SELECT
                    concat('dp', chr(58), dp.id),
                    dp.user_id,
                    dp.permission_id,
                    COALESCE(dp.permission_type, 'dynamic'),
                    'allow',
                    COALESCE(dp.scope, 'global'),
                    dp.scope_id,
                    dp.conditions,
                    dp.assigned_at,
                    dp.expires_at,
                    100,
                    dp.is_active,
                    'dynamic_permission',
                    dp.id,
                    dp.assigned_by,
                    NULL,
                    COALESCE(dp.assigned_at, CURRENT_TIMESTAMP),
                    COALESCE(dp.assigned_at, CURRENT_TIMESTAMP)
                FROM dynamic_permissions dp
                WHERE NOT EXISTS (
                    SELECT 1 FROM permission_grants pg
                    WHERE pg.source_type = 'dynamic_permission'
                      AND pg.source_id = dp.id
                      AND pg.permission_id = dp.permission_id
                )
                """
            )
        )

    if _table_exists(conn, "temporary_permissions"):
        conn.execute(
            sa.text(
                """
                INSERT INTO permission_grants (
                    id, user_id, permission_id, grant_type, effect, scope, scope_id, conditions,
                    starts_at, expires_at, priority, is_active, source_type, source_id,
                    granted_by, reason, created_at, updated_at
                )
                SELECT
                    concat('tp', chr(58), tp.id),
                    tp.user_id,
                    tp.permission_id,
                    'temporary',
                    'allow',
                    COALESCE(tp.scope, 'global'),
                    tp.scope_id,
                    NULL,
                    tp.assigned_at,
                    tp.expires_at,
                    110,
                    tp.is_active,
                    'temporary_permission',
                    tp.id,
                    tp.assigned_by,
                    NULL,
                    COALESCE(tp.assigned_at, CURRENT_TIMESTAMP),
                    COALESCE(tp.assigned_at, CURRENT_TIMESTAMP)
                FROM temporary_permissions tp
                WHERE NOT EXISTS (
                    SELECT 1 FROM permission_grants pg
                    WHERE pg.source_type = 'temporary_permission'
                      AND pg.source_id = tp.id
                      AND pg.permission_id = tp.permission_id
                )
                """
            )
        )

    if _table_exists(conn, "conditional_permissions"):
        conn.execute(
            sa.text(
                """
                INSERT INTO permission_grants (
                    id, user_id, permission_id, grant_type, effect, scope, scope_id, conditions,
                    starts_at, expires_at, priority, is_active, source_type, source_id,
                    granted_by, reason, created_at, updated_at
                )
                SELECT
                    concat('cp', chr(58), cp.id),
                    cp.user_id,
                    cp.permission_id,
                    'conditional',
                    'allow',
                    COALESCE(cp.scope, 'global'),
                    cp.scope_id,
                    cp.conditions,
                    cp.assigned_at,
                    NULL,
                    120,
                    cp.is_active,
                    'conditional_permission',
                    cp.id,
                    cp.assigned_by,
                    NULL,
                    COALESCE(cp.assigned_at, CURRENT_TIMESTAMP),
                    COALESCE(cp.assigned_at, CURRENT_TIMESTAMP)
                FROM conditional_permissions cp
                WHERE NOT EXISTS (
                    SELECT 1 FROM permission_grants pg
                    WHERE pg.source_type = 'conditional_permission'
                      AND pg.source_id = cp.id
                      AND pg.permission_id = cp.permission_id
                )
                """
            )
        )


def _backfill_from_delegation(conn: sa.Connection) -> None:
    if not _table_exists(conn, "permission_delegations"):
        return

    conn.execute(
        sa.text(
            """
            INSERT INTO permission_grants (
                id, user_id, permission_id, grant_type, effect, scope, scope_id, conditions,
                starts_at, expires_at, priority, is_active, source_type, source_id,
                granted_by, reason, created_at, updated_at
            )
            SELECT
                concat('dg', chr(58), pd.id, chr(58), permission_ids.permission_id) AS id,
                pd.delegatee_id,
                p.id,
                'delegation',
                'allow',
                COALESCE(pd.scope, 'global'),
                pd.scope_id,
                pd.conditions,
                pd.starts_at,
                pd.ends_at,
                90,
                pd.is_active,
                'permission_delegation',
                pd.id,
                pd.delegator_id,
                pd.reason,
                COALESCE(pd.created_at, CURRENT_TIMESTAMP),
                COALESCE(pd.created_at, CURRENT_TIMESTAMP)
            FROM permission_delegations pd
            CROSS JOIN LATERAL (
                SELECT value::text AS permission_id
                FROM jsonb_array_elements_text(
                    CASE
                        WHEN jsonb_typeof(pd.permission_ids::jsonb) = 'array'
                            THEN pd.permission_ids::jsonb
                        ELSE '[]'::jsonb
                    END
                )
            ) permission_ids
            JOIN permissions p ON p.id = permission_ids.permission_id
            WHERE pd.delegatee_id IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1 FROM permission_grants pg
                  WHERE pg.source_type = 'permission_delegation'
                    AND pg.source_id = pd.id
                    AND pg.permission_id = p.id
              )
            """
        )
    )


def upgrade() -> None:
    conn = op.get_bind()
    if not _table_exists(conn, "permission_grants"):
        _create_permission_grants_table()

    _backfill_from_resource_permissions(conn)
    _backfill_from_dynamic_tables(conn)
    _backfill_from_delegation(conn)


def downgrade() -> None:
    conn = op.get_bind()
    if not _table_exists(conn, "permission_grants"):
        return

    op.drop_index("ux_permission_grants_source_permission", table_name="permission_grants")
    op.drop_index("ix_permission_grants_starts_at", table_name="permission_grants")
    op.drop_index("ix_permission_grants_expires_at", table_name="permission_grants")
    op.drop_index("ix_permission_grants_source_id", table_name="permission_grants")
    op.drop_index("ix_permission_grants_source_type", table_name="permission_grants")
    op.drop_index("ix_permission_grants_is_active", table_name="permission_grants")
    op.drop_index("ix_permission_grants_scope_id", table_name="permission_grants")
    op.drop_index("ix_permission_grants_scope", table_name="permission_grants")
    op.drop_index("ix_permission_grants_permission_id", table_name="permission_grants")
    op.drop_index("ix_permission_grants_user_id", table_name="permission_grants")
    op.drop_table("permission_grants")
