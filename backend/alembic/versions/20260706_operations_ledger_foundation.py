"""operations ledger foundation

Revision ID: 20260706_operations_ledger_foundation
Revises: 20260623_notification_create_perm
Create Date: 2026-07-06
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260706_operations_ledger_foundation"
down_revision: str | Sequence[str] | None = "20260623_notification_create_perm"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _table_has_column(
    inspector: sa.engine.reflection.Inspector,
    table_name: str,
    column_name: str,
) -> bool:
    if not inspector.has_table(table_name):
        return False
    return any(
        column["name"] == column_name for column in inspector.get_columns(table_name)
    )


def _constraint_exists(
    inspector: sa.engine.reflection.Inspector,
    table_name: str,
    constraint_name: str,
) -> bool:
    if not inspector.has_table(table_name):
        return False
    constraints = inspector.get_unique_constraints(table_name)
    constraints += inspector.get_check_constraints(table_name)
    constraints += inspector.get_foreign_keys(table_name)
    return any(constraint.get("name") == constraint_name for constraint in constraints)


def _add_contract_ledger_columns(inspector: sa.engine.reflection.Inspector) -> None:
    if not inspector.has_table("contract_ledger_entries"):
        return
    if not _table_has_column(inspector, "contract_ledger_entries", "ledger_views"):
        op.add_column(
            "contract_ledger_entries",
            sa.Column(
                "ledger_views",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
                server_default=sa.text("'[]'::jsonb"),
            ),
        )
    if not _table_has_column(inspector, "contract_ledger_entries", "follow_up_status"):
        op.add_column(
            "contract_ledger_entries",
            sa.Column("follow_up_status", sa.String(length=50), nullable=True),
        )
    if not _table_has_column(
        inspector, "contract_ledger_entries", "next_follow_up_date"
    ):
        op.add_column(
            "contract_ledger_entries",
            sa.Column("next_follow_up_date", sa.Date(), nullable=True),
        )
    if not _table_has_column(inspector, "contract_ledger_entries", "follow_up_note"):
        op.add_column(
            "contract_ledger_entries",
            sa.Column("follow_up_note", sa.Text(), nullable=True),
        )


def _create_payment_tables(inspector: sa.engine.reflection.Inspector) -> None:
    if not inspector.has_table("operational_payment_flows"):
        op.create_table(
            "operational_payment_flows",
            sa.Column("flow_id", sa.String(), nullable=False),
            sa.Column("flow_type", sa.String(length=40), nullable=False),
            sa.Column("occurred_on", sa.Date(), nullable=False),
            sa.Column("amount", sa.DECIMAL(15, 2), nullable=False),
            sa.Column("registered_by", sa.String(length=100), nullable=False),
            sa.Column("counterparty_id", sa.String(), nullable=True),
            sa.Column(
                "voucher_attachment_ids",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
            ),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column(
                "status",
                sa.String(length=20),
                nullable=False,
                server_default="active",
            ),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.CheckConstraint(
                "amount > 0", name="ck_operational_payment_flow_amount_positive"
            ),
            sa.CheckConstraint(
                "flow_type IN ('terminal_rent_receipt', 'service_fee_receipt', 'upstream_cost_payment')",
                name="ck_operational_payment_flow_type",
            ),
            sa.CheckConstraint(
                "status IN ('active', 'voided', 'corrected')",
                name="ck_operational_payment_flow_status",
            ),
            sa.ForeignKeyConstraint(
                ["counterparty_id"],
                ["parties.id"],
                name="fk_operational_payment_flow_counterparty",
            ),
            sa.PrimaryKeyConstraint("flow_id"),
        )
        op.create_index(
            "ix_operational_payment_flows_flow_type",
            "operational_payment_flows",
            ["flow_type"],
        )
        op.create_index(
            "ix_operational_payment_flows_counterparty_id",
            "operational_payment_flows",
            ["counterparty_id"],
        )
    if not inspector.has_table("payment_allocations"):
        op.create_table(
            "payment_allocations",
            sa.Column("allocation_id", sa.String(), nullable=False),
            sa.Column("flow_id", sa.String(), nullable=False),
            sa.Column("target_type", sa.String(length=40), nullable=False),
            sa.Column("target_id", sa.String(), nullable=False),
            sa.Column("year_month", sa.String(length=7), nullable=False),
            sa.Column("amount", sa.DECIMAL(15, 2), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.CheckConstraint(
                "amount > 0", name="ck_payment_allocation_amount_positive"
            ),
            sa.CheckConstraint(
                "target_type IN ('contract_ledger_entry', 'service_fee_ledger')",
                name="ck_payment_allocation_target_type",
            ),
            sa.CheckConstraint(
                "year_month ~ '^\\d{4}-\\d{2}$'",
                name="ck_payment_allocation_year_month_format",
            ),
            sa.ForeignKeyConstraint(
                ["flow_id"],
                ["operational_payment_flows.flow_id"],
                name="fk_payment_allocation_flow",
            ),
            sa.PrimaryKeyConstraint("allocation_id"),
        )
        op.create_index(
            "ix_payment_allocations_flow_id", "payment_allocations", ["flow_id"]
        )
        op.create_index(
            "ix_payment_allocations_target_type", "payment_allocations", ["target_type"]
        )
        op.create_index(
            "ix_payment_allocations_target_id", "payment_allocations", ["target_id"]
        )
        op.create_index(
            "ix_payment_allocations_year_month", "payment_allocations", ["year_month"]
        )


def _add_service_fee_columns(inspector: sa.engine.reflection.Inspector) -> None:
    if not inspector.has_table("service_fee_ledgers"):
        return
    if not _table_has_column(
        inspector, "service_fee_ledgers", "agency_agreement_contract_id"
    ):
        op.add_column(
            "service_fee_ledgers",
            sa.Column("agency_agreement_contract_id", sa.String(), nullable=True),
        )
    if not _table_has_column(inspector, "service_fee_ledgers", "source_ledger_ids"):
        op.add_column(
            "service_fee_ledgers",
            sa.Column(
                "source_ledger_ids",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
                server_default=sa.text("'[]'::jsonb"),
            ),
        )
    if not _table_has_column(
        inspector, "service_fee_ledgers", "calculation_base_amount"
    ):
        op.add_column(
            "service_fee_ledgers",
            sa.Column(
                "calculation_base_amount",
                sa.DECIMAL(15, 2),
                nullable=True,
                server_default="0",
            ),
        )


def _backfill_ledger_views() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE contract_ledger_entries AS cle
            SET ledger_views = CASE c.group_relation_type
                WHEN 'DOWNSTREAM' THEN '["terminal_collection", "operator_income"]'::jsonb
                WHEN 'DIRECT_LEASE' THEN '["terminal_collection"]'::jsonb
                WHEN 'UPSTREAM' THEN '["operator_cost"]'::jsonb
                ELSE '[]'::jsonb
            END
            FROM contracts AS c
            WHERE cle.contract_id = c.contract_id
              AND (cle.ledger_views IS NULL OR cle.ledger_views = '[]'::jsonb)
            """
        )
    )
    missing = bind.execute(
        sa.text(
            """
            SELECT COUNT(*)
            FROM contract_ledger_entries
            WHERE payment_status <> 'voided'
              AND (ledger_views IS NULL OR jsonb_array_length(ledger_views) = 0)
            """
        )
    ).scalar()
    if missing:
        raise RuntimeError(
            "contract_ledger_entries contains non-voided rows without ledger_views"
        )


