"""Lock full managed-property sources in occupancy-report snapshots.

Revision ID: 20261102_report_full_scope_snapshot
Revises: 20261031_report_lines_receipts
Create Date: 2026-11-02
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20261102_report_full_scope_snapshot"
down_revision: str | None = "20261031_report_lines_receipts"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "monthly_occupancy_reports",
        sa.Column("full_scope_snapshot", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("monthly_occupancy_reports", "full_scope_snapshot")
