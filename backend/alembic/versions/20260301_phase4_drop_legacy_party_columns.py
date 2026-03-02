"""phase4_drop_legacy_party_columns

Revision ID: 20260301_phase4_drop_legacy_party_columns
Revises: 20260301_phase4_set_party_columns_not_null
Create Date: 2026-03-01 09:20:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260301_phase4_drop_legacy_party_columns"
down_revision: str | None = "20260301_phase4_set_party_columns_not_null"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = "20260301_phase4_set_party_columns_not_null"


_LEGACY_COLUMNS: tuple[tuple[str, str], ...] = (
    ("assets", "organization_id"),
    ("assets", "ownership_id"),
    ("assets", "management_entity"),
    ("assets", "project_id"),
    ("rent_contracts", "ownership_id"),
    ("rent_ledger", "ownership_id"),
    ("projects", "organization_id"),
    ("projects", "management_entity"),
    ("projects", "ownership_entity"),
    ("property_certificates", "organization_id"),
    ("roles", "organization_id"),
)

_LEGACY_TABLES: tuple[str, ...] = (
    "project_ownership_relations",
    "property_certificate_owners",
    "property_owners",
    "abac_policy_subjects",
)


def _column_exists(
    inspector: sa.engine.reflection.Inspector,
    table_name: str,
    column_name: str,
) -> bool:
    if not inspector.has_table(table_name):
        return False
    return any(
        str(column.get("name")) == column_name
        for column in inspector.get_columns(table_name)
    )


def _drop_legacy_columns(inspector: sa.engine.reflection.Inspector) -> None:
    for table_name, column_name in _LEGACY_COLUMNS:
        if not _column_exists(inspector, table_name, column_name):
            continue
        op.drop_column(table_name, column_name)


def _drop_legacy_tables(inspector: sa.engine.reflection.Inspector) -> None:
    for table_name in _LEGACY_TABLES:
        if not inspector.has_table(table_name):
            continue
        op.drop_table(table_name)


def upgrade() -> None:
    """Drop Phase4 Step4 legacy columns/tables with idempotent guards."""
    inspector = sa.inspect(op.get_bind())
    _drop_legacy_columns(inspector)
    _drop_legacy_tables(inspector)


def downgrade() -> None:
    """Best-effort rollback for dropped Step4 legacy columns/tables."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("assets"):
        if not _column_exists(inspector, "assets", "organization_id"):
            op.add_column("assets", sa.Column("organization_id", sa.String(), nullable=True))
        if not _column_exists(inspector, "assets", "ownership_id"):
            op.add_column("assets", sa.Column("ownership_id", sa.String(), nullable=True))
        if not _column_exists(inspector, "assets", "management_entity"):
            op.add_column("assets", sa.Column("management_entity", sa.String(length=200), nullable=True))
        if not _column_exists(inspector, "assets", "project_id"):
            op.add_column("assets", sa.Column("project_id", sa.String(), nullable=True))

    if inspector.has_table("rent_contracts") and not _column_exists(
        inspector, "rent_contracts", "ownership_id"
    ):
        op.add_column("rent_contracts", sa.Column("ownership_id", sa.String(), nullable=True))

    if inspector.has_table("rent_ledger") and not _column_exists(
        inspector, "rent_ledger", "ownership_id"
    ):
        op.add_column("rent_ledger", sa.Column("ownership_id", sa.String(), nullable=True))

    if inspector.has_table("projects"):
        if not _column_exists(inspector, "projects", "organization_id"):
            op.add_column("projects", sa.Column("organization_id", sa.String(), nullable=True))
        if not _column_exists(inspector, "projects", "management_entity"):
            op.add_column("projects", sa.Column("management_entity", sa.String(length=200), nullable=True))
        if not _column_exists(inspector, "projects", "ownership_entity"):
            op.add_column("projects", sa.Column("ownership_entity", sa.String(length=200), nullable=True))

    if inspector.has_table("property_certificates") and not _column_exists(
        inspector, "property_certificates", "organization_id"
    ):
        op.add_column(
            "property_certificates",
            sa.Column("organization_id", sa.String(), nullable=True),
        )

    if inspector.has_table("roles") and not _column_exists(inspector, "roles", "organization_id"):
        op.add_column("roles", sa.Column("organization_id", sa.String(), nullable=True))

    inspector = sa.inspect(bind)
    if not inspector.has_table("project_ownership_relations"):
        op.create_table(
            "project_ownership_relations",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("project_id", sa.String(), nullable=False),
            sa.Column("ownership_id", sa.String(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.Column("created_by", sa.String(length=100), nullable=True),
            sa.Column("updated_by", sa.String(length=100), nullable=True),
        )

    if not inspector.has_table("property_owners"):
        op.create_table(
            "property_owners",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("owner_type", sa.String(), nullable=False),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("id_type", sa.String(length=50), nullable=True),
            sa.Column("id_number", sa.String(length=100), nullable=True),
            sa.Column("phone", sa.String(length=20), nullable=True),
            sa.Column("address", sa.String(length=500), nullable=True),
            sa.Column("organization_id", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )

    if not inspector.has_table("property_certificate_owners"):
        op.create_table(
            "property_certificate_owners",
            sa.Column("certificate_id", sa.String(), primary_key=True),
            sa.Column("owner_id", sa.String(), primary_key=True),
            sa.Column("ownership_share", sa.Numeric(5, 2), nullable=True),
            sa.Column("owner_category", sa.String(length=50), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )

    if not inspector.has_table("abac_policy_subjects"):
        op.create_table(
            "abac_policy_subjects",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("policy_id", sa.String(), nullable=False),
            sa.Column("subject_type", sa.String(length=100), nullable=False),
            sa.Column("subject_id", sa.String(), nullable=False),
        )
