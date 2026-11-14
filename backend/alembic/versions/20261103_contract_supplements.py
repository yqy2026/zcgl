"""Register contract supplements as independent business requirements."""

import sqlalchemy as sa

from alembic import op

revision = "20261103_contract_supplements"
down_revision = "20261102_archive_documents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "contract_supplements",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("contract_kind", sa.String(20), nullable=False),
        sa.Column("contract_id", sa.String(36), nullable=False),
        sa.Column("agreement_number", sa.String(100), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("signed_on", sa.Date()),
        sa.Column("created_by", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("withdrawn_by", sa.String(), sa.ForeignKey("users.id")),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True)),
        sa.Column("withdrawal_reason", sa.String(1000)),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.CheckConstraint("version >= 1", name="ck_contract_supplements_version"),
        sa.UniqueConstraint(
            "contract_kind",
            "contract_id",
            "agreement_number",
            name="uq_contract_supplements_number",
        ),
        sa.CheckConstraint(
            "contract_kind IN ('upstream','terminal')",
            name="ck_contract_supplements_kind",
        ),
        sa.CheckConstraint(
            "length(trim(agreement_number)) > 0 AND length(trim(title)) > 0",
            name="ck_contract_supplements_text",
        ),
        sa.CheckConstraint(
            "(withdrawn_at IS NULL AND withdrawn_by IS NULL AND withdrawal_reason IS NULL) OR (withdrawn_at IS NOT NULL AND withdrawn_by IS NOT NULL AND withdrawal_reason IS NOT NULL AND length(trim(withdrawal_reason)) > 0)",
            name="ck_contract_supplements_withdrawal",
        ),
    )
    op.create_index(
        "ix_contract_supplements_contract_id", "contract_supplements", ["contract_id"]
    )


def downgrade() -> None:
    op.drop_table("contract_supplements")
