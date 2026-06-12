"""drop property certificate is_verified flag

Revision ID: 20260611_drop_property_certificate_is_verified
Revises: 20260611_contract_group_nullable_rule_drop_versions
Create Date: 2026-06-11 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260611_drop_property_certificate_is_verified"
down_revision: str | None = "20260611_contract_group_nullable_rule_drop_versions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _column_exists(
    inspector: sa.engine.reflection.Inspector,
    table_name: str,
    column_name: str,
) -> bool:
    if not inspector.has_table(table_name):
        return False
    return any(
        column["name"] == column_name for column in inspector.get_columns(table_name)
    )


def upgrade() -> None:
    """Remove the retired manual verification flag from property certificates."""
    inspector = sa.inspect(op.get_bind())
    if _column_exists(inspector, "property_certificates", "verified"):
        op.drop_column("property_certificates", "verified")


def downgrade() -> None:
    """Restore the retired manual verification flag."""
    inspector = sa.inspect(op.get_bind())
    if not _column_exists(inspector, "property_certificates", "verified"):
        op.add_column(
            "property_certificates",
            sa.Column(
                "verified",
                sa.Boolean(),
                nullable=True,
                server_default=sa.false(),
                comment="manual verification flag",
            ),
        )
