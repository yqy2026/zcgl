"""add party review fields

Revision ID: 20260311_party_review_fields
Revises: 20260311_req_ast_002_active_project_unique
Create Date: 2026-03-11 13:10:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260311_party_review_fields"
down_revision: str | None = "20260311_req_ast_002_active_project_unique"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "parties",
        sa.Column(
            "review_status",
            sa.String(length=50),
            nullable=False,
            server_default="draft",
            comment="审核状态",
        ),
    )
    op.add_column(
        "parties",
        sa.Column("review_by", sa.String(length=100), nullable=True, comment="审核人"),
    )
    op.add_column(
        "parties",
        sa.Column("reviewed_at", sa.DateTime(), nullable=True, comment="审核时间"),
    )
    op.add_column(
        "parties",
        sa.Column("review_reason", sa.Text(), nullable=True, comment="审核原因/驳回原因"),
    )


def downgrade() -> None:
    op.drop_column("parties", "review_reason")
    op.drop_column("parties", "reviewed_at")
    op.drop_column("parties", "review_by")
    op.drop_column("parties", "review_status")
