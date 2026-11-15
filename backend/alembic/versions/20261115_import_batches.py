"""Register import batches and per-row change facts for the V4-3 import."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20261115_import_batches"
down_revision = "20261104_fee_stamp_archive"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "import_batches",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("mode", sa.String(10), nullable=False),
        sa.Column("status", sa.String(12), nullable=False, server_default="uploaded"),
        sa.Column(
            "file_document_id",
            sa.String(36),
            sa.ForeignKey("attachments.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("template_version", sa.String(20), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("valid_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("warning_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("proposal_hash", sa.String(64)),
        sa.Column("committed_at", sa.DateTime(timezone=True)),
        sa.Column("committed_by", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column("reverted_at", sa.DateTime(timezone=True)),
        sa.Column("reverted_by", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column("revert_reason", sa.Text()),
        sa.Column("idempotency_key", sa.String(100)),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "mode IN ('create', 'update')", name="ck_import_batches_mode"
        ),
        sa.CheckConstraint(
            "status IN ('uploaded', 'validating', 'invalid', 'ready', "
            "'committed', 'reverted')",
            name="ck_import_batches_status",
        ),
        sa.CheckConstraint(
            "row_count >= 0 AND valid_count >= 0 AND error_count >= 0 "
            "AND warning_count >= 0",
            name="ck_import_batches_counts_nonnegative",
        ),
        sa.CheckConstraint(
            "status <> 'committed' "
            "OR (committed_at IS NOT NULL AND committed_by IS NOT NULL)",
            name="ck_import_batches_commit_audit",
        ),
        sa.CheckConstraint(
            "status <> 'reverted' "
            "OR (reverted_at IS NOT NULL AND reverted_by IS NOT NULL "
            "AND revert_reason IS NOT NULL)",
            name="ck_import_batches_revert_audit",
        ),
    )
    op.create_index(
        "uq_import_batches_commit_idempotency",
        "import_batches",
        ["committed_by", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )

    op.create_table(
        "import_batch_changes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "batch_id",
            sa.String(36),
            sa.ForeignKey("import_batches.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sheet_name", sa.String(20), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("target_type", sa.String(20), nullable=False),
        sa.Column("target_key", sa.String(200), nullable=False),
        sa.Column("field_name", sa.String(50), nullable=False),
        sa.Column(
            "old_value", sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
        ),
        sa.Column(
            "new_value", sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
        ),
        sa.Column("selected", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("severity", sa.String(10), nullable=False, server_default="change"),
        sa.Column("effect_summary", sa.Text(), nullable=False, server_default=""),
        sa.CheckConstraint(
            "severity IN ('change', 'warning', 'error')",
            name="ck_import_batch_changes_severity",
        ),
        sa.CheckConstraint(
            "target_type IN ('asset_unit', 'upstream_contract', 'terminal_contract')",
            name="ck_import_batch_changes_target_type",
        ),
        sa.CheckConstraint(
            "row_number >= 0", name="ck_import_batch_changes_row_positive"
        ),
        sa.UniqueConstraint(
            "batch_id",
            "row_number",
            "target_key",
            "field_name",
            name="uq_import_batch_changes_row_field",
        ),
    )
    op.create_index(
        "ix_import_batch_changes_batch_id", "import_batch_changes", ["batch_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_import_batch_changes_batch_id", table_name="import_batch_changes")
    op.drop_table("import_batch_changes")
    op.drop_index("uq_import_batches_commit_idempotency", table_name="import_batches")
    op.drop_table("import_batches")
