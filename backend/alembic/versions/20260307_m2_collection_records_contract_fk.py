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
down_revision: str | None = "20260306_m2_legacy_contract_backfill"
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


def _rewrite_legacy_collection_references() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("collection_records"):
        return

    if inspector.has_table("rent_ledger") and inspector.has_table("contract_ledger_entries"):
        bind.execute(
            sa.text(
                """
                WITH ledger_map AS (
                    SELECT
                        legacy.id AS legacy_ledger_id,
                        target.entry_id AS target_entry_id
                    FROM rent_ledger AS legacy
                    JOIN contract_ledger_entries AS target
                        ON target.contract_id = legacy.contract_id
                       AND target.year_month = legacy.year_month
                )
                UPDATE collection_records AS cr
                SET ledger_id = ledger_map.target_entry_id
                FROM ledger_map
                WHERE cr.ledger_id = ledger_map.legacy_ledger_id
                  AND cr.ledger_id IS DISTINCT FROM ledger_map.target_entry_id
                """
            )
        )

    if inspector.has_table("rent_contracts") and inspector.has_table("contracts"):
        bind.execute(
            sa.text(
                """
                WITH contract_map AS (
                    SELECT
                        legacy.id AS legacy_contract_id,
                        target.contract_id AS target_contract_id
                    FROM rent_contracts AS legacy
                    JOIN contracts AS target
                        ON target.contract_id = legacy.id
                )
                UPDATE collection_records AS cr
                SET contract_id = contract_map.target_contract_id
                FROM contract_map
                WHERE cr.contract_id = contract_map.legacy_contract_id
                  AND cr.contract_id IS DISTINCT FROM contract_map.target_contract_id
                """
            )
        )


def _assert_backfilled_references_exist() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("collection_records"):
        return

    missing_ledger_refs = int(
        bind.execute(
            sa.text(
                """
                SELECT COUNT(*)
                FROM collection_records AS cr
                LEFT JOIN contract_ledger_entries AS cle
                    ON cle.entry_id = cr.ledger_id
                WHERE cle.entry_id IS NULL
                """
            )
        ).scalar()
        or 0
    )
    if missing_ledger_refs > 0:
        raise RuntimeError(
            "collection_records.ledger_id still references rows missing from contract_ledger_entries"
        )

    missing_contract_refs = int(
        bind.execute(
            sa.text(
                """
                SELECT COUNT(*)
                FROM collection_records AS cr
                LEFT JOIN contracts AS c
                    ON c.contract_id = cr.contract_id
                WHERE c.contract_id IS NULL
                """
            )
        ).scalar()
        or 0
    )
    if missing_contract_refs > 0:
        raise RuntimeError(
            "collection_records.contract_id still references rows missing from contracts"
        )


def upgrade() -> None:
    _drop_fk_if_points_to("collection_records", "rent_ledger")
    _drop_fk_if_points_to("collection_records", "rent_contracts")
    _rewrite_legacy_collection_references()
    _assert_backfilled_references_exist()

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
