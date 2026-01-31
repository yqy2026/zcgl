"""add_search_trgm_indexes

Revision ID: b5a7c4d9e2f1
Revises: 752cb03b2555
Create Date: 2026-01-31 16:30:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b5a7c4d9e2f1"
down_revision: str | None = "752cb03b2555"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add ownership code index and trigram search indexes for assets."""
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_index(op.f("ix_ownerships_code"), "ownerships", ["code"], unique=False)

    op.create_index(
        "ix_assets_property_name_trgm",
        "assets",
        ["property_name"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"property_name": "gin_trgm_ops"},
    )
    op.create_index(
        "ix_assets_business_category_trgm",
        "assets",
        ["business_category"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"business_category": "gin_trgm_ops"},
    )
    op.create_index(
        "ix_assets_address_trgm",
        "assets",
        ["address"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"address": "gin_trgm_ops"},
    )
    op.create_index(
        "ix_assets_ownership_entity_trgm",
        "assets",
        ["ownership_entity"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"ownership_entity": "gin_trgm_ops"},
    )


def downgrade() -> None:
    """Remove trigram search indexes and ownership code index."""
    op.drop_index("ix_assets_ownership_entity_trgm", table_name="assets")
    op.drop_index("ix_assets_address_trgm", table_name="assets")
    op.drop_index("ix_assets_business_category_trgm", table_name="assets")
    op.drop_index("ix_assets_property_name_trgm", table_name="assets")

    op.drop_index(op.f("ix_ownerships_code"), table_name="ownerships")
