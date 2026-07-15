"""backfill ledger authorization

Revision ID: 20260710_ledger_authorization
Revises: 20260706_operations_ledger_foundation
Create Date: 2026-07-10
"""

from __future__ import annotations

from collections.abc import Sequence
from copy import deepcopy
from datetime import UTC, datetime

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260710_ledger_authorization"
down_revision: str | Sequence[str] | None = "20260706_operations_ledger_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ALLOW_ALL: dict[str, object] = {"==": [1, 1]}

_POLICY_RULES: tuple[tuple[str, tuple[str, ...], dict[str, object]], ...] = (
    ("platform_admin", ("create", "read", "update", "delete"), _ALLOW_ALL),
    ("asset_owner_operator", ("create", "read", "update", "delete"), _ALLOW_ALL),
    ("asset_manager_operator", ("create", "read", "update", "delete"), _ALLOW_ALL),
    ("dual_party_viewer", ("read",), _ALLOW_ALL),
    ("project_manager_operator", ("read",), _ALLOW_ALL),
    ("audit_viewer", ("read",), _ALLOW_ALL),
    ("no_data_access", ("create", "read", "update", "delete"), _ALLOW_ALL),
)

_PERMISSIONS: tuple[tuple[str, str, str, str], ...] = (
    (
        "permission:ledger:create",
        "create",
        "创建经营台账",
        "创建经营台账收付流水与费用台账",
    ),
    (
        "permission:ledger:update",
        "update",
        "更新经营台账",
        "更新经营台账分摊、跟进与服务费",
    ),
)


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _rule_id(policy_name: str, action: str) -> str:
    return f"backfill_20260710_rule_{policy_name}_ledger_{action}"


def upgrade() -> None:
    bind = op.get_bind()
    now = _utcnow_naive()
    policy_table = sa.table(
        "abac_policies",
        sa.column("id", sa.String()),
        sa.column("name", sa.String()),
    )
    rule_table = sa.table(
        "abac_policy_rules",
        sa.column("id", sa.String()),
        sa.column("policy_id", sa.String()),
        sa.column("resource_type", sa.String()),
        sa.column(
            "action",
            postgresql.ENUM(
                "create",
                "read",
                "list",
                "update",
                "delete",
                "export",
                name="abac_action",
                create_type=False,
            ),
        ),
        sa.column("condition_expr", sa.JSON()),
        sa.column("field_mask", sa.JSON()),
    )

    for policy_name, actions, condition in _POLICY_RULES:
        policy_id = bind.execute(
            sa.select(policy_table.c.id)
            .where(policy_table.c.name == policy_name)
            .limit(1)
        ).scalar_one_or_none()
        if policy_id is None:
            raise RuntimeError(
                f"missing ABAC policy required for ledger: {policy_name}"
            )
        for action in actions:
            rule_id = _rule_id(policy_name, action)
            exists = bind.execute(
                sa.select(sa.literal(1))
                .select_from(rule_table)
                .where(rule_table.c.id == rule_id)
                .limit(1)
            ).scalar_one_or_none()
            if exists is not None:
                continue
            bind.execute(
                rule_table.insert().values(
                    id=rule_id,
                    policy_id=policy_id,
                    resource_type="ledger",
                    action=action,
                    condition_expr=deepcopy(condition),
                    field_mask=None,
                )
            )

    for permission_id, action, display_name, description in _PERMISSIONS:
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
                    'ledger',
                    CAST(:action AS varchar),
                    TRUE,
                    FALSE,
                    :now,
                    :now
                WHERE NOT EXISTS (
                    SELECT 1 FROM permissions
                    WHERE name = CAST(:permission_name AS varchar)
                       OR (resource = 'ledger' AND action = CAST(:action AS varchar))
                )
                """
            ),
            {
                "permission_id": permission_id,
                "permission_name": f"ledger:{action}",
                "display_name": display_name,
                "description": description,
                "action": action,
                "now": now,
            },
        )
        permission_exists = bind.execute(
            sa.text("SELECT 1 FROM permissions WHERE id = :permission_id"),
            {"permission_id": permission_id},
        ).scalar_one_or_none()
        if permission_exists is None:
            raise RuntimeError(
                "ledger permission already exists under an unexpected id: "
                f"ledger:{action}"
            )

    bind.execute(
        sa.text(
            """
            INSERT INTO role_permissions (role_id, permission_id, created_at)
            SELECT r.id, p.id, :now
            FROM roles r
            JOIN permissions p
              ON p.id IN ('permission:ledger:create', 'permission:ledger:update')
            WHERE r.name IN ('system_admin', 'ops_admin', 'executive')
              AND NOT EXISTS (
                  SELECT 1 FROM role_permissions rp
                  WHERE rp.role_id = r.id AND rp.permission_id = p.id
              )
            """
        ),
        {"now": now},
    )


def downgrade() -> None:
    bind = op.get_bind()
    rule_ids = [
        _rule_id(policy_name, action)
        for policy_name, actions, _condition in _POLICY_RULES
        for action in actions
    ]
    bind.execute(
        sa.text(
            """
            DELETE FROM role_permissions
            WHERE permission_id IN (
                'permission:ledger:create',
                'permission:ledger:update'
            )
            """
        )
    )
    bind.execute(
        sa.text(
            """
            DELETE FROM permissions
            WHERE id IN (
                'permission:ledger:create',
                'permission:ledger:update'
            )
            """
        )
    )
    rule_table = sa.table("abac_policy_rules", sa.column("id", sa.String()))
    bind.execute(rule_table.delete().where(rule_table.c.id.in_(rule_ids)))
