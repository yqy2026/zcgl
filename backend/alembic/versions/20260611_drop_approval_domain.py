"""drop retired approval workflow domain

Revision ID: 20260611_drop_approval_domain
Revises: 20260611_encrypt_party_contact_phone
Create Date: 2026-06-11 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260611_drop_approval_domain"
down_revision: str | None = "20260611_encrypt_party_contact_phone"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _table_exists(
    inspector: sa.engine.reflection.Inspector,
    table_name: str,
) -> bool:
    return inspector.has_table(table_name)


def _drop_approval_permissions(inspector: sa.engine.reflection.Inspector) -> None:
    bind = op.get_bind()

    if _table_exists(inspector, "abac_policy_rules"):
        bind.execute(
            sa.text(
                """
                DELETE FROM abac_policy_rules
                WHERE resource_type = 'approval'
                """
            )
        )

    if _table_exists(inspector, "resource_permissions"):
        bind.execute(
            sa.text(
                """
                DELETE FROM resource_permissions
                WHERE resource_type = 'approval'
                """
            )
        )

    if not _table_exists(inspector, "permissions"):
        return

    if _table_exists(inspector, "role_permissions"):
        bind.execute(
            sa.text(
                """
                DELETE FROM role_permissions
                WHERE permission_id IN (
                    SELECT id FROM permissions WHERE resource = 'approval'
                )
                """
            )
        )

    if _table_exists(inspector, "permission_grants"):
        bind.execute(
            sa.text(
                """
                DELETE FROM permission_grants
                WHERE permission_id IN (
                    SELECT id FROM permissions WHERE resource = 'approval'
                )
                """
            )
        )

    bind.execute(sa.text("DELETE FROM permissions WHERE resource = 'approval'"))


def _drop_approval_notifications(inspector: sa.engine.reflection.Inspector) -> None:
    if not _table_exists(inspector, "notifications"):
        return

    op.get_bind().execute(
        sa.text(
            """
            DELETE FROM notifications
            WHERE type = 'approval_pending'
               OR related_entity_type = 'approval'
            """
        )
    )


def upgrade() -> None:
    """Remove the retired approval workflow runtime tables and RBAC entries."""
    inspector = sa.inspect(op.get_bind())
    _drop_approval_permissions(inspector)
    _drop_approval_notifications(inspector)

    for table_name in (
        "approval_action_logs",
        "approval_task_snapshots",
        "approval_instances",
    ):
        if _table_exists(inspector, table_name):
            op.drop_table(table_name)


def downgrade() -> None:
    """Do not recreate the retired approval workflow domain."""
    raise RuntimeError("REQ-APR-001 approval workflow was removed from the MVP")
