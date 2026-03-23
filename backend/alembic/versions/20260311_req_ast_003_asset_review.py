"""REQ-AST-003: add asset review logs and rename rejected status to reversed.

Revision ID: 20260311_req_ast_003_asset_review
Revises: 20260311_party_review_fields
Create Date: 2026-03-11 15:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260311_req_ast_003_asset_review"
down_revision: str | None = "20260311_party_review_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "asset_review_logs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("asset_id", sa.String(), nullable=False, comment="关联资产 ID"),
        sa.Column(
            "action",
            sa.String(length=20),
            nullable=False,
            comment="动作：submit/approve/reject/reverse/resubmit",
        ),
        sa.Column("from_status", sa.String(length=20), nullable=False),
        sa.Column("to_status", sa.String(length=20), nullable=False),
        sa.Column("operator", sa.String(length=100), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "context",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="附加上下文信息",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_asset_review_logs_asset_id",
        "asset_review_logs",
        ["asset_id"],
        unique=False,
    )
    op.execute(
        "UPDATE assets SET review_status = 'reversed' WHERE review_status = 'rejected'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE assets SET review_status = 'rejected' WHERE review_status = 'reversed'"
    )
    op.drop_index("ix_asset_review_logs_asset_id", table_name="asset_review_logs")
    op.drop_table("asset_review_logs")
