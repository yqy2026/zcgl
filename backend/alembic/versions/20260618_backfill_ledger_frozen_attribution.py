"""backfill frozen attribution for existing ledgers

Revision ID: 20260618_backfill_ledger_frozen_attribution
Revises: 20260618_ledger_frozen_attribution
Create Date: 2026-06-18

Existing ledger rows predate frozen attribution. This migration snapshots the
current contract group and asset links as the best available approximation of
the historical attribution at migration time.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260618_backfill_ledger_frozen_attribution"
down_revision: str | Sequence[str] | None = "20260618_ledger_frozen_attribution"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

REQUIRED_TABLES = (
    "contract_ledger_entries",
    "service_fee_ledgers",
    "contracts",
    "contract_groups",
    "contract_assets",
    "contract_group_assets",
)
ATTRIBUTION_COLUMNS = (
    "attributed_project_id",
    "attributed_owner_party_id",
    "attributed_operator_party_id",
    "attributed_asset_ids",
)


def _has_required_schema(inspector: sa.engine.reflection.Inspector) -> bool:
    if not all(inspector.has_table(table_name) for table_name in REQUIRED_TABLES):
        return False

    columns_by_table = {
        table_name: {column["name"] for column in inspector.get_columns(table_name)}
        for table_name in ("contract_ledger_entries", "service_fee_ledgers")
    }
    return all(
        column_name in columns_by_table[table_name]
        for table_name in columns_by_table
        for column_name in ATTRIBUTION_COLUMNS
    )


def _execute_sql(bind: sa.engine.Connection, sql_text: str) -> None:
    bind.execute(sa.text(sql_text))


def _count_rows(bind: sa.engine.Connection, sql_text: str) -> int:
    return int(bind.execute(sa.text(sql_text)).scalar() or 0)


def _assert_no_missing_attribution(bind: sa.engine.Connection) -> None:
    missing_rent_ledgers = _count_rows(
        bind,
        """
        SELECT COUNT(*)
        FROM contract_ledger_entries
        WHERE attributed_project_id IS NULL
           OR attributed_owner_party_id IS NULL
           OR attributed_operator_party_id IS NULL
           OR attributed_asset_ids IS NULL
           OR jsonb_array_length(attributed_asset_ids) = 0
        """,
    )
    if missing_rent_ledgers > 0:
        raise RuntimeError(
            "contract_ledger_entries still contain missing frozen attribution after backfill"
        )

    missing_service_fee_ledgers = _count_rows(
        bind,
        """
        SELECT COUNT(*)
        FROM service_fee_ledgers
        WHERE attributed_project_id IS NULL
           OR attributed_owner_party_id IS NULL
           OR attributed_operator_party_id IS NULL
           OR attributed_asset_ids IS NULL
           OR jsonb_array_length(attributed_asset_ids) = 0
        """,
    )
    if missing_service_fee_ledgers > 0:
        raise RuntimeError(
            "service_fee_ledgers still contain missing frozen attribution after backfill"
        )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not _has_required_schema(inspector):
        return

    _execute_sql(
        bind,
        """
        WITH contract_asset_snapshots AS (
            SELECT
                c.contract_id,
                cg.project_id,
                cg.owner_party_id,
                cg.operator_party_id,
                COALESCE(contract_assets.asset_ids, group_assets.asset_ids) AS asset_ids
            FROM contracts AS c
            JOIN contract_groups AS cg
                ON cg.contract_group_id = c.contract_group_id
            LEFT JOIN LATERAL (
                SELECT jsonb_agg(ca.asset_id ORDER BY ca.asset_id) AS asset_ids
                FROM contract_assets AS ca
                WHERE ca.contract_id = c.contract_id
            ) AS contract_assets ON TRUE
            LEFT JOIN LATERAL (
                SELECT jsonb_agg(cga.asset_id ORDER BY cga.asset_id) AS asset_ids
                FROM contract_group_assets AS cga
                WHERE cga.contract_group_id = cg.contract_group_id
            ) AS group_assets ON TRUE
        )
        UPDATE contract_ledger_entries AS cle
        SET
            attributed_project_id = COALESCE(
                cle.attributed_project_id,
                contract_asset_snapshots.project_id
            ),
            attributed_owner_party_id = COALESCE(
                cle.attributed_owner_party_id,
                contract_asset_snapshots.owner_party_id
            ),
            attributed_operator_party_id = COALESCE(
                cle.attributed_operator_party_id,
                contract_asset_snapshots.operator_party_id
            ),
            attributed_asset_ids = COALESCE(
                cle.attributed_asset_ids,
                contract_asset_snapshots.asset_ids,
                '[]'::jsonb
            )
        FROM contract_asset_snapshots
        WHERE cle.contract_id = contract_asset_snapshots.contract_id
        """,
    )

    _execute_sql(
        bind,
        """
        UPDATE service_fee_ledgers AS sfl
        SET
            attributed_project_id = COALESCE(
                sfl.attributed_project_id,
                cle.attributed_project_id
            ),
            attributed_owner_party_id = COALESCE(
                sfl.attributed_owner_party_id,
                cle.attributed_owner_party_id
            ),
            attributed_operator_party_id = COALESCE(
                sfl.attributed_operator_party_id,
                cle.attributed_operator_party_id
            ),
            attributed_asset_ids = COALESCE(
                sfl.attributed_asset_ids,
                cle.attributed_asset_ids,
                '[]'::jsonb
            )
        FROM contract_ledger_entries AS cle
        WHERE sfl.source_ledger_id = cle.entry_id
        """,
    )

    _assert_no_missing_attribution(bind)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not _has_required_schema(inspector):
        return

    _execute_sql(
        bind,
        """
        UPDATE service_fee_ledgers
        SET
            attributed_project_id = NULL,
            attributed_owner_party_id = NULL,
            attributed_operator_party_id = NULL,
            attributed_asset_ids = NULL
        """,
    )
    _execute_sql(
        bind,
        """
        UPDATE contract_ledger_entries
        SET
            attributed_project_id = NULL,
            attributed_owner_party_id = NULL,
            attributed_operator_party_id = NULL,
            attributed_asset_ids = NULL
        """,
    )
