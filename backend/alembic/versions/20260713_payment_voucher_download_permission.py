"""payment voucher download and ledger read permissions

Revision ID: 20260713_payment_voucher_download_permission
Revises: 20260713_payment_voucher_attachments
Create Date: 2026-07-13
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op

revision: str = "20260713_payment_voucher_download_permission"
down_revision: str | Sequence[str] | None = "20260713_payment_voucher_attachments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_POLICY_NAMES = (
    "platform_admin",
    "asset_owner_operator",
    "asset_manager_operator",
    "dual_party_viewer",
    "project_manager_operator",
    "audit_viewer",
    "no_data_access",
)
_RULE_SPEC = dict(resource_type="ledger_voucher", action="read")
_PERMISSION_ID = "permission:ledger_voucher:read"
_LEDGER_READ_PERMISSION_ID = "permission:ledger:read"


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def upgrade() -> None:
    bind = op.get_bind()
    now = _utcnow_naive()
    for policy_name in _POLICY_NAMES:
        policy_id = bind.execute(
            sa.text("SELECT id FROM abac_policies WHERE name = :name LIMIT 1"),
            {"name": policy_name},
        ).scalar_one_or_none()
        if policy_id is None:
            raise RuntimeError(
                f"missing ABAC policy required for voucher download: {policy_name}"
            )
        rule_id = f"backfill_20260713_rule_{policy_name}_ledger_voucher_read"
        bind.execute(
            sa.text(
                """
                INSERT INTO abac_policy_rules (
                    id, policy_id, resource_type, action, condition_expr, field_mask
                )
                SELECT
                    :rule_id, :policy_id, :resource_type,
                    CAST(:action AS abac_action), CAST(:condition_expr AS jsonb), NULL
                WHERE NOT EXISTS (
                    SELECT 1 FROM abac_policy_rules WHERE id = :rule_id
                )
                """
            ),
            {
                "rule_id": rule_id,
                "policy_id": policy_id,
                "resource_type": _RULE_SPEC["resource_type"],
                "action": _RULE_SPEC["action"],
                "condition_expr": json.dumps({"==": [1, 1]}),
            },
        )

    bind.execute(
        sa.text(
            """
            INSERT INTO permissions (
                id, name, display_name, description, resource, action,
                is_system_permission, requires_approval, created_at, updated_at
            )
            SELECT
                :permission_id, 'ledger_voucher:read', '下载经营收付流水凭证',
                '下载经营收付流水凭证并记录审计证据', 'ledger_voucher', 'read',
                TRUE, FALSE, :now, :now
            WHERE NOT EXISTS (
                SELECT 1 FROM permissions
                WHERE name = 'ledger_voucher:read'
                   OR (resource = 'ledger_voucher' AND action = 'read')
            )
            """
        ),
        {"permission_id": _PERMISSION_ID, "now": now},
    )
    permission_exists = bind.execute(
        sa.text("SELECT 1 FROM permissions WHERE id = :permission_id"),
        {"permission_id": _PERMISSION_ID},
    ).scalar_one_or_none()
    if permission_exists is None:
        raise RuntimeError(
            "ledger_voucher:read permission exists under an unexpected id"
        )
    bind.execute(
        sa.text(
            """
            INSERT INTO permissions (
                id, name, display_name, description, resource, action,
                is_system_permission, requires_approval, created_at, updated_at
            )
            SELECT
                :permission_id, 'ledger:read', '查看经营台账',
                '查看经营台账与收付流水', 'ledger', 'read',
                TRUE, FALSE, :now, :now
            WHERE NOT EXISTS (
                SELECT 1 FROM permissions
                WHERE name = 'ledger:read'
                   OR (resource = 'ledger' AND action = 'read')
            )
            """
        ),
        {"permission_id": _LEDGER_READ_PERMISSION_ID, "now": now},
    )
    ledger_read_exists = bind.execute(
        sa.text("SELECT 1 FROM permissions WHERE id = :permission_id"),
        {"permission_id": _LEDGER_READ_PERMISSION_ID},
    ).scalar_one_or_none()
    if ledger_read_exists is None:
        raise RuntimeError("ledger:read permission exists under an unexpected id")
    bind.execute(
        sa.text(
            """
            INSERT INTO role_permissions (role_id, permission_id, created_at)
            SELECT r.id, p.id, :now
            FROM roles AS r
            JOIN permissions AS p
              ON p.id IN ('permission:ledger:read', 'permission:ledger_voucher:read')
            WHERE r.name IN (
                'system_admin', 'ops_admin', 'reviewer', 'executive', 'viewer'
            )
              AND NOT EXISTS (
                  SELECT 1 FROM role_permissions AS rp
                  WHERE rp.role_id = r.id AND rp.permission_id = p.id
              )
            """
        ),
        {"now": now},
    )


def downgrade() -> None:
    raise RuntimeError("voucher download permission migration is not downgraded")
