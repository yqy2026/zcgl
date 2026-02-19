"""create_abac_and_relation_tables

Revision ID: 20260219_create_abac_and_relation_tables
Revises: 20260219_create_party_tables
Create Date: 2026-02-19 12:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260219_create_abac_and_relation_tables"
down_revision: str | None = "20260219_create_party_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create project/certificate relation and ABAC tables."""

    op.create_table(
        "project_assets",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("asset_id", sa.String(), nullable=False),
        sa.Column(
            "valid_from",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("valid_to", sa.DateTime(), nullable=True),
        sa.Column("bind_reason", sa.String(length=500), nullable=True),
        sa.Column("unbind_reason", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from",
            name="ck_project_assets_valid_range",
        ),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_project_assets_project_id", "project_assets", ["project_id"], unique=False)
    op.create_index("ix_project_assets_asset_id", "project_assets", ["asset_id"], unique=False)

    op.execute(
        """
        CREATE TYPE certificate_relation_role AS ENUM (
            'owner', 'co_owner', 'issuer', 'custodian'
        )
        """
    )

    op.create_table(
        "certificate_party_relations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("certificate_id", sa.String(), nullable=False),
        sa.Column("party_id", sa.String(), nullable=False),
        sa.Column(
            "relation_role",
            postgresql.ENUM(
                "owner",
                "co_owner",
                "issuer",
                "custodian",
                name="certificate_relation_role",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("share_ratio", sa.Numeric(5, 2), nullable=True),
        sa.Column(
            "valid_from",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("valid_to", sa.DateTime(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from",
            name="ck_certificate_party_relations_valid_range",
        ),
        sa.CheckConstraint(
            "share_ratio IS NULL OR (share_ratio > 0 AND share_ratio <= 100)",
            name="ck_certificate_party_relations_share_ratio",
        ),
        sa.ForeignKeyConstraint(
            ["certificate_id"], ["property_certificates.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["party_id"], ["parties.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_certificate_party_relations_certificate_id",
        "certificate_party_relations",
        ["certificate_id"],
        unique=False,
    )
    op.create_index(
        "ix_certificate_party_relations_party_id",
        "certificate_party_relations",
        ["party_id"],
        unique=False,
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uq_certificate_primary_owner_active
        ON certificate_party_relations (certificate_id)
        WHERE relation_role = 'owner' AND is_primary = true AND valid_to IS NULL;
        """
    )
    op.execute(
        """
        ALTER TABLE certificate_party_relations
        ADD CONSTRAINT ex_certificate_party_relations_no_overlap
        EXCLUDE USING gist (
            certificate_id WITH =,
            party_id WITH =,
            relation_role WITH =,
            tsrange(valid_from, COALESCE(valid_to, 'infinity'::timestamp), '[]') WITH &&
        );
        """
    )

    op.execute("CREATE TYPE abac_effect AS ENUM ('allow', 'deny')")
    op.create_table(
        "abac_policies",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column(
            "effect",
            postgresql.ENUM("allow", "deny", name="abac_effect", create_type=False),
            nullable=False,
            server_default="allow",
        ),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.execute(
        "CREATE TYPE abac_action AS ENUM ('create', 'read', 'list', 'update', 'delete', 'export')"
    )
    op.create_table(
        "abac_policy_rules",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("policy_id", sa.String(), nullable=False),
        sa.Column("resource_type", sa.String(length=100), nullable=False),
        sa.Column(
            "action",
            postgresql.ENUM(
                "create",
                "read",
                "list",
                "update",
                "delete",
                "export",
                name="abac_action",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("condition_expr", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("field_mask", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["policy_id"], ["abac_policies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_abac_policy_rules_policy_id", "abac_policy_rules", ["policy_id"], unique=False
    )

    op.create_table(
        "abac_role_policies",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("role_id", sa.String(), nullable=False),
        sa.Column("policy_id", sa.String(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("priority_override", sa.Integer(), nullable=True),
        sa.Column("params_override", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["policy_id"], ["abac_policies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("role_id", "policy_id", name="uq_abac_role_policies_role_policy"),
    )
    op.create_index(
        "ix_abac_role_policies_role_id", "abac_role_policies", ["role_id"], unique=False
    )
    op.create_index(
        "ix_abac_role_policies_policy_id",
        "abac_role_policies",
        ["policy_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop ABAC and relation tables."""

    op.drop_table("abac_role_policies")
    op.drop_table("abac_policy_rules")
    op.drop_table("abac_policies")

    op.execute("DROP TYPE IF EXISTS abac_action")
    op.execute("DROP TYPE IF EXISTS abac_effect")

    op.drop_table("certificate_party_relations")
    op.execute("DROP TYPE IF EXISTS certificate_relation_role")

    op.drop_table("project_assets")
