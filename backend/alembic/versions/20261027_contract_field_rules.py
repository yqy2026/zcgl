"""enforce management agreement field rules

Revision ID: 20261027_contract_field_rules
Revises: 20261024_asset_contract_write_receipts
Create Date: 2026-10-27
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261027_contract_field_rules"
down_revision: str | Sequence[str] | None = "20261024_asset_contract_write_receipts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    invalid = (
        op.get_bind()
        .execute(
            sa.text("""
        SELECT c.id, c.contract_number,
               c.deposit_amount <> 0 AS has_deposit,
               EXISTS (
                   SELECT 1 FROM contract_rent_schedules s
                   WHERE s.contract_kind = 'upstream' AND s.contract_id = c.id
               ) AS has_rent_schedules
        FROM upstream_contracts c
        WHERE c.contract_type = 'management_agreement'
          AND (c.deposit_amount <> 0 OR EXISTS (
              SELECT 1 FROM contract_rent_schedules s
              WHERE s.contract_kind = 'upstream' AND s.contract_id = c.id
          ))
        ORDER BY c.id
    """)
        )
        .mappings()
        .all()
    )
    if invalid:
        raise RuntimeError(
            "Management agreements have inapplicable deposit or rent schedules; "
            "correct these contracts before retrying: "
            + repr([dict(row) for row in invalid])
        )
    op.create_check_constraint(
        "ck_upstream_contracts_management_deposit_zero",
        "upstream_contracts",
        "contract_type = 'lease' OR deposit_amount = 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_upstream_contracts_management_deposit_zero",
        "upstream_contracts",
        type_="check",
    )
