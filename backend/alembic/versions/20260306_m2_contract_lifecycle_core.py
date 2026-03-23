"""m2 contract lifecycle core tables

Revision ID: 20260306_m2_contract_lifecycle_core
Revises: cca6e52486f4
Create Date: 2026-03-06 18:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260306_m2_contract_lifecycle_core"
down_revision: str | None = "cca6e52486f4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "contract_audit_logs",
        sa.Column("log_id", sa.String(), nullable=False),
        sa.Column("contract_id", sa.String(), nullable=False),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("old_status", sa.String(length=50), nullable=True),
        sa.Column("new_status", sa.String(length=50), nullable=True),
        sa.Column("review_status_old", sa.String(length=50), nullable=True),
        sa.Column("review_status_new", sa.String(length=50), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("operator_id", sa.String(length=100), nullable=True),
        sa.Column("operator_name", sa.String(length=100), nullable=True),
        sa.Column("related_entry_id", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["contract_id"],
            ["contracts.contract_id"],
            name="fk_contract_audit_log_contract",
        ),
        sa.PrimaryKeyConstraint("log_id"),
    )
    op.create_index(
        "ix_contract_audit_logs_contract_id",
        "contract_audit_logs",
        ["contract_id"],
        unique=False,
    )

    op.create_table(
        "contract_rent_terms",
        sa.Column("rent_term_id", sa.String(), nullable=False),
        sa.Column("contract_id", sa.String(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("monthly_rent", sa.DECIMAL(15, 2), nullable=False),
        sa.Column(
            "management_fee",
            sa.DECIMAL(15, 2),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "other_fees",
            sa.DECIMAL(15, 2),
            nullable=False,
            server_default="0",
        ),
        sa.Column("total_monthly_amount", sa.DECIMAL(15, 2), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["contract_id"],
            ["contracts.contract_id"],
            name="fk_contract_rent_term_contract",
        ),
        sa.PrimaryKeyConstraint("rent_term_id"),
        sa.UniqueConstraint(
            "contract_id",
            "sort_order",
            name="uq_contract_rent_term_order",
        ),
    )
    op.create_index(
        "ix_contract_rent_terms_contract_id",
        "contract_rent_terms",
        ["contract_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_contract_rent_terms_contract_id", table_name="contract_rent_terms"
    )
    op.drop_table("contract_rent_terms")
    op.drop_index(
        "ix_contract_audit_logs_contract_id", table_name="contract_audit_logs"
    )
    op.drop_table("contract_audit_logs")
