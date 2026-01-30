"""add_asset_high_frequency_query_indexes

Revision ID: 752cb03b2555
Revises: 8f37856a3aae
Create Date: 2026-01-30 11:31:49.698426

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '752cb03b2555'
down_revision: str | None = '8f37856a3aae'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add indexes for high-frequency query fields in assets table."""
    # 为资产表的高频查询字段添加索引
    op.create_index(op.f('ix_assets_ownership_entity'), 'assets', ['ownership_entity'], unique=False)
    op.create_index(op.f('ix_assets_project_name'), 'assets', ['project_name'], unique=False)
    op.create_index(op.f('ix_assets_ownership_status'), 'assets', ['ownership_status'], unique=False)
    op.create_index(op.f('ix_assets_property_nature'), 'assets', ['property_nature'], unique=False)
    op.create_index(op.f('ix_assets_usage_status'), 'assets', ['usage_status'], unique=False)


def downgrade() -> None:
    """Remove indexes for high-frequency query fields in assets table."""
    op.drop_index(op.f('ix_assets_usage_status'), table_name='assets')
    op.drop_index(op.f('ix_assets_property_nature'), table_name='assets')
    op.drop_index(op.f('ix_assets_ownership_status'), table_name='assets')
    op.drop_index(op.f('ix_assets_project_name'), table_name='assets')
    op.drop_index(op.f('ix_assets_ownership_entity'), table_name='assets')
