"""Drop historical SaaS tenant_id columns.

This migration removes legacy `tenant_id` columns from `assets` and
`rent_contracts`. The project runtime permission model is organization-scoped
instead of SaaS multi-tenant scoped.

Note:
- `downgrade()` re-adds the columns only for Alembic rollback compatibility.
- Runtime code should not depend on these columns.
"""

import sqlalchemy as sa

from alembic import op

revision: str = "20260130_drop_tenant_id_columns"
down_revision: str | None = "752cb03b2555"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.drop_column("assets", "tenant_id")
    op.drop_column("rent_contracts", "tenant_id")


def downgrade() -> None:
    op.add_column("assets", sa.Column("tenant_id", sa.String(50), nullable=True))
    op.add_column(
        "rent_contracts", sa.Column("tenant_id", sa.String(50), nullable=True)
    )
