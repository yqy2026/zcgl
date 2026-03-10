"""m2 collection records reference contract ledger entries

Revision ID: 20260307_m2_collection_records_contract_fk
Revises: 20260306_m2_contract_ledger_entries
Create Date: 2026-03-07 09:02:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260307_m2_collection_records_contract_fk"
down_revision: str | None = "20260306_m2_contract_ledger_entries"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _drop_fk_if_points_to(table_name: str, referred_table: str) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for foreign_key in inspector.get_foreign_keys(table_name):
        if foreign_key.get("referred_table") != referred_table:
            continue
        constraint_name = foreign_key.get("name")
        if constraint_name:
            op.drop_constraint(constraint_name, table_name, type_="foreignkey")


def upgrade() -> None:
    _drop_fk_if_points_to("collection_records", "rent_ledger")
    _drop_fk_if_points_to("collection_records", "rent_contracts")

    op.create_foreign_key(
        "fk_collection_records_ledger_entry",
        "collection_records",
        "contract_ledger_entries",
        ["ledger_id"],
        ["entry_id"],
    )
    op.create_foreign_key(
        "fk_collection_records_contract",
        "collection_records",
        "contracts",
        ["contract_id"],
        ["contract_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_collection_records_ledger_entry",
        "collection_records",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_collection_records_contract",
        "collection_records",
        type_="foreignkey",
    )

    op.create_foreign_key(
        "fk_collection_records_legacy_ledger",
        "collection_records",
        "rent_ledger",
        ["ledger_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_collection_records_legacy_contract",
        "collection_records",
        "rent_contracts",
        ["contract_id"],
        ["id"],
    )
