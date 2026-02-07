"""add asset extra fields and system admin permission

Revision ID: 20260206_add_asset_fields_and_system_admin_permission
Revises: 20260206_remove_legacy_role_and_asset_ownership_entity
Create Date: 2026-02-06 00:00:00.000000

"""

from collections.abc import Sequence
from datetime import datetime
import uuid

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "20260206_add_asset_fields_and_system_admin_permission"
down_revision: str | None = "20260206_remove_legacy_role_and_asset_ownership_entity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ADMIN_PERMISSION_NAME = "system:admin"
ADMIN_PERMISSION_RESOURCE = "system"
ADMIN_PERMISSION_ACTION = "admin"


def upgrade() -> None:
    # Add missing asset fields
    with op.batch_alter_table("assets") as batch_op:
        batch_op.add_column(
            sa.Column(
                "wuyang_project_name",
                sa.String(length=200),
                comment="五羊项目名称",
            )
        )
        batch_op.add_column(sa.Column("description", sa.Text(), comment="描述"))

    # Ensure system admin permission exists and assign to admin roles
    conn = op.get_bind()
    perm_row = conn.execute(
        sa.text("SELECT id FROM permissions WHERE name = :name"),
        {"name": ADMIN_PERMISSION_NAME},
    ).first()

    if perm_row:
        perm_id = perm_row[0]
    else:
        perm_id = str(uuid.uuid4())
        now = datetime.utcnow()
        conn.execute(
            sa.text(
                """
                INSERT INTO permissions (
                    id,
                    name,
                    display_name,
                    description,
                    resource,
                    action,
                    is_system_permission,
                    requires_approval,
                    max_level,
                    conditions,
                    created_at,
                    updated_at,
                    created_by,
                    updated_by
                ) VALUES (
                    :id,
                    :name,
                    :display_name,
                    :description,
                    :resource,
                    :action,
                    :is_system_permission,
                    :requires_approval,
                    :max_level,
                    :conditions,
                    :created_at,
                    :updated_at,
                    :created_by,
                    :updated_by
                )
                """
            ),
            {
                "id": perm_id,
                "name": ADMIN_PERMISSION_NAME,
                "display_name": "系统管理员",
                "description": "系统管理员全局权限",
                "resource": ADMIN_PERMISSION_RESOURCE,
                "action": ADMIN_PERMISSION_ACTION,
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

    roles = conn.execute(
        sa.text(
            "SELECT id, name FROM roles WHERE lower(name) IN ('admin', 'super_admin')"
        )
    ).fetchall()

    if roles:
        now = datetime.utcnow()
        for role_id, _role_name in roles:
            exists = conn.execute(
                sa.text(
                    """
                    SELECT 1 FROM role_permissions
                    WHERE role_id = :role_id AND permission_id = :permission_id
                    """
                ),
                {"role_id": role_id, "permission_id": perm_id},
            ).first()
            if exists:
                continue
            conn.execute(
                sa.text(
                    """
                    INSERT INTO role_permissions (
                        role_id,
                        permission_id,
                        created_at,
                        created_by
                    ) VALUES (
                        :role_id,
                        :permission_id,
                        :created_at,
                        :created_by
                    )
                    """
                ),
                {
                    "role_id": role_id,
                    "permission_id": perm_id,
                    "created_at": now,
                    "created_by": "migration",
                },
            )


def downgrade() -> None:
    conn = op.get_bind()
    perm_row = conn.execute(
        sa.text("SELECT id FROM permissions WHERE name = :name"),
        {"name": ADMIN_PERMISSION_NAME},
    ).first()
    if perm_row:
        perm_id = perm_row[0]
        conn.execute(
            sa.text("DELETE FROM role_permissions WHERE permission_id = :permission_id"),
            {"permission_id": perm_id},
        )
        conn.execute(
            sa.text("DELETE FROM permissions WHERE id = :permission_id"),
            {"permission_id": perm_id},
        )

    with op.batch_alter_table("assets") as batch_op:
        batch_op.drop_column("description")
        batch_op.drop_column("wuyang_project_name")
