"""party soft delete + review log table

Revision ID: 20260312_party_soft_delete_review_log
Revises: 20260311_req_ast_003_asset_review
Create Date: 2026-03-12 20:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260312_party_soft_delete_review_log"
down_revision: str | None = "20260311_req_ast_003_asset_review"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # --- parties: add deleted_at ---
    op.add_column(
        "parties",
        sa.Column(
            "deleted_at",
            sa.DateTime(),
            nullable=True,
            comment="软删除时间",
        ),
    )

    # --- party_review_logs: new table (skip if exists) ---
    conn = op.get_bind()
    inspector = inspect(conn)
    if "party_review_logs" not in inspector.get_table_names():
        op.create_table(
            "party_review_logs",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column(
                "party_id",
                sa.String(),
                sa.ForeignKey("parties.id"),
                nullable=False,
                index=True,
                comment="关联主体 ID",
            ),
            sa.Column(
                "action",
                sa.String(length=20),
                nullable=False,
                comment="动作：submit/approve/reject",
            ),
            sa.Column(
                "from_status",
                sa.String(length=20),
                nullable=False,
                comment="变更前审核状态",
            ),
            sa.Column(
                "to_status",
                sa.String(length=20),
                nullable=False,
                comment="变更后审核状态",
            ),
            sa.Column(
                "operator",
                sa.String(length=100),
                nullable=True,
                comment="操作人",
            ),
            sa.Column(
                "reason",
                sa.Text(),
                nullable=True,
                comment="驳回原因",
            ),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
                comment="创建时间",
            ),
        )


def downgrade() -> None:
    op.drop_table("party_review_logs")
    op.drop_column("parties", "deleted_at")
