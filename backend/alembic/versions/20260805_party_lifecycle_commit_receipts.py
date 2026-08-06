"""Add durable receipts for Party lifecycle commits."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260805_party_lifecycle_commit_receipts"
down_revision: str | Sequence[str] | None = "20260804_user_party_scope_commit_receipts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "party_lifecycle_commits",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column(
            "party_id",
            sa.String(),
            sa.ForeignKey("parties.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "actor_id",
            sa.String(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("operation", sa.String(length=20), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("before_state", sa.JSON(), nullable=False),
        sa.Column("after_state", sa.JSON(), nullable=False),
        sa.Column("impact_summary", sa.JSON(), nullable=False),
        sa.Column("result_data", sa.JSON(), nullable=False),
        sa.Column("committed_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "party_id",
            "actor_id",
            "idempotency_key",
            name="uq_party_lifecycle_commit_request",
        ),
    )
    op.create_index(
        "ix_party_lifecycle_commits_party_id",
        "party_lifecycle_commits",
        ["party_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_party_lifecycle_commits_party_id",
        table_name="party_lifecycle_commits",
    )
    op.drop_table("party_lifecycle_commits")
