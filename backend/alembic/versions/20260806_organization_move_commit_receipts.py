"""Add durable receipts for Organization hierarchy moves.

Revision ID: 20260806_organization_move_commit_receipts
Revises: 20260806_user_organization_transfer_commit_receipts
Create Date: 2026-08-06
"""

import sqlalchemy as sa

from alembic import op

revision = "20260806_organization_move_commit_receipts"
down_revision = "20260806_user_organization_transfer_commit_receipts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organization_move_commits",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column(
            "organization_id",
            sa.String(),
            sa.ForeignKey("organizations.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "target_parent_id",
            sa.String(),
            sa.ForeignKey("organizations.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "actor_id",
            sa.String(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
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
            "organization_id",
            "actor_id",
            "idempotency_key",
            name="uq_organization_move_commit_request",
        ),
    )
    op.create_index(
        "ix_organization_move_commits_organization_id",
        "organization_move_commits",
        ["organization_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_organization_move_commits_organization_id",
        table_name="organization_move_commits",
    )
    op.drop_table("organization_move_commits")
