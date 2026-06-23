"""drop orphan project review fields

Revision ID: 20260619_drop_project_review_fields
Revises: 20260618_backfill_ledger_frozen_attribution
Create Date: 2026-06-19
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260619_drop_project_review_fields"
down_revision: str | Sequence[str] | None = (
    "20260618_backfill_ledger_frozen_attribution"
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PROJECT_REVIEW_COLUMNS = (
    "review_status",
    "review_by",
    "reviewed_at",
    "review_reason",
)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("projects"):
        return

    existing_columns = {column["name"] for column in inspector.get_columns("projects")}
    for column_name in PROJECT_REVIEW_COLUMNS:
        if column_name in existing_columns:
            op.drop_column("projects", column_name)


def downgrade() -> None:
    raise RuntimeError("project review fields were retired and are not recreated")
