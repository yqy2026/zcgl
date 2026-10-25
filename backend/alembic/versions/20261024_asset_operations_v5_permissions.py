"""seed asset-operations v5 capability permissions

Revision ID: 20261024_asset_operations_v5_permissions
Revises: 20261023_asset_operations_v5_contracts
Create Date: 2026-10-24
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op

revision: str = "20261024_asset_operations_v5_permissions"
down_revision: str | Sequence[str] | None = "20261023_asset_operations_v5_contracts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PERMISSIONS: tuple[tuple[str, str, str], ...] = (
    ("read", "查看资产运营", "查看资产运营工作台、资产、合同及台账"),
    ("write", "维护资产运营", "维护资产单元、合同、租金、押金及生命周期"),
    ("report", "管理资产运营报送", "保存考核范围并提交或撤回报送"),
    ("archive", "管理资产运营档案", "上传、替换、下载及配对业务档案"),
    ("import", "管理资产运营导入", "校验、提交及撤销资产运营导入批次"),
)
BUILTIN_ROLE_NAMES: tuple[str, ...] = ("ops_admin", "system_admin")


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def upgrade() -> None:
    bind = op.get_bind()
    now = _utcnow_naive()
    existing_roles = set(
        bind.execute(
            sa.text(
                "SELECT name FROM roles WHERE name IN ('ops_admin', 'system_admin')"
            )
        ).scalars()
    )
    missing_roles = set(BUILTIN_ROLE_NAMES) - existing_roles
    if len(missing_roles) > 0:
        raise RuntimeError(
            "missing built-in roles required for asset-operations permissions: "
            + ", ".join(sorted(missing_roles))
        )

    for action, display_name, description in PERMISSIONS:
        permission_id = f"permission:asset_ops:{action}"
        permission_name = f"asset_ops:{action}"
        bind.execute(
            sa.text(
                """
                INSERT INTO permissions (
                    id, name, display_name, description, resource, action,
                    is_system_permission, requires_approval, created_at, updated_at
                )
                SELECT
                    CAST(:permission_id AS varchar),
                    CAST(:permission_name AS varchar),
                    CAST(:display_name AS varchar),
                    CAST(:description AS varchar),
                    'asset_ops',
                    CAST(:action AS varchar),
                    TRUE,
                    FALSE,
                    :now,
                    :now
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM permissions
                    WHERE name = CAST(:permission_name AS varchar)
                       OR (
                           resource = 'asset_ops'
                           AND action = CAST(:action AS varchar)
                       )
                )
                """
            ),
            {
                "permission_id": permission_id,
                "permission_name": permission_name,
                "display_name": display_name,
                "description": description,
                "action": action,
                "now": now,
            },
        )
        owned_id = bind.execute(
            sa.text(
                "SELECT id FROM permissions "
                "WHERE name = CAST(:permission_name AS varchar) "
                "AND resource = 'asset_ops' "
                "AND action = CAST(:action AS varchar)"
            ),
            {"permission_name": permission_name, "action": action},
        ).scalar_one_or_none()
        if owned_id != permission_id:
            raise RuntimeError(
                "asset-operations permission exists under an unexpected id: "
                + permission_name
            )

    bind.execute(
        sa.text(
            """
            INSERT INTO role_permissions (role_id, permission_id, created_at)
            SELECT r.id, p.id, :now
            FROM roles AS r
            CROSS JOIN permissions AS p
            WHERE r.name IN ('ops_admin', 'system_admin')
              AND p.id IN (
                  'permission:asset_ops:read',
                  'permission:asset_ops:write',
                  'permission:asset_ops:report',
                  'permission:asset_ops:archive',
                  'permission:asset_ops:import'
              )
              AND NOT EXISTS (
                  SELECT 1
                  FROM role_permissions AS rp
                  WHERE rp.role_id = r.id AND rp.permission_id = p.id
              )
            """
        ),
        {"now": now},
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            DELETE FROM role_permissions
            WHERE permission_id IN (
                'permission:asset_ops:read',
                'permission:asset_ops:write',
                'permission:asset_ops:report',
                'permission:asset_ops:archive',
                'permission:asset_ops:import'
            )
            """
        )
    )
    bind.execute(
        sa.text(
            """
            DELETE FROM permissions
            WHERE id IN (
                'permission:asset_ops:read',
                'permission:asset_ops:write',
                'permission:asset_ops:report',
                'permission:asset_ops:archive',
                'permission:asset_ops:import'
            )
            """
        )
    )
