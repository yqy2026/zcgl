"""merge_heads_before_ocr_cleanup

Revision ID: 345d5f07ee41
Revises: 20260130_drop_tenant_id_columns, b5a7c4d9e2f1
Create Date: 2026-01-31 21:45:36.987274

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '345d5f07ee41'
down_revision: Union[str, None] = ('20260130_drop_tenant_id_columns', 'b5a7c4d9e2f1')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
