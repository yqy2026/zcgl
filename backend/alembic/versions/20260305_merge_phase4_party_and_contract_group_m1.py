"""merge_phase4_party_and_contract_group_m1

Revision ID: cca6e52486f4
Revises: 20260301_phase4_drop_legacy_party_columns, 20260305_contract_group_m1
Create Date: 2026-03-05 18:46:42.154125

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "cca6e52486f4"
down_revision: str | Sequence[str] | None = (
    "20260301_phase4_drop_legacy_party_columns",
    "20260305_contract_group_m1",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
