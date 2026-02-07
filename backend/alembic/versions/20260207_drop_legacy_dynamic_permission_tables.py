"""drop legacy dynamic permission tables

Revision ID: 20260207_drop_legacy_dynamic_permission_tables
Revises: 20260207_unify_permission_grants
Create Date: 2026-02-07 00:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260207_drop_legacy_dynamic_permission_tables"
down_revision: str | None = "20260207_unify_permission_grants"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


LEGACY_DYNAMIC_TABLES = [
    "dynamic_permission_audit",
    "permission_delegations",
    "permission_requests",
    "permission_templates",
    "conditional_permissions",
    "temporary_permissions",
    "dynamic_permissions",
]


def _table_exists(conn: sa.Connection, table_name: str) -> bool:
    return sa.inspect(conn).has_table(table_name)


def upgrade() -> None:
    conn = op.get_bind()
    for table_name in LEGACY_DYNAMIC_TABLES:
        if _table_exists(conn, table_name):
            op.drop_table(table_name)


def downgrade() -> None:
    conn = op.get_bind()

    if not _table_exists(conn, "dynamic_permissions"):
        op.create_table(
            "dynamic_permissions",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("user_id", sa.String(), nullable=False),
            sa.Column("permission_id", sa.String(), nullable=False),
            sa.Column("permission_type", sa.String(), nullable=False),
            sa.Column("scope", sa.String(), nullable=False),
            sa.Column("scope_id", sa.String(), nullable=True),
            sa.Column("conditions", sa.JSON(), nullable=True),
            sa.Column("expires_at", sa.DateTime(), nullable=True),
            sa.Column("assigned_by", sa.String(), nullable=False),
            sa.Column("assigned_at", sa.DateTime(), nullable=False),
            sa.Column("revoked_by", sa.String(), nullable=True),
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.ForeignKeyConstraint(["assigned_by"], ["users.id"]),
            sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"]),
            sa.ForeignKeyConstraint(["revoked_by"], ["users.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _table_exists(conn, "temporary_permissions"):
        op.create_table(
            "temporary_permissions",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("user_id", sa.String(), nullable=False),
            sa.Column("permission_id", sa.String(), nullable=False),
            sa.Column("scope", sa.String(), nullable=False),
            sa.Column("scope_id", sa.String(), nullable=True),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("assigned_by", sa.String(), nullable=False),
            sa.Column("assigned_at", sa.DateTime(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.ForeignKeyConstraint(["assigned_by"], ["users.id"]),
            sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _table_exists(conn, "conditional_permissions"):
        op.create_table(
            "conditional_permissions",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("user_id", sa.String(), nullable=False),
            sa.Column("permission_id", sa.String(), nullable=False),
            sa.Column("scope", sa.String(), nullable=False),
            sa.Column("scope_id", sa.String(), nullable=True),
            sa.Column("conditions", sa.JSON(), nullable=False),
            sa.Column("assigned_by", sa.String(), nullable=False),
            sa.Column("assigned_at", sa.DateTime(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.ForeignKeyConstraint(["assigned_by"], ["users.id"]),
            sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _table_exists(conn, "permission_templates"):
        op.create_table(
            "permission_templates",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("permission_ids", sa.JSON(), nullable=False),
            sa.Column("scope", sa.String(), nullable=False),
            sa.Column("conditions", sa.JSON(), nullable=True),
            sa.Column("created_by", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _table_exists(conn, "permission_requests"):
        op.create_table(
            "permission_requests",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("user_id", sa.String(), nullable=False),
            sa.Column("permission_ids", sa.JSON(), nullable=False),
            sa.Column("scope", sa.String(), nullable=False),
            sa.Column("scope_id", sa.String(), nullable=True),
            sa.Column("reason", sa.Text(), nullable=False),
            sa.Column("requested_duration_hours", sa.String(), nullable=True),
            sa.Column("requested_conditions", sa.JSON(), nullable=True),
            sa.Column("status", sa.String(), nullable=False, server_default="pending"),
            sa.Column("approved_by", sa.String(), nullable=True),
            sa.Column("approved_at", sa.DateTime(), nullable=True),
            sa.Column("approval_comment", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["approved_by"], ["users.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _table_exists(conn, "permission_delegations"):
        op.create_table(
            "permission_delegations",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("delegator_id", sa.String(), nullable=False),
            sa.Column("delegatee_id", sa.String(), nullable=False),
            sa.Column("permission_ids", sa.JSON(), nullable=False),
            sa.Column("scope", sa.String(), nullable=False),
            sa.Column("scope_id", sa.String(), nullable=True),
            sa.Column("starts_at", sa.DateTime(), nullable=False),
            sa.Column("ends_at", sa.DateTime(), nullable=False),
            sa.Column("conditions", sa.JSON(), nullable=True),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["delegatee_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["delegator_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _table_exists(conn, "dynamic_permission_audit"):
        op.create_table(
            "dynamic_permission_audit",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("user_id", sa.String(), nullable=False),
            sa.Column("permission_id", sa.String(), nullable=False),
            sa.Column("action", sa.String(), nullable=False),
            sa.Column("permission_type", sa.String(), nullable=False),
            sa.Column("scope", sa.String(), nullable=False),
            sa.Column("scope_id", sa.String(), nullable=True),
            sa.Column("assigned_by", sa.String(), nullable=False),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("conditions", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["assigned_by"], ["users.id"]),
            sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
