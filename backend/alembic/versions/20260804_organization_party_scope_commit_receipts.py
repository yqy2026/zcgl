"""Add durable receipts for Organization Party scope commits.

Preview state remains short-lived cache data. This migration only adds the
durable commit receipt and the dedicated permission required for the commit
endpoint.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op

revision: str = "20260804_organization_party_scope_commit_receipts"
down_revision: str | Sequence[str] | None = (
    "20260804_organization_party_scope_model_cutover"
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PERMISSION_NAME = "organization:manage_party_scope"


def _seed_permission(bind: sa.engine.Connection) -> str:
    permission_row = bind.execute(
        sa.text("SELECT id FROM permissions WHERE name = :name"),
        {"name": PERMISSION_NAME},
    ).first()
    if permission_row:
        return str(permission_row[0])

    permission_id = str(uuid.uuid4())
    now = datetime.now(UTC).replace(tzinfo=None)
    bind.execute(
        sa.text(
            """
            INSERT INTO permissions (
                id, name, display_name, description, resource, action,
                is_system_permission, requires_approval, max_level, conditions,
                created_at, updated_at, created_by, updated_by
            ) VALUES (
                :id, :name, :display_name, :description, :resource, :action,
                :is_system_permission, :requires_approval, :max_level, :conditions,
                :created_at, :updated_at, :created_by, :updated_by
            )
            """
        ),
        {
            "id": permission_id,
            "name": PERMISSION_NAME,
            "display_name": "管理组织主体范围",
            "description": "预览并提交组织代表主体范围变更",
            "resource": "organization",
            "action": "manage_party_scope",
            "is_system_permission": True,
            "requires_approval": False,
            "max_level": None,
            "conditions": None,
            "created_at": now,
            "updated_at": now,
            "created_by": "migration",
            "updated_by": "migration",
        },
    )
    return permission_id


def _assign_permission_to_roles(bind: sa.engine.Connection, permission_id: str) -> None:
    roles = bind.execute(
        sa.text(
            "SELECT id FROM roles "
            "WHERE lower(name) IN ('admin', 'system_admin', 'perm_admin')"
        )
    ).fetchall()
    now = datetime.now(UTC).replace(tzinfo=None)
    for (role_id,) in roles:
        existing = bind.execute(
            sa.text(
                """
                SELECT 1 FROM role_permissions
                WHERE role_id = :role_id AND permission_id = :permission_id
                """
            ),
            {"role_id": role_id, "permission_id": permission_id},
        ).first()
        if existing:
            continue
        bind.execute(
            sa.text(
                """
                INSERT INTO role_permissions (
                    role_id, permission_id, created_at, created_by
                ) VALUES (:role_id, :permission_id, :created_at, :created_by)
                """
            ),
            {
                "role_id": role_id,
                "permission_id": permission_id,
                "created_at": now,
                "created_by": "migration",
            },
        )


def upgrade() -> None:
    op.create_table(
        "organization_party_scope_commits",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column(
            "organization_id",
            sa.String(),
            sa.ForeignKey("organizations.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "actor_id",
            sa.String(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("proposal", sa.JSON(), nullable=False),
        sa.Column("before_scope", sa.JSON(), nullable=False),
        sa.Column("after_scope", sa.JSON(), nullable=False),
        sa.Column("impact_summary", sa.JSON(), nullable=False),
        sa.Column("result_data", sa.JSON(), nullable=False),
        sa.Column("committed_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "actor_id",
            "idempotency_key",
            name="uq_organization_party_scope_commit_request",
        ),
    )
    op.create_index(
        "ix_organization_party_scope_commits_organization_id",
        "organization_party_scope_commits",
        ["organization_id"],
    )

    bind = op.get_bind()
    permission_id = _seed_permission(bind)
    _assign_permission_to_roles(bind, permission_id)


def downgrade() -> None:
    bind = op.get_bind()
    permission_row = bind.execute(
        sa.text("SELECT id FROM permissions WHERE name = :name"),
        {"name": PERMISSION_NAME},
    ).first()
    if permission_row:
        permission_id = str(permission_row[0])
        bind.execute(
            sa.text("DELETE FROM role_permissions WHERE permission_id = :permission_id"),
            {"permission_id": permission_id},
        )
        bind.execute(
            sa.text("DELETE FROM permissions WHERE id = :permission_id"),
            {"permission_id": permission_id},
        )

    op.drop_index(
        "ix_organization_party_scope_commits_organization_id",
        table_name="organization_party_scope_commits",
    )
    op.drop_table("organization_party_scope_commits")
