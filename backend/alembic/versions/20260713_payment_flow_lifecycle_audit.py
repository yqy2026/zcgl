"""payment flow lifecycle and voucher audit

Revision ID: 20260713_payment_flow_lifecycle_audit
Revises: 20260710_ledger_authorization
Create Date: 2026-07-13
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260713_payment_flow_lifecycle_audit"
down_revision: str | Sequence[str] | None = "20260710_ledger_authorization"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _add_lifecycle_fields() -> None:
    op.add_column(
        "operational_payment_flows",
        sa.Column("corrected_from_flow_id", sa.String(), nullable=True),
    )
    op.add_column(
        "operational_payment_flows",
        sa.Column("status_changed_by", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "operational_payment_flows",
        sa.Column("status_changed_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "operational_payment_flows",
        sa.Column("status_change_reason", sa.Text(), nullable=True),
    )
    op.create_foreign_key(
        "fk_operational_payment_flow_corrected_from",
        "operational_payment_flows",
        "operational_payment_flows",
        ["corrected_from_flow_id"],
        ["flow_id"],
    )
    op.create_unique_constraint(
        "uq_operational_payment_flow_corrected_from",
        "operational_payment_flows",
        ["corrected_from_flow_id"],
    )
    op.create_check_constraint(
        "ck_operational_payment_flow_lifecycle_audit",
        "operational_payment_flows",
        "(status = 'active' AND status_changed_by IS NULL "
        "AND status_changed_at IS NULL AND status_change_reason IS NULL) OR "
        "(status IN ('voided', 'corrected') AND status_changed_by IS NOT NULL "
        "AND btrim(status_changed_by) <> '' AND status_changed_at IS NOT NULL "
        "AND status_change_reason IS NOT NULL "
        "AND btrim(status_change_reason) <> '')",
    )


def upgrade() -> None:
    _add_lifecycle_fields()


def downgrade() -> None:
    raise RuntimeError("payment flow lifecycle migration is not downgraded")
