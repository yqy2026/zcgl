"""Create asset-operations v5 signed-contract fact tables.

Revision ID: 20261023_asset_operations_v5_contracts
Revises: 20261023_asset_operations_v5_asset_units
Create Date: 2026-10-23
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261023_asset_operations_v5_contracts"
down_revision: str | Sequence[str] | None = (
    "20261023_asset_operations_v5_asset_units"
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "upstream_contracts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("contract_number", sa.String(length=100), nullable=False),
        sa.Column("contract_type", sa.String(length=30), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("owner_party_id", sa.String(), nullable=False),
        sa.Column("operator_party_id", sa.String(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("payment_cycle", sa.String(length=20), nullable=True),
        sa.Column("payment_day", sa.Integer(), nullable=True),
        sa.Column("management_fee_rate", sa.Numeric(9, 6), nullable=True),
        sa.Column(
            "deposit_amount",
            sa.Numeric(14, 2),
            nullable=False,
            server_default="0",
        ),
        sa.Column("oa_reference", sa.String(length=100), nullable=True),
        sa.Column("renewed_from_id", sa.String(length=36), nullable=True),
        sa.Column("scan_document_id", sa.String(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")
        ),
        sa.CheckConstraint(
            "contract_type IN ('lease', 'management_agreement')",
            name="ck_upstream_contracts_type",
        ),
        sa.CheckConstraint(
            "end_date >= start_date",
            name="ck_upstream_contracts_date_range",
        ),
        sa.CheckConstraint(
            "(contract_type = 'lease' "
            "AND payment_cycle IN ('monthly', 'quarterly', 'yearly', 'custom') "
            "AND management_fee_rate IS NULL) OR "
            "(contract_type = 'management_agreement' "
            "AND payment_cycle IS NULL AND payment_day IS NULL "
            "AND management_fee_rate IS NOT NULL)",
            name="ck_upstream_contracts_payment_terms",
        ),
        sa.CheckConstraint(
            "payment_day IS NULL OR payment_day BETWEEN 1 AND 31",
            name="ck_upstream_contracts_payment_day",
        ),
        sa.CheckConstraint(
            "management_fee_rate IS NULL OR "
            "(management_fee_rate >= 0 AND management_fee_rate <= 1)",
            name="ck_upstream_contracts_management_fee_rate",
        ),
        sa.CheckConstraint(
            "deposit_amount >= 0",
            name="ck_upstream_contracts_deposit_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["owner_party_id"], ["parties.id"], name="fk_upstream_contracts_owner"
        ),
        sa.ForeignKeyConstraint(
            ["operator_party_id"],
            ["parties.id"],
            name="fk_upstream_contracts_operator",
        ),
        sa.ForeignKeyConstraint(
            ["renewed_from_id"],
            ["upstream_contracts.id"],
            name="fk_upstream_contracts_renewed_from",
        ),
        sa.ForeignKeyConstraint(
            ["scan_document_id"],
            ["attachments.id"],
            name="fk_upstream_contracts_scan_document",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_upstream_contracts"),
        sa.UniqueConstraint(
            "contract_number", name="uq_upstream_contracts_contract_number"
        ),
    )
    op.create_index(
        "ix_upstream_contracts_owner_party_id",
        "upstream_contracts",
        ["owner_party_id"],
    )
    op.create_index(
        "ix_upstream_contracts_operator_party_id",
        "upstream_contracts",
        ["operator_party_id"],
    )
    op.create_index(
        "ix_upstream_contracts_start_date", "upstream_contracts", ["start_date"]
    )
    op.create_index(
        "ix_upstream_contracts_end_date", "upstream_contracts", ["end_date"]
    )
    op.create_index(
        "ix_upstream_contracts_renewed_from_id",
        "upstream_contracts",
        ["renewed_from_id"],
    )
    op.create_index(
        "ix_upstream_contracts_scan_document_id",
        "upstream_contracts",
        ["scan_document_id"],
    )

    op.create_table(
        "terminal_contracts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("contract_number", sa.String(length=100), nullable=False),
        sa.Column("contract_mode", sa.String(length=20), nullable=False),
        sa.Column("tenant_party_id", sa.String(), nullable=False),
        sa.Column("lessor_party_id", sa.String(), nullable=False),
        sa.Column("upstream_contract_id", sa.String(length=36), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("deposit_months", sa.Numeric(8, 2), nullable=True),
        sa.Column(
            "deposit_amount",
            sa.Numeric(14, 2),
            nullable=False,
            server_default="0",
        ),
        sa.Column("rent_collector", sa.String(length=20), nullable=False),
        sa.Column("renewed_from_id", sa.String(length=36), nullable=True),
        sa.Column("scan_document_id", sa.String(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")
        ),
        sa.CheckConstraint(
            "contract_mode IN ('sublease', 'direct_lease')",
            name="ck_terminal_contracts_mode",
        ),
        sa.CheckConstraint(
            "end_date >= start_date",
            name="ck_terminal_contracts_date_range",
        ),
        sa.CheckConstraint(
            "(contract_mode = 'sublease' AND rent_collector = 'operator') OR "
            "(contract_mode = 'direct_lease' AND rent_collector = 'owner')",
            name="ck_terminal_contracts_rent_collector",
        ),
        sa.CheckConstraint(
            "deposit_months IS NULL OR deposit_months >= 0",
            name="ck_terminal_contracts_deposit_months_nonnegative",
        ),
        sa.CheckConstraint(
            "deposit_amount >= 0",
            name="ck_terminal_contracts_deposit_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_party_id"], ["parties.id"], name="fk_terminal_contracts_tenant"
        ),
        sa.ForeignKeyConstraint(
            ["lessor_party_id"], ["parties.id"], name="fk_terminal_contracts_lessor"
        ),
        sa.ForeignKeyConstraint(
            ["upstream_contract_id"],
            ["upstream_contracts.id"],
            name="fk_terminal_contracts_upstream",
        ),
        sa.ForeignKeyConstraint(
            ["renewed_from_id"],
            ["terminal_contracts.id"],
            name="fk_terminal_contracts_renewed_from",
        ),
        sa.ForeignKeyConstraint(
            ["scan_document_id"],
            ["attachments.id"],
            name="fk_terminal_contracts_scan_document",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_terminal_contracts"),
        sa.UniqueConstraint(
            "contract_number", name="uq_terminal_contracts_contract_number"
        ),
    )
    for column in (
        "tenant_party_id",
        "lessor_party_id",
        "upstream_contract_id",
        "start_date",
        "end_date",
        "renewed_from_id",
        "scan_document_id",
    ):
        op.create_index(
            f"ix_terminal_contracts_{column}", "terminal_contracts", [column]
        )

    op.create_table(
        "upstream_contract_asset_units",
        sa.Column("upstream_contract_id", sa.String(length=36), nullable=False),
        sa.Column("asset_unit_id", sa.String(length=36), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="ck_upstream_contract_asset_units_effective_range",
        ),
        sa.ForeignKeyConstraint(
            ["upstream_contract_id"],
            ["upstream_contracts.id"],
            name="fk_upstream_contract_asset_units_contract",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["asset_unit_id"],
            ["asset_units.id"],
            name="fk_upstream_contract_asset_units_unit",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "upstream_contract_id",
            "asset_unit_id",
            name="pk_upstream_contract_asset_units",
        ),
    )
    op.create_index(
        "ix_upstream_contract_asset_units_unit",
        "upstream_contract_asset_units",
        ["asset_unit_id"],
    )

    op.create_table(
        "terminal_contract_asset_units",
        sa.Column("terminal_contract_id", sa.String(length=36), nullable=False),
        sa.Column("asset_unit_id", sa.String(length=36), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="ck_terminal_contract_asset_units_effective_range",
        ),
        sa.ForeignKeyConstraint(
            ["terminal_contract_id"],
            ["terminal_contracts.id"],
            name="fk_terminal_contract_asset_units_contract",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["asset_unit_id"],
            ["asset_units.id"],
            name="fk_terminal_contract_asset_units_unit",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "terminal_contract_id",
            "asset_unit_id",
            name="pk_terminal_contract_asset_units",
        ),
    )
    op.create_index(
        "ix_terminal_contract_asset_units_unit",
        "terminal_contract_asset_units",
        ["asset_unit_id"],
    )
    op.execute(
        """
        ALTER TABLE terminal_contract_asset_units
        ADD CONSTRAINT ex_terminal_contract_asset_units_unit_period
        EXCLUDE USING gist (
            asset_unit_id WITH =,
            daterange(
                effective_from,
                COALESCE(effective_to, 'infinity'::date),
                '[]'
            ) WITH &&
        )
        """
    )

    op.create_table(
        "contract_rent_schedules",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("contract_kind", sa.String(length=20), nullable=False),
        sa.Column("contract_id", sa.String(length=36), nullable=False),
        sa.Column("stage_start", sa.Date(), nullable=False),
        sa.Column("stage_end", sa.Date(), nullable=False),
        sa.Column("base_monthly_rent", sa.Numeric(14, 2), nullable=False),
        sa.Column(
            "increase_rate", sa.Numeric(9, 6), nullable=False, server_default="0"
        ),
        sa.Column(
            "free_rent_months",
            sa.Numeric(8, 2),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "discount_amount",
            sa.Numeric(14, 2),
            nullable=False,
            server_default="0",
        ),
        sa.Column("actual_monthly_rent", sa.Numeric(14, 2), nullable=False),
        sa.Column("payment_cycle", sa.String(length=20), nullable=False),
        sa.Column("due_day", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "contract_kind IN ('upstream', 'terminal')",
            name="ck_contract_rent_schedules_kind",
        ),
        sa.CheckConstraint(
            "stage_end >= stage_start",
            name="ck_contract_rent_schedules_stage_range",
        ),
        sa.CheckConstraint(
            "base_monthly_rent >= 0 AND increase_rate >= 0 "
            "AND free_rent_months >= 0 AND discount_amount >= 0 "
            "AND actual_monthly_rent >= 0",
            name="ck_contract_rent_schedules_amounts_nonnegative",
        ),
        sa.CheckConstraint(
            "payment_cycle IN ('monthly', 'quarterly', 'yearly', 'custom')",
            name="ck_contract_rent_schedules_payment_cycle",
        ),
        sa.CheckConstraint(
            "due_day BETWEEN 1 AND 31",
            name="ck_contract_rent_schedules_due_day",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_contract_rent_schedules"),
        sa.UniqueConstraint(
            "contract_kind",
            "contract_id",
            "stage_start",
            name="uq_contract_rent_schedules_target_stage",
        ),
    )
    op.create_index(
        "ix_contract_rent_schedules_target",
        "contract_rent_schedules",
        ["contract_kind", "contract_id"],
    )

    op.create_table(
        "contract_lifecycle_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("contract_kind", sa.String(length=20), nullable=False),
        sa.Column("contract_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=20), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("termination_type", sa.String(length=20), nullable=True),
        sa.Column("handover_status", sa.String(length=20), nullable=True),
        sa.Column("deposit_settlement_status", sa.String(length=20), nullable=True),
        sa.Column("successor_contract_id", sa.String(length=36), nullable=True),
        sa.Column("reversed_event_id", sa.String(length=36), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")
        ),
        sa.Column("idempotency_key", sa.String(length=100), nullable=False),
        sa.CheckConstraint(
            "contract_kind IN ('upstream', 'terminal')",
            name="ck_contract_lifecycle_events_kind",
        ),
        sa.CheckConstraint(
            "event_type IN ('renewed', 'terminated', 'exited', 'reversed')",
            name="ck_contract_lifecycle_events_type",
        ),
        sa.CheckConstraint(
            "(event_type = 'terminated' AND contract_kind = 'terminal') OR "
            "(event_type = 'exited' AND contract_kind = 'upstream') OR "
            "event_type IN ('renewed', 'reversed')",
            name="ck_contract_lifecycle_events_target_compatibility",
        ),
        sa.CheckConstraint(
            "(event_type = 'renewed' AND successor_contract_id IS NOT NULL "
            "AND successor_contract_id <> contract_id) OR "
            "(event_type <> 'renewed' AND successor_contract_id IS NULL)",
            name="ck_contract_lifecycle_events_successor",
        ),
        sa.CheckConstraint(
            "(event_type = 'reversed' AND reversed_event_id IS NOT NULL) OR "
            "(event_type <> 'reversed' AND reversed_event_id IS NULL)",
            name="ck_contract_lifecycle_events_reversal",
        ),
        sa.CheckConstraint(
            "event_type = 'renewed' OR "
            "(reason IS NOT NULL AND length(trim(reason)) > 0)",
            name="ck_contract_lifecycle_events_reason",
        ),
        sa.CheckConstraint(
            "termination_type IS NULL OR "
            "termination_type IN ('expiry', 'early', 'mutual')",
            name="ck_contract_lifecycle_events_termination_type",
        ),
        sa.CheckConstraint(
            "handover_status IS NULL OR "
            "handover_status IN ('pending', 'completed', 'not_applicable')",
            name="ck_contract_lifecycle_events_handover_status",
        ),
        sa.CheckConstraint(
            "deposit_settlement_status IS NULL OR deposit_settlement_status IN "
            "('pending', 'settled', 'not_applicable')",
            name="ck_contract_lifecycle_events_deposit_status",
        ),
        sa.ForeignKeyConstraint(
            ["reversed_event_id"],
            ["contract_lifecycle_events.id"],
            name="fk_contract_lifecycle_events_reversed_event",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="fk_contract_lifecycle_events_created_by"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_contract_lifecycle_events"),
        sa.UniqueConstraint(
            "idempotency_key",
            name="uq_contract_lifecycle_events_idempotency_key",
        ),
    )
    op.create_index(
        "ix_contract_lifecycle_events_target",
        "contract_lifecycle_events",
        ["contract_kind", "contract_id", "effective_date"],
    )


def downgrade() -> None:
    raise RuntimeError(
        "asset-operations v5 contract schema is irreversible; "
        "roll forward with a corrective migration"
    )
