"""Extend attachment constraints for import batch originals and xlsx files."""

from alembic import op

revision = "20261115b_import_attachment_types"
down_revision = "20261115_import_batches"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_attachment_owner_type", "attachments", type_="check")
    op.create_check_constraint(
        "ck_attachment_owner_type",
        "attachments",
        "owner_type IN ('asset', 'contract', 'property_certificate', "
        "'payment_flow', 'management_fee_statement', 'import_batch')",
    )
    op.drop_constraint("ck_attachment_file_type", "attachments", type_="check")
    op.create_check_constraint(
        "ck_attachment_file_type",
        "attachments",
        "file_type IN ('pdf', 'jpg', 'jpeg', 'png', 'xlsx')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_attachment_file_type", "attachments", type_="check")
    op.create_check_constraint(
        "ck_attachment_file_type",
        "attachments",
        "file_type IN ('pdf', 'jpg', 'jpeg', 'png')",
    )
    op.drop_constraint("ck_attachment_owner_type", "attachments", type_="check")
    op.create_check_constraint(
        "ck_attachment_owner_type",
        "attachments",
        "owner_type IN ('asset', 'contract', 'property_certificate', "
        "'payment_flow', 'management_fee_statement')",
    )
