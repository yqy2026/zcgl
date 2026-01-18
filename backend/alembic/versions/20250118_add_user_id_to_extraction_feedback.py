"""add user_id to extraction_feedback

Revision ID: 20250118_add_user_id_feedback
Revises: 20250118_add_property_cert_tables
Create Date: 2025-01-18 15:00:00.000000

Security Fix: Add user_id field to extraction_feedback table for audit trail.

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20250118_add_user_id_feedback"
down_revision: str | None = "20250118_add_property_cert_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""

    # Add user_id column to extraction_feedback table
    op.add_column(
        "extraction_feedback",
        sa.Column(
            "user_id",
            sa.String,
            sa.ForeignKey("users.id"),
            nullable=True,
            comment="提交反馈的用户ID",
        ),
    )

    # Create index on user_id for performance
    op.create_index(
        "ix_extraction_feedback_user_id",
        "extraction_feedback",
        ["user_id"],
    )


def downgrade() -> None:
    """Downgrade schema."""

    # Drop index first
    op.drop_index("ix_extraction_feedback_user_id", table_name="extraction_feedback")

    # Drop column
    op.drop_column("extraction_feedback", "user_id")
