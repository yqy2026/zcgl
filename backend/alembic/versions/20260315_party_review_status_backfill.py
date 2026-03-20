"""backfill rejected party review status to draft

Revision ID: 20260315_party_review_status_backfill
Revises: 20260312_party_soft_delete_review_log
Create Date: 2026-03-15 10:20:00.000000
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260315_party_review_status_backfill"
down_revision: str | None = "20260312_party_soft_delete_review_log"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.execute("UPDATE parties SET review_status = 'draft' WHERE review_status = 'rejected'")


def downgrade() -> None:
    # Irreversible data repair. Keep downgrade as a no-op to avoid
    # reintroducing an invalid terminal status into the Party state machine.
    return None
