"""Allow attachments owned by management fee statements.

Revision ID: 20261029_fee_attachments
Revises: 20261029_fee_deferrals
"""

from alembic import op

revision = "20261029_fee_attachments"
down_revision = "20261029_fee_deferrals"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_attachment_owner_type", "attachments", type_="check")
    op.create_check_constraint(
        "ck_attachment_owner_type",
        "attachments",
        "owner_type IN ('asset', 'contract', 'property_certificate', 'payment_flow', 'management_fee_statement')",
    )


def downgrade() -> None:
    raise RuntimeError(
        "Management fee attachments preserve append-only confirmation evidence; use a corrective migration"
    )
