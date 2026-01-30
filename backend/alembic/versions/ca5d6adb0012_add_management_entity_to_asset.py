"""add management_entity to asset

Revision ID: ca5d6adb0012
Revises: 20250120_add_security_events
Create Date: 2026-01-24 11:11:33.734151

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ca5d6adb0012"
down_revision: str | None = "20250120_add_security_events"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = inspect(bind)
    if inspector.has_table("assets"):
        columns = {column["name"] for column in inspector.get_columns("assets")}
        if "management_entity" not in columns:
            op.add_column(
                "assets",
                sa.Column(
                    "management_entity",
                    sa.String(length=200),
                    nullable=True,
                    comment="经营管理单位",
                ),
            )


def downgrade() -> None:
    """Downgrade schema - remove management_entity column from assets."""
    bind = op.get_bind()
    inspector = inspect(bind)
    if inspector.has_table("assets"):
        columns = {column["name"] for column in inspector.get_columns("assets")}
        if "management_entity" in columns:
            op.drop_column("assets", "management_entity")
