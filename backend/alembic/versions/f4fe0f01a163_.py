"""empty message

Revision ID: f4fe0f01a163
Revises: 20250118_add_property_cert_tables, e4c9e4968dd7
Create Date: 2026-01-18 12:10:12.661993

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f4fe0f01a163'
down_revision: Union[str, None] = ('20250118_add_property_cert_tables', 'e4c9e4968dd7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
