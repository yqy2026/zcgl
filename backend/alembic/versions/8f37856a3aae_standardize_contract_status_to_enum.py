"""standardize_contract_status_to_enum

Revision ID: 8f37856a3aae
Revises: ca5d6adb0012
Create Date: 2026-01-24 20:52:35.669980

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text


# revision identifiers, used by Alembic.
revision: str = '8f37856a3aae'
down_revision: Union[str, None] = 'ca5d6adb0012'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Update existing statuses to English Enum values

    # "有效" -> "ACTIVE"
    op.execute(text("UPDATE rent_contracts SET contract_status = 'ACTIVE' WHERE contract_status = '有效'"))

    # "到期", "已到期" -> "EXPIRED"
    op.execute(text("UPDATE rent_contracts SET contract_status = 'EXPIRED' WHERE contract_status IN ('到期', '已到期')"))

    # "终止", "已终止" -> "TERMINATED"
    op.execute(text("UPDATE rent_contracts SET contract_status = 'TERMINATED' WHERE contract_status IN ('终止', '已终止')"))

    # "已续签" -> "RENEWED"
    op.execute(text("UPDATE rent_contracts SET contract_status = 'RENEWED' WHERE contract_status = '已续签'"))


def downgrade() -> None:
    """Downgrade schema."""
    # Revert back to Chinese (Best effort)
    op.execute(text("UPDATE rent_contracts SET contract_status = '有效' WHERE contract_status = 'ACTIVE'"))
    op.execute(text("UPDATE rent_contracts SET contract_status = '到期' WHERE contract_status = 'EXPIRED'"))
    op.execute(text("UPDATE rent_contracts SET contract_status = '已终止' WHERE contract_status = 'TERMINATED'"))
    op.execute(text("UPDATE rent_contracts SET contract_status = '已续签' WHERE contract_status = 'RENEWED'"))
    op.execute(text("UPDATE rent_contracts SET contract_status = '草稿' WHERE contract_status = 'DRAFT'"))
