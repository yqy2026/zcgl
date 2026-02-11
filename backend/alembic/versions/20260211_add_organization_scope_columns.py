"""Add organization scope columns for core asset tables.

Revision ID: 20260211_add_organization_scope_columns
Revises: 20260211_add_phase2_aligned_performance_indexes
Create Date: 2026-02-11 16:45:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260211_add_organization_scope_columns"
down_revision: str | None = "20260211_add_phase2_aligned_performance_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _column_exists(bind: sa.engine.Connection, table: str, column: str) -> bool:
    inspector = sa.inspect(bind)
    return any(col["name"] == column for col in inspector.get_columns(table))


def upgrade() -> None:
    """Add organization_id columns and backfill core business tables."""
    bind = op.get_bind()

    if not _column_exists(bind, "projects", "organization_id"):
        with op.batch_alter_table("projects") as batch_op:
            batch_op.add_column(
                sa.Column("organization_id", sa.String(), nullable=True)
            )
            batch_op.create_foreign_key(
                "fk_projects_organization_id_organizations",
                "organizations",
                ["organization_id"],
                ["id"],
            )
            batch_op.create_index(
                "ix_projects_organization_id",
                ["organization_id"],
                unique=False,
            )

    if not _column_exists(bind, "assets", "organization_id"):
        with op.batch_alter_table("assets") as batch_op:
            batch_op.add_column(
                sa.Column("organization_id", sa.String(), nullable=True)
            )
            batch_op.create_foreign_key(
                "fk_assets_organization_id_organizations",
                "organizations",
                ["organization_id"],
                ["id"],
            )
            batch_op.create_index(
                "ix_assets_organization_id",
                ["organization_id"],
                unique=False,
            )

    if not _column_exists(bind, "property_certificates", "organization_id"):
        with op.batch_alter_table("property_certificates") as batch_op:
            batch_op.add_column(
                sa.Column("organization_id", sa.String(), nullable=True)
            )
            batch_op.create_foreign_key(
                "fk_property_certificates_organization_id_organizations",
                "organizations",
                ["organization_id"],
                ["id"],
            )
            batch_op.create_index(
                "ix_property_certificates_organization_id",
                ["organization_id"],
                unique=False,
            )

    # Backfill from creator's default organization.
    op.execute(
        """
        UPDATE projects AS p
        SET organization_id = u.default_organization_id
        FROM users AS u
        WHERE p.organization_id IS NULL
          AND u.default_organization_id IS NOT NULL
          AND (
            p.created_by = u.id
            OR p.created_by = u.username
          )
        """
    )

    op.execute(
        """
        UPDATE assets AS a
        SET organization_id = u.default_organization_id
        FROM users AS u
        WHERE a.organization_id IS NULL
          AND u.default_organization_id IS NOT NULL
          AND (
            a.created_by = u.id
            OR a.created_by = u.username
          )
        """
    )

    op.execute(
        """
        UPDATE property_certificates AS pc
        SET organization_id = u.default_organization_id
        FROM users AS u
        WHERE pc.organization_id IS NULL
          AND u.default_organization_id IS NOT NULL
          AND (
            pc.created_by = u.id
            OR pc.created_by = u.username
          )
        """
    )

    # Backfill certificates by owner-organization relation if creator mapping missing.
    op.execute(
        """
        UPDATE property_certificates AS pc
        SET organization_id = owner_scope.organization_id
        FROM (
            SELECT
                pco.certificate_id AS certificate_id,
                MIN(po.organization_id) AS organization_id
            FROM property_certificate_owners AS pco
            JOIN property_owners AS po
              ON po.id = pco.owner_id
            WHERE po.organization_id IS NOT NULL
            GROUP BY pco.certificate_id
        ) AS owner_scope
        WHERE pc.id = owner_scope.certificate_id
          AND pc.organization_id IS NULL
        """
    )


def downgrade() -> None:
    """Drop organization scope columns for core business tables."""
    bind = op.get_bind()

    if _column_exists(bind, "property_certificates", "organization_id"):
        with op.batch_alter_table("property_certificates") as batch_op:
            batch_op.drop_index("ix_property_certificates_organization_id")
            batch_op.drop_constraint(
                "fk_property_certificates_organization_id_organizations",
                type_="foreignkey",
            )
            batch_op.drop_column("organization_id")

    if _column_exists(bind, "assets", "organization_id"):
        with op.batch_alter_table("assets") as batch_op:
            batch_op.drop_index("ix_assets_organization_id")
            batch_op.drop_constraint(
                "fk_assets_organization_id_organizations",
                type_="foreignkey",
            )
            batch_op.drop_column("organization_id")

    if _column_exists(bind, "projects", "organization_id"):
        with op.batch_alter_table("projects") as batch_op:
            batch_op.drop_index("ix_projects_organization_id")
            batch_op.drop_constraint(
                "fk_projects_organization_id_organizations",
                type_="foreignkey",
            )
            batch_op.drop_column("organization_id")