def _backfill_service_fee_ledgers(inspector: sa.engine.reflection.Inspector) -> None:
    if not inspector.has_table("service_fee_ledgers"):
        return
    bind = op.get_bind()
    invalid_group = bind.execute(
        sa.text(
            """
            SELECT sfl.contract_group_id
            FROM service_fee_ledgers AS sfl
            LEFT JOIN contracts AS c
              ON c.contract_group_id = sfl.contract_group_id
             AND c.group_relation_type = 'ENTRUSTED'
            GROUP BY sfl.contract_group_id
            HAVING COUNT(c.contract_id) <> 1
            LIMIT 1
            """
        )
    ).first()
    if invalid_group is not None:
        raise RuntimeError(
            "service_fee_ledgers require exactly one entrusted contract per group"
        )

    bind.execute(
        sa.text(
            """
            UPDATE service_fee_ledgers AS sfl
            SET agency_agreement_contract_id = c.contract_id
            FROM contracts AS c
            WHERE c.contract_group_id = sfl.contract_group_id
              AND c.group_relation_type = 'ENTRUSTED'
               AND sfl.agency_agreement_contract_id IS NULL
            """
        )
    )

    if _table_has_column(inspector, "service_fee_ledgers", "source_ledger_id"):
        missing_source = bind.execute(
            sa.text(
                """
                SELECT sfl.service_fee_entry_id
                FROM service_fee_ledgers AS sfl
                LEFT JOIN contract_ledger_entries AS cle
                  ON cle.entry_id = sfl.source_ledger_id
                WHERE sfl.source_ledger_id IS NOT NULL
                  AND cle.entry_id IS NULL
                LIMIT 1
                """
            )
        ).first()
        if missing_source is not None:
            raise RuntimeError(
                "service_fee_ledgers contains rows with missing source ledger entries"
            )

        inconsistent_scope = bind.execute(
            sa.text(
                """
                SELECT sfl.contract_group_id, sfl.attributed_owner_party_id, sfl.year_month
                FROM service_fee_ledgers AS sfl
                WHERE sfl.source_ledger_id IS NOT NULL
                GROUP BY
                    sfl.contract_group_id,
                    sfl.agency_agreement_contract_id,
                    sfl.attributed_owner_party_id,
                    sfl.year_month
                HAVING COUNT(DISTINCT sfl.service_fee_ratio) <> 1
                    OR COUNT(DISTINCT sfl.currency_code) <> 1
                LIMIT 1
                """
            )
        ).first()
        if inconsistent_scope is not None:
            raise RuntimeError(
                "service_fee_ledgers monthly scope has inconsistent ratio or currency"
            )

        bind.execute(
            sa.text(
                """
                WITH grouped AS (
                    SELECT
                        MIN(sfl.service_fee_entry_id) AS canonical_id,
                        sfl.contract_group_id,
                        sfl.agency_agreement_contract_id,
                        sfl.attributed_owner_party_id,
                        sfl.year_month,
                        (ARRAY_AGG(sfl.agency_contract_id ORDER BY sfl.service_fee_entry_id))[1]
                            AS agency_contract_id,
                        (ARRAY_AGG(sfl.currency_code ORDER BY sfl.service_fee_entry_id))[1]
                            AS currency_code,
                        (ARRAY_AGG(sfl.service_fee_ratio ORDER BY sfl.service_fee_entry_id))[1]
                            AS service_fee_ratio,
                        TO_JSONB(ARRAY_AGG(DISTINCT sfl.source_ledger_id)) AS source_ledger_ids,
                        SUM(cle.paid_amount) AS calculation_base_amount,
                        SUM(sfl.paid_amount) AS paid_amount,
                        (ARRAY_AGG(sfl.attributed_project_id ORDER BY sfl.service_fee_entry_id))[1]
                            AS attributed_project_id,
                        (ARRAY_AGG(sfl.attributed_operator_party_id ORDER BY sfl.service_fee_entry_id))[1]
                            AS attributed_operator_party_id,
                        (ARRAY_AGG(sfl.attributed_asset_ids ORDER BY sfl.service_fee_entry_id))[1]
                            AS attributed_asset_ids
                    FROM service_fee_ledgers AS sfl
                    JOIN contract_ledger_entries AS cle
                      ON cle.entry_id = sfl.source_ledger_id
                    WHERE sfl.source_ledger_id IS NOT NULL
                    GROUP BY
                        sfl.contract_group_id,
                        sfl.agency_agreement_contract_id,
                        sfl.attributed_owner_party_id,
                        sfl.year_month
                )
                UPDATE service_fee_ledgers AS sfl
                SET agency_contract_id = grouped.agency_contract_id,
                    source_ledger_ids = grouped.source_ledger_ids,
                    calculation_base_amount = grouped.calculation_base_amount,
                    amount_due = ROUND(grouped.calculation_base_amount * grouped.service_fee_ratio, 2),
                    paid_amount = grouped.paid_amount,
                    currency_code = grouped.currency_code,
                    service_fee_ratio = grouped.service_fee_ratio,
                    attributed_project_id = grouped.attributed_project_id,
                    attributed_operator_party_id = grouped.attributed_operator_party_id,
                    attributed_asset_ids = grouped.attributed_asset_ids,
                    updated_at = NOW()
                FROM grouped
                WHERE sfl.service_fee_entry_id = grouped.canonical_id
                """
            )
        )
        bind.execute(
            sa.text(
                """
                WITH grouped AS (
                    SELECT
                        MIN(service_fee_entry_id) AS canonical_id,
                        contract_group_id,
                        agency_agreement_contract_id,
                        attributed_owner_party_id,
                        year_month
                    FROM service_fee_ledgers
                    WHERE source_ledger_id IS NOT NULL
                    GROUP BY
                        contract_group_id,
                        agency_agreement_contract_id,
                        attributed_owner_party_id,
                        year_month
                )
                DELETE FROM service_fee_ledgers AS sfl
                USING grouped
                WHERE sfl.source_ledger_id IS NOT NULL
                  AND sfl.contract_group_id = grouped.contract_group_id
                  AND sfl.agency_agreement_contract_id = grouped.agency_agreement_contract_id
                  AND sfl.attributed_owner_party_id IS NOT DISTINCT FROM grouped.attributed_owner_party_id
                  AND sfl.year_month = grouped.year_month
                  AND sfl.service_fee_entry_id <> grouped.canonical_id
                """
            )
        )


