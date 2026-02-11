"""add property certificate tables

Revision ID: 20250118_add_property_cert_tables
Revises: 20250118_add_llm_prompt
Create Date: 2025-01-18 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20250118_add_property_cert_tables"
down_revision: str | None = "20250118_add_uid_feedback"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Ensure Alembic version column can hold long revision IDs.
    # PostgreSQL default is VARCHAR(32), while this repository contains
    # revision IDs longer than 32 characters.
    op.execute(
        "ALTER TABLE alembic_version "
        "ALTER COLUMN version_num TYPE VARCHAR(255)"
    )

    # Check if tables already exist (created by initial migration)
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    # Skip if tables already exist (from initial migration)
    if "property_owners" in existing_tables:
        return

    # Create property_owners table
    op.create_table(
        "property_owners",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("owner_type", sa.String, nullable=False, index=True),
        sa.Column("name", sa.String(200), nullable=False, index=True),
        sa.Column("id_type", sa.String(50), nullable=True),
        sa.Column("id_number", sa.String(100), nullable=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("address", sa.String(500), nullable=True),
        sa.Column(
            "organization_id",
            sa.String(),
            sa.ForeignKey("organizations.id"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    # Create indexes for property_owners
    op.create_index("idx_property_owners_owner_type", "property_owners", ["owner_type"])
    op.create_index("idx_property_owners_name", "property_owners", ["name"])
    op.create_index(
        "idx_property_owners_organization_id", "property_owners", ["organization_id"]
    )

    # Create property_certificates table
    op.create_table(
        "property_certificates",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column(
            "certificate_number",
            sa.String(100),
            nullable=False,
            unique=True,
            index=True,
        ),
        sa.Column("certificate_type", sa.String, nullable=False, index=True),
        sa.Column("extraction_confidence", sa.Float, nullable=True),
        sa.Column("extraction_source", sa.String(20), server_default="manual"),
        sa.Column("verified", sa.Boolean, server_default="false"),
        sa.Column("registration_date", sa.Date, nullable=True),
        sa.Column("property_address", sa.String(500), nullable=True),
        sa.Column("property_type", sa.String(50), nullable=True),
        sa.Column("building_area", sa.String(50), nullable=True),
        sa.Column("floor_info", sa.String(100), nullable=True),
        sa.Column("land_area", sa.String(50), nullable=True),
        sa.Column("land_use_type", sa.String(50), nullable=True),
        sa.Column("land_use_term_start", sa.Date, nullable=True),
        sa.Column("land_use_term_end", sa.Date, nullable=True),
        sa.Column("co_ownership", sa.String(200), nullable=True),
        sa.Column("restrictions", sa.Text, nullable=True),
        sa.Column("remarks", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.Column("created_by", sa.String(100), nullable=True),
    )

    # Create indexes for property_certificates
    op.create_index(
        "idx_property_certificates_certificate_number",
        "property_certificates",
        ["certificate_number"],
    )
    op.create_index(
        "idx_property_certificates_certificate_type",
        "property_certificates",
        ["certificate_type"],
    )
    op.create_index(
        "idx_property_certificates_property_address",
        "property_certificates",
        ["property_address"],
    )

    # Create association table: property_certificate_owners
    op.create_table(
        "property_certificate_owners",
        sa.Column(
            "certificate_id",
            sa.String,
            sa.ForeignKey("property_certificates.id"),
            primary_key=True,
        ),
        sa.Column(
            "owner_id", sa.String, sa.ForeignKey("property_owners.id"), primary_key=True
        ),
        sa.Column("ownership_share", sa.Numeric(5, 2), nullable=True),
        sa.Column("owner_category", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    # Create indexes for property_certificate_owners
    op.create_index(
        "idx_property_certificate_owners_certificate_id",
        "property_certificate_owners",
        ["certificate_id"],
    )
    op.create_index(
        "idx_property_certificate_owners_owner_id",
        "property_certificate_owners",
        ["owner_id"],
    )

    # Create association table: property_cert_assets
    op.create_table(
        "property_cert_assets",
        sa.Column(
            "certificate_id",
            sa.String,
            sa.ForeignKey("property_certificates.id"),
            primary_key=True,
        ),
        sa.Column("asset_id", sa.String, sa.ForeignKey("assets.id"), primary_key=True),
        sa.Column("link_type", sa.String(50), nullable=True),
        sa.Column("notes", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    # Create indexes for property_cert_assets
    op.create_index(
        "idx_property_cert_assets_certificate_id",
        "property_cert_assets",
        ["certificate_id"],
    )
    op.create_index(
        "idx_property_cert_assets_asset_id", "property_cert_assets", ["asset_id"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Check if tables exist before dropping
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    # Only drop if tables exist
    if "property_cert_assets" not in existing_tables:
        return

    # Drop indexes
    op.drop_index("idx_property_cert_assets_asset_id", "property_cert_assets")
    op.drop_index("idx_property_cert_assets_certificate_id", "property_cert_assets")
    op.drop_index(
        "idx_property_certificate_owners_owner_id", "property_certificate_owners"
    )
    op.drop_index(
        "idx_property_certificate_owners_certificate_id", "property_certificate_owners"
    )
    op.drop_index("idx_property_certificates_property_address", "property_certificates")
    op.drop_index("idx_property_certificates_certificate_type", "property_certificates")
    op.drop_index(
        "idx_property_certificates_certificate_number", "property_certificates"
    )
    op.drop_index("idx_property_owners_organization_id", "property_owners")
    op.drop_index("idx_property_owners_name", "property_owners")
    op.drop_index("idx_property_owners_owner_type", "property_owners")

    # Drop association tables
    op.drop_table("property_cert_assets")
    op.drop_table("property_certificate_owners")

    # Drop tables
    op.drop_table("property_certificates")
    op.drop_table("property_owners")
