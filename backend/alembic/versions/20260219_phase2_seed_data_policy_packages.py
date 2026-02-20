"""phase2_seed_data_policy_packages

Revision ID: 20260219_phase2_seed_data_policy_packages
Revises: 20260219_phase2_add_party_columns_step1
Create Date: 2026-02-19 21:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260219_phase2_seed_data_policy_packages"
down_revision: str | None = "20260219_phase2_add_party_columns_step1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


POLICY_SEEDS: list[dict[str, object]] = [
    {
        "policy_id": "seed_policy_platform_admin",
        "rule_id": "seed_rule_platform_admin_asset_list",
        "name": "platform_admin",
        "effect": "allow",
        "priority": 10,
        "resource_type": "asset",
        "action": "list",
    },
    {
        "policy_id": "seed_policy_asset_owner_operator",
        "rule_id": "seed_rule_asset_owner_operator_asset_read",
        "name": "asset_owner_operator",
        "effect": "allow",
        "priority": 20,
        "resource_type": "asset",
        "action": "read",
    },
    {
        "policy_id": "seed_policy_asset_manager_operator",
        "rule_id": "seed_rule_asset_manager_operator_asset_update",
        "name": "asset_manager_operator",
        "effect": "allow",
        "priority": 30,
        "resource_type": "asset",
        "action": "update",
    },
    {
        "policy_id": "seed_policy_dual_party_viewer",
        "rule_id": "seed_rule_dual_party_viewer_asset_list",
        "name": "dual_party_viewer",
        "effect": "allow",
        "priority": 40,
        "resource_type": "asset",
        "action": "list",
    },
    {
        "policy_id": "seed_policy_project_manager_operator",
        "rule_id": "seed_rule_project_manager_operator_project_update",
        "name": "project_manager_operator",
        "effect": "allow",
        "priority": 50,
        "resource_type": "project",
        "action": "update",
    },
    {
        "policy_id": "seed_policy_audit_viewer",
        "rule_id": "seed_rule_audit_viewer_asset_read",
        "name": "audit_viewer",
        "effect": "allow",
        "priority": 60,
        "resource_type": "asset",
        "action": "read",
    },
    {
        "policy_id": "seed_policy_no_data_access",
        "rule_id": "seed_rule_no_data_access_asset_list",
        "name": "no_data_access",
        "effect": "deny",
        "priority": 5,
        "resource_type": "asset",
        "action": "list",
    },
]


def upgrade() -> None:
    """Seed baseline data-policy packages for role binding."""
    bind = op.get_bind()
    now = _utcnow_naive()

    policy_table = sa.table(
        "abac_policies",
        sa.column("id", sa.String()),
        sa.column("name", sa.String()),
        sa.column(
            "effect",
            postgresql.ENUM("allow", "deny", name="abac_effect", create_type=False),
        ),
        sa.column("priority", sa.Integer()),
        sa.column("enabled", sa.Boolean()),
        sa.column("created_at", sa.DateTime()),
        sa.column("updated_at", sa.DateTime()),
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

    for seed in POLICY_SEEDS:
        policy_exists = bind.execute(
            sa.select(sa.literal(1))
            .select_from(policy_table)
            .where(policy_table.c.name == seed["name"])
            .limit(1)
        ).scalar_one_or_none()

        if policy_exists is None:
            bind.execute(
                policy_table.insert().values(
                    id=seed["policy_id"],
                    name=seed["name"],
                    effect=seed["effect"],
                    priority=seed["priority"],
                    enabled=True,
                    created_at=now,
                    updated_at=now,
                )
            )

        rule_exists = bind.execute(
            sa.select(sa.literal(1))
            .select_from(rule_table)
            .where(rule_table.c.id == seed["rule_id"])
            .limit(1)
        ).scalar_one_or_none()
        if rule_exists is not None:
            continue

        policy_id = bind.execute(
            sa.select(policy_table.c.id)
            .where(policy_table.c.name == seed["name"])
            .limit(1)
        ).scalar_one_or_none()
        if policy_id is None:
            continue

        bind.execute(
            rule_table.insert().values(
                id=seed["rule_id"],
                policy_id=policy_id,
                resource_type=seed["resource_type"],
                action=seed["action"],
                condition_expr={"==": [1, 1]},
                field_mask=None,
            )
        )


def downgrade() -> None:
    """Remove seeded baseline data-policy packages."""
    bind = op.get_bind()
    policy_ids = [str(seed["policy_id"]) for seed in POLICY_SEEDS]
    rule_ids = [str(seed["rule_id"]) for seed in POLICY_SEEDS]

    rule_table = sa.table(
        "abac_policy_rules",
        sa.column("id", sa.String()),
        sa.column("policy_id", sa.String()),
    )
    policy_table = sa.table(
        "abac_policies",
        sa.column("id", sa.String()),
        sa.column("name", sa.String()),
    )

    bind.execute(rule_table.delete().where(rule_table.c.id.in_(rule_ids)))
    bind.execute(policy_table.delete().where(policy_table.c.id.in_(policy_ids)))
