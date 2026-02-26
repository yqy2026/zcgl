"""backfill_ownership_occupancy_policy_rules

Revision ID: 20260224_backfill_ownership_occupancy_policy_rules
Revises: 20260219_phase2_add_party_columns_step1
Create Date: 2026-02-24 09:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence
from copy import deepcopy
from datetime import UTC, datetime

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260224_backfill_ownership_occupancy_policy_rules"
down_revision: str | None = "20260219_phase2_add_party_columns_step1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


_ALLOW_ALL_CONDITION_EXPR: dict[str, object] = {"==": [1, 1]}
_DENY_ALL_CONDITION_EXPR: dict[str, object] = {"==": [1, 0]}

_OWNER_SCOPE_CONDITION_EXPR: dict[str, object] = {
    "if": [
        {
            "or": [
                {"!!": {"var": "resource.owner_party_id"}},
                {"!!": {"var": "resource.party_id"}},
            ]
        },
        {
            "or": [
                {
                    "in": [
                        {"var": "resource.owner_party_id"},
                        {"var": "subject.owner_party_ids"},
                    ]
                },
                {
                    "in": [
                        {"var": "resource.party_id"},
                        {"var": "subject.owner_party_ids"},
                    ]
                },
            ]
        },
        _DENY_ALL_CONDITION_EXPR,
    ]
}

_MANAGER_SCOPE_CONDITION_EXPR: dict[str, object] = {
    "if": [
        {
            "or": [
                {"!!": {"var": "resource.manager_party_id"}},
                {"!!": {"var": "resource.party_id"}},
            ]
        },
        {
            "or": [
                {
                    "in": [
                        {"var": "resource.manager_party_id"},
                        {"var": "subject.manager_party_ids"},
                    ]
                },
                {
                    "in": [
                        {"var": "resource.party_id"},
                        {"var": "subject.manager_party_ids"},
                    ]
                },
            ]
        },
        _DENY_ALL_CONDITION_EXPR,
    ]
}

_DUAL_SCOPE_CONDITION_EXPR: dict[str, object] = {
    "if": [
        {
            "or": [
                {"!!": {"var": "resource.owner_party_id"}},
                {"!!": {"var": "resource.manager_party_id"}},
                {"!!": {"var": "resource.party_id"}},
            ]
        },
        {
            "or": [
                {
                    "in": [
                        {"var": "resource.owner_party_id"},
                        {"var": "subject.owner_party_ids"},
                    ]
                },
                {
                    "in": [
                        {"var": "resource.manager_party_id"},
                        {"var": "subject.manager_party_ids"},
                    ]
                },
                {
                    "in": [
                        {"var": "resource.party_id"},
                        {"var": "subject.owner_party_ids"},
                    ]
                },
                {
                    "in": [
                        {"var": "resource.party_id"},
                        {"var": "subject.manager_party_ids"},
                    ]
                },
            ]
        },
        _DENY_ALL_CONDITION_EXPR,
    ]
}

_POLICY_CONDITION_EXPR_BY_NAME: dict[str, dict[str, object]] = {
    "platform_admin": _ALLOW_ALL_CONDITION_EXPR,
    "asset_owner_operator": _OWNER_SCOPE_CONDITION_EXPR,
    "asset_manager_operator": _MANAGER_SCOPE_CONDITION_EXPR,
    "dual_party_viewer": _DUAL_SCOPE_CONDITION_EXPR,
    "project_manager_operator": _MANAGER_SCOPE_CONDITION_EXPR,
    "audit_viewer": _DUAL_SCOPE_CONDITION_EXPR,
    "no_data_access": _ALLOW_ALL_CONDITION_EXPR,
}


def _condition_expr_for_policy(policy_name: str) -> dict[str, object]:
    return deepcopy(
        _POLICY_CONDITION_EXPR_BY_NAME.get(policy_name, _ALLOW_ALL_CONDITION_EXPR)
    )


_RW_ACTIONS = ("create", "read", "update", "delete")
_READ_ONLY_ACTIONS = ("read",)
_MISSING_RESOURCE_TYPES = ("ownership", "occupancy", "custom_field")


def _build_policy_seeds(
    *,
    policy_id: str,
    policy_name: str,
    effect: str,
    priority: int,
    resources: tuple[str, ...],
    actions: tuple[str, ...],
) -> list[dict[str, object]]:
    seeds: list[dict[str, object]] = []
    for resource in resources:
        for action in actions:
            seeds.append(
                {
                    "policy_id": policy_id,
                    "rule_id": f"seed_rule_{policy_name}_{resource}_{action}",
                    "name": policy_name,
                    "effect": effect,
                    "priority": priority,
                    "resource_type": resource,
                    "action": action,
                    "condition_expr": _condition_expr_for_policy(policy_name),
                }
            )
    return seeds


MISSING_RESOURCE_POLICY_SEEDS: list[dict[str, object]] = [
    *_build_policy_seeds(
        policy_id="seed_policy_platform_admin",
        policy_name="platform_admin",
        effect="allow",
        priority=10,
        resources=_MISSING_RESOURCE_TYPES,
        actions=_RW_ACTIONS,
    ),
    *_build_policy_seeds(
        policy_id="seed_policy_asset_owner_operator",
        policy_name="asset_owner_operator",
        effect="allow",
        priority=20,
        resources=_MISSING_RESOURCE_TYPES,
        actions=_RW_ACTIONS,
    ),
    *_build_policy_seeds(
        policy_id="seed_policy_asset_manager_operator",
        policy_name="asset_manager_operator",
        effect="allow",
        priority=30,
        resources=_MISSING_RESOURCE_TYPES,
        actions=_RW_ACTIONS,
    ),
    *_build_policy_seeds(
        policy_id="seed_policy_dual_party_viewer",
        policy_name="dual_party_viewer",
        effect="allow",
        priority=40,
        resources=_MISSING_RESOURCE_TYPES,
        actions=_READ_ONLY_ACTIONS,
    ),
    *_build_policy_seeds(
        policy_id="seed_policy_project_manager_operator",
        policy_name="project_manager_operator",
        effect="allow",
        priority=50,
        resources=_MISSING_RESOURCE_TYPES,
        actions=_READ_ONLY_ACTIONS,
    ),
    *_build_policy_seeds(
        policy_id="seed_policy_audit_viewer",
        policy_name="audit_viewer",
        effect="allow",
        priority=60,
        resources=_MISSING_RESOURCE_TYPES,
        actions=_READ_ONLY_ACTIONS,
    ),
    *_build_policy_seeds(
        policy_id="seed_policy_no_data_access",
        policy_name="no_data_access",
        effect="deny",
        priority=5,
        resources=_MISSING_RESOURCE_TYPES,
        actions=_RW_ACTIONS,
    ),
]


def upgrade() -> None:
    """Backfill ownership/occupancy ABAC rules for already-upgraded databases."""
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

    for seed in MISSING_RESOURCE_POLICY_SEEDS:
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
                condition_expr=seed["condition_expr"],
                field_mask=None,
            )
        )


def downgrade() -> None:
    """Rollback only ownership/occupancy rules inserted by this revision."""
    bind = op.get_bind()

    rule_ids = [str(seed["rule_id"]) for seed in MISSING_RESOURCE_POLICY_SEEDS]
    policy_ids = sorted({str(seed["policy_id"]) for seed in MISSING_RESOURCE_POLICY_SEEDS})

    rule_table = sa.table(
        "abac_policy_rules",
        sa.column("id", sa.String()),
        sa.column("policy_id", sa.String()),
    )
    policy_table = sa.table(
        "abac_policies",
        sa.column("id", sa.String()),
    )

    bind.execute(rule_table.delete().where(rule_table.c.id.in_(rule_ids)))

    remaining_rule_exists = (
        sa.select(sa.literal(1))
        .select_from(rule_table)
        .where(rule_table.c.policy_id == policy_table.c.id)
        .exists()
    )
    orphan_policy_ids = bind.execute(
        sa.select(policy_table.c.id).where(
            policy_table.c.id.in_(policy_ids),
            ~remaining_rule_exists,
        )
    ).scalars().all()
    if orphan_policy_ids:
        bind.execute(policy_table.delete().where(policy_table.c.id.in_(orphan_policy_ids)))
