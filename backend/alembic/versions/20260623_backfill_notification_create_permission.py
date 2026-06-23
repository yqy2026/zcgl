"""backfill notification create permission

Revision ID: 20260623_notification_create_perm
Revises: 20260620_property_certificate_attachments_asset_code
Create Date: 2026-06-23
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260623_notification_create_perm"
down_revision: str | Sequence[str] | None = (
    "20260620_property_certificate_attachments_asset_code"
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PERMISSION_ID = "permission:notification:create"
PERMISSION_NAME = "notification:create"


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(
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
                created_at,
                updated_at
            )
            SELECT
                CAST(:permission_id AS varchar),
                CAST(:permission_name AS varchar),
                '创建系统通知',
                '创建内容中立的系统通知',
                'notification',
                'create',
                TRUE,
                FALSE,
                NOW(),
                NOW()
            WHERE NOT EXISTS (
                SELECT 1 FROM permissions
                WHERE name = CAST(:permission_name AS varchar)
                   OR (resource = 'notification' AND action = 'create')
            )
            """
        ),
        {"permission_id": PERMISSION_ID, "permission_name": PERMISSION_NAME},
    )
    bind.execute(
        sa.text(
            """
            INSERT INTO role_permissions (role_id, permission_id, created_at)
            SELECT r.id, p.id, NOW()
            FROM roles r
            JOIN permissions p
              ON p.resource = 'notification'
             AND p.action = 'create'
            WHERE r.name IN ('system_admin', 'ops_admin')
              AND NOT EXISTS (
                  SELECT 1
                  FROM role_permissions rp
                  WHERE rp.role_id = r.id
                    AND rp.permission_id = p.id
              )
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            DELETE FROM role_permissions
            WHERE permission_id IN (
                SELECT id FROM permissions
                WHERE resource = 'notification' AND action = 'create'
            )
            """
        )
    )
    bind.execute(
        sa.text(
            """
            DELETE FROM permissions
            WHERE resource = 'notification' AND action = 'create'
            """
        )
    )
