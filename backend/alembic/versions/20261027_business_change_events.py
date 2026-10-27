"""Persist business changes in the contract command transaction."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20261027_business_change_events"
down_revision = "20261027_contract_field_rules"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "business_change_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("target_type", sa.String(50), nullable=False),
        sa.Column("target_id", sa.String(36), nullable=False),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("before", postgresql.JSONB(), nullable=False),
        sa.Column("after", postgresql.JSONB(), nullable=False),
        sa.Column("reason", sa.Text()),
        sa.Column("actor_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("correlation_id", sa.String(100), nullable=False),
    )
    op.create_index(
        "ix_business_change_events_target_time",
        "business_change_events",
        ["target_type", "target_id", "occurred_at"],
    )
    op.create_index(
        "ix_business_change_events_correlation",
        "business_change_events",
        ["correlation_id"],
    )


def downgrade() -> None:
    raise RuntimeError("Business changes are audit facts; use a corrective migration")
