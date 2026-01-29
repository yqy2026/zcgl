"""standardize_contract_status_to_enum

Revision ID: 8f37856a3aae
Revises: ca5d6adb0012
Create Date: 2026-01-24 20:52:35.669980

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8f37856a3aae"
down_revision: str | None = "ca5d6adb0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Define a temporary table representation for the update
    rent_contracts = sa.table(
        "rent_contracts",
        sa.column("contract_status", sa.String),
    )

    # 1. Update existing statuses to English Enum values using SQLAlchemy constructs
    # This avoids raw SQL strings and potential SQL injection risks, maintaining the abstraction layer

    # "有效" -> "ACTIVE"
    op.execute(
        rent_contracts.update()
        .where(rent_contracts.c.contract_status == "有效")
        .values(contract_status="ACTIVE")
    )

    # "到期", "已到期" -> "EXPIRED"
    op.execute(
        rent_contracts.update()
        .where(rent_contracts.c.contract_status.in_(["到期", "已到期"]))
        .values(contract_status="EXPIRED")
    )

    # "终止", "已终止" -> "TERMINATED"
    op.execute(
        rent_contracts.update()
        .where(rent_contracts.c.contract_status.in_(["终止", "已终止"]))
        .values(contract_status="TERMINATED")
    )

    # "已续签" -> "RENEWED"
    op.execute(
        rent_contracts.update()
        .where(rent_contracts.c.contract_status == "已续签")
        .values(contract_status="RENEWED")
    )


def downgrade() -> None:
    """Downgrade schema."""
    rent_contracts = sa.table(
        "rent_contracts",
        sa.column("contract_status", sa.String),
    )

    # Revert back to Chinese (Best effort)
    op.execute(
        rent_contracts.update()
        .where(rent_contracts.c.contract_status == "ACTIVE")
        .values(contract_status="有效")
    )

    op.execute(
        rent_contracts.update()
        .where(rent_contracts.c.contract_status == "EXPIRED")
        .values(contract_status="到期")
    )

    op.execute(
        rent_contracts.update()
        .where(rent_contracts.c.contract_status == "TERMINATED")
        .values(contract_status="已终止")
    )

    op.execute(
        rent_contracts.update()
        .where(rent_contracts.c.contract_status == "RENEWED")
        .values(contract_status="已续签")
    )

    # Handle DRAFT which might have been introduced
    op.execute(
        rent_contracts.update()
        .where(rent_contracts.c.contract_status == "DRAFT")
        .values(contract_status="草稿")
    )
