"""add indexes for management entity and manager name

Revision ID: 20260209_add_asset_management_manager_indexes
Revises: 20260208_phone_email
Create Date: 2026-02-09 11:30:00.000000

"""

from collections.abc import Sequence

from sqlalchemy import inspect

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260209_add_asset_management_manager_indexes"
down_revision: str | None = "20260208_phone_email"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _index_exists(index_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    indexes = inspector.get_indexes("assets")
    return any(index.get("name") == index_name for index in indexes)


def upgrade() -> None:
    """Add missing indexes for high-frequency asset filters."""
    management_entity_index = op.f("ix_assets_management_entity")
    manager_name_index = op.f("ix_assets_manager_name")

    if not _index_exists(management_entity_index):
        op.create_index(
            management_entity_index,
            "assets",
            ["management_entity"],
            unique=False,
        )
    if not _index_exists(manager_name_index):
        op.create_index(
            manager_name_index,
            "assets",
            ["manager_name"],
            unique=False,
        )


def downgrade() -> None:
    """Remove indexes for high-frequency asset filters."""
    management_entity_index = op.f("ix_assets_management_entity")
    manager_name_index = op.f("ix_assets_manager_name")

    if _index_exists(manager_name_index):
        op.drop_index(manager_name_index, table_name="assets")
    if _index_exists(management_entity_index):
        op.drop_index(management_entity_index, table_name="assets")
