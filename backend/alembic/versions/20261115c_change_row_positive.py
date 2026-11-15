"""Allow row_number 0 for file-level import issues."""

from alembic import op

revision = "20261115c_change_row_positive"
down_revision = "20261115b_import_attachment_types"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_import_batch_changes_row_positive",
        "import_batch_changes",
        type_="check",
    )
    op.create_check_constraint(
        "ck_import_batch_changes_row_positive",
        "import_batch_changes",
        "row_number >= 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_import_batch_changes_row_positive",
        "import_batch_changes",
        type_="check",
    )
    op.create_check_constraint(
        "ck_import_batch_changes_row_positive",
        "import_batch_changes",
        "row_number > 0",
    )