def _backfill_payment_allocations(inspector: sa.engine.reflection.Inspector) -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            INSERT INTO operational_payment_flows (
                flow_id, flow_type, occurred_on, amount, registered_by,
                counterparty_id, voucher_attachment_ids, notes, status, created_at, updated_at
            )
            SELECT
                'backfill-rent-' || cle.entry_id,
                CASE
                    WHEN cle.ledger_views ? 'operator_cost' THEN 'upstream_cost_payment'
                    ELSE 'terminal_rent_receipt'
                END,
                cle.due_date,
                cle.paid_amount,
                'system_migration',
                NULL,
                NULL,
                'system migration backfill from paid_amount',
                'active',
                NOW(),
                NOW()
            FROM contract_ledger_entries AS cle
            WHERE cle.paid_amount > 0
              AND cle.payment_status <> 'voided'
            ON CONFLICT (flow_id) DO NOTHING
            """
        )
    )
    bind.execute(
        sa.text(
            """
            INSERT INTO payment_allocations (
                allocation_id, flow_id, target_type, target_id, year_month, amount, created_at, updated_at
            )
            SELECT
                'backfill-rent-alloc-' || cle.entry_id,
                'backfill-rent-' || cle.entry_id,
                'contract_ledger_entry',
                cle.entry_id,
                cle.year_month,
                cle.paid_amount,
                NOW(),
                NOW()
            FROM contract_ledger_entries AS cle
            WHERE cle.paid_amount > 0
              AND cle.payment_status <> 'voided'
            ON CONFLICT (allocation_id) DO NOTHING
            """
        )
    )

    if inspector.has_table("service_fee_ledgers"):
        bind.execute(
            sa.text(
                """
                INSERT INTO operational_payment_flows (
                    flow_id, flow_type, occurred_on, amount, registered_by,
                    counterparty_id, voucher_attachment_ids, notes, status, created_at, updated_at
                )
                SELECT
                    'backfill-service-fee-' || sfl.service_fee_entry_id,
                    'service_fee_receipt',
                    TO_DATE(sfl.year_month || '-01', 'YYYY-MM-DD'),
                    sfl.paid_amount,
                    'system_migration',
                    NULL,
                    NULL,
                    'system migration backfill from service_fee paid_amount',
                    'active',
                    NOW(),
                    NOW()
                FROM service_fee_ledgers AS sfl
                WHERE sfl.paid_amount > 0
                  AND sfl.payment_status <> 'voided'
                ON CONFLICT (flow_id) DO NOTHING
                """
            )
        )
        bind.execute(
            sa.text(
                """
                INSERT INTO payment_allocations (
                    allocation_id, flow_id, target_type, target_id, year_month, amount, created_at, updated_at
                )
                SELECT
                    'backfill-service-fee-alloc-' || sfl.service_fee_entry_id,
                    'backfill-service-fee-' || sfl.service_fee_entry_id,
                    'service_fee_ledger',
                    sfl.service_fee_entry_id,
                    sfl.year_month,
                    sfl.paid_amount,
                    NOW(),
                    NOW()
                FROM service_fee_ledgers AS sfl
                WHERE sfl.paid_amount > 0
                  AND sfl.payment_status <> 'voided'
                ON CONFLICT (allocation_id) DO NOTHING
                """
            )
        )

    missing_rent_allocations = bind.execute(
        sa.text(
            """
            SELECT COUNT(*)
            FROM contract_ledger_entries AS cle
            WHERE cle.paid_amount > 0
              AND cle.payment_status <> 'voided'
              AND NOT EXISTS (
                  SELECT 1
                  FROM payment_allocations AS pa
                  JOIN operational_payment_flows AS opf ON opf.flow_id = pa.flow_id
                  WHERE pa.target_type = 'contract_ledger_entry'
                    AND pa.target_id = cle.entry_id
                    AND opf.status = 'active'
              )
            """
        )
    ).scalar()
    if missing_rent_allocations:
        raise RuntimeError(
            "contract_ledger_entries has paid_amount rows without PaymentAllocation"
        )

    if inspector.has_table("service_fee_ledgers"):
        missing_service_fee_allocations = bind.execute(
            sa.text(
                """
                SELECT COUNT(*)
                FROM service_fee_ledgers AS sfl
                WHERE sfl.paid_amount > 0
                  AND sfl.payment_status <> 'voided'
                  AND NOT EXISTS (
                      SELECT 1
                      FROM payment_allocations AS pa
                      JOIN operational_payment_flows AS opf ON opf.flow_id = pa.flow_id
                      WHERE pa.target_type = 'service_fee_ledger'
                        AND pa.target_id = sfl.service_fee_entry_id
                        AND opf.status = 'active'
                  )
                """
            )
        ).scalar()
        if missing_service_fee_allocations:
            raise RuntimeError(
                "service_fee_ledgers has paid_amount rows without PaymentAllocation"
            )


def _finalize_constraints(inspector: sa.engine.reflection.Inspector) -> None:
    if inspector.has_table("contract_ledger_entries"):
        op.alter_column(
            "contract_ledger_entries",
            "ledger_views",
            existing_type=postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=None,
        )
        if not _constraint_exists(
            inspector,
            "contract_ledger_entries",
            "ck_contract_ledger_entry_ledger_views_array",
        ):
            op.create_check_constraint(
                "ck_contract_ledger_entry_ledger_views_array",
                "contract_ledger_entries",
                "jsonb_typeof(ledger_views) = 'array'",
            )
        if not _constraint_exists(
            inspector,
            "contract_ledger_entries",
            "ck_contract_ledger_entry_follow_up_status",
        ):
            op.create_check_constraint(
                "ck_contract_ledger_entry_follow_up_status",
                "contract_ledger_entries",
                "follow_up_status IS NULL OR follow_up_status IN "
                "('pending_follow_up', 'contacted', 'promised_payment', "
                "'disputed', 'offline_received_pending_entry', 'deferred')",
            )

    if inspector.has_table("service_fee_ledgers"):
        for column_name, existing_type in [
            ("agency_agreement_contract_id", sa.String()),
            ("source_ledger_ids", postgresql.JSONB(astext_type=sa.Text())),
            ("calculation_base_amount", sa.DECIMAL(15, 2)),
        ]:
            op.alter_column(
                "service_fee_ledgers",
                column_name,
                existing_type=existing_type,
                nullable=False,
                server_default=None,
            )
        if not _constraint_exists(
            inspector, "service_fee_ledgers", "fk_service_fee_ledger_agreement"
        ):
            op.create_foreign_key(
                "fk_service_fee_ledger_agreement",
                "service_fee_ledgers",
                "contracts",
                ["agency_agreement_contract_id"],
                ["contract_id"],
            )
        if not _constraint_exists(
            inspector, "service_fee_ledgers", "ck_service_fee_ledger_source_ids_array"
        ):
            op.create_check_constraint(
                "ck_service_fee_ledger_source_ids_array",
                "service_fee_ledgers",
                "jsonb_typeof(source_ledger_ids) = 'array'",
            )
        if not _constraint_exists(
            inspector,
            "service_fee_ledgers",
            "ck_service_fee_ledger_calculation_base_nonnegative",
        ):
            op.create_check_constraint(
                "ck_service_fee_ledger_calculation_base_nonnegative",
                "service_fee_ledgers",
                "calculation_base_amount >= 0",
            )
        if _constraint_exists(
            inspector, "service_fee_ledgers", "uq_service_fee_ledger_source"
        ):
            op.drop_constraint(
                "uq_service_fee_ledger_source",
                "service_fee_ledgers",
                type_="unique",
            )
        if not _constraint_exists(
            inspector, "service_fee_ledgers", "uq_service_fee_ledger_monthly_scope"
        ):
            op.create_unique_constraint(
                "uq_service_fee_ledger_monthly_scope",
                "service_fee_ledgers",
                [
                    "contract_group_id",
                    "agency_agreement_contract_id",
                    "attributed_owner_party_id",
                    "year_month",
                ],
            )
        if _constraint_exists(
            inspector, "service_fee_ledgers", "fk_service_fee_ledger_source"
        ):
            op.drop_constraint(
                "fk_service_fee_ledger_source",
                "service_fee_ledgers",
                type_="foreignkey",
            )
        if _table_has_column(inspector, "service_fee_ledgers", "source_ledger_id"):
            op.drop_column("service_fee_ledgers", "source_ledger_id")


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    _add_contract_ledger_columns(inspector)
    _add_service_fee_columns(inspector)
    inspector = sa.inspect(bind)
    _create_payment_tables(inspector)
    inspector = sa.inspect(bind)
    _backfill_ledger_views()
    _backfill_service_fee_ledgers(inspector)
    _backfill_payment_allocations(inspector)
    inspector = sa.inspect(bind)
    _finalize_constraints(inspector)


def downgrade() -> None:
    raise RuntimeError("operations ledger foundation is not downgraded")
