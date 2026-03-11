"""REQ-AST-002: add partial unique index ensuring one active project per asset

Revision ID: 20260311_req_ast_002_active_project_unique
Revises: 20260307_m2_cleanup_legacy_contract_policy_rules
Create Date: 2026-03-11 12:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260311_req_ast_002_active_project_unique"
down_revision: str | None = "20260307_m2_cleanup_legacy_contract_policy_rules"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_project_assets_active_asset "
        "ON project_assets (asset_id) WHERE valid_to IS NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_project_assets_active_asset")
