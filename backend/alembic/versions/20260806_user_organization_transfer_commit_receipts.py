"""Add durable receipts for human-user organization transfers."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260806_user_organization_transfer_commit_receipts"
down_revision: str | Sequence[str] | None = "20260805_party_lifecycle_commit_receipts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_organization_transfer_commits",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column(
            "user_id",
            sa.String(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "actor_id",
            sa.String(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "target_organization_id",
            sa.String(),
            sa.ForeignKey("organizations.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("proposal", sa.JSON(), nullable=False),
        sa.Column("before_scope", sa.JSON(), nullable=False),
        sa.Column("after_scope", sa.JSON(), nullable=False),
        sa.Column("impact_summary", sa.JSON(), nullable=False),
        sa.Column("result_data", sa.JSON(), nullable=False),
        sa.Column("committed_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "actor_id",
            "idempotency_key",
            name="uq_user_organization_transfer_commit_request",
        ),
    )
    op.create_index(
        "ix_user_organization_transfer_commits_user_id",
        "user_organization_transfer_commits",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_user_organization_transfer_commits_user_id",
        table_name="user_organization_transfer_commits",
    )
    op.drop_table("user_organization_transfer_commits")
