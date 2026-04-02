"""REQ-APR-001: add approval domain tables.

Revision ID: 20260402_req_apr_001_approval_domain
Revises: 20260329_req_rnt_004_005_audit_context
Create Date: 2026-04-02 11:40:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260402_req_apr_001_approval_domain"
down_revision: str | None = "20260329_req_rnt_004_005_audit_context"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "approval_instances",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("approval_no", sa.String(length=64), nullable=False),
        sa.Column("business_type", sa.String(length=50), nullable=False),
        sa.Column("business_id", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("starter_id", sa.String(), nullable=False),
        sa.Column("assignee_user_id", sa.String(), nullable=False),
        sa.Column("current_task_id", sa.String(), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["assignee_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["starter_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("approval_no"),
    )
    op.create_index(
        "ix_approval_instances_business_id",
        "approval_instances",
        ["business_id"],
        unique=False,
    )
    op.create_index(
        "ix_approval_instances_business_status",
        "approval_instances",
        ["business_type", "business_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_approval_instances_business_type",
        "approval_instances",
        ["business_type"],
        unique=False,
    )
    op.create_index(
        "ix_approval_instances_status",
        "approval_instances",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_approval_instances_starter_id",
        "approval_instances",
        ["starter_id"],
        unique=False,
    )
    op.create_index(
        "ix_approval_instances_assignee_user_id",
        "approval_instances",
        ["assignee_user_id"],
        unique=False,
    )

    op.create_table(
        "approval_task_snapshots",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("approval_instance_id", sa.String(), nullable=False),
        sa.Column("business_type", sa.String(length=50), nullable=False),
        sa.Column("business_id", sa.String(length=50), nullable=False),
        sa.Column("task_name", sa.String(length=100), nullable=False),
        sa.Column("assignee_user_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["approval_instance_id"], ["approval_instances.id"]),
        sa.ForeignKeyConstraint(["assignee_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_approval_task_snapshots_approval_instance_id",
        "approval_task_snapshots",
        ["approval_instance_id"],
        unique=False,
    )
    op.create_index(
        "ix_approval_task_snapshots_assignee_user_id",
        "approval_task_snapshots",
        ["assignee_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_approval_task_snapshots_business_id",
        "approval_task_snapshots",
        ["business_id"],
        unique=False,
    )
    op.create_index(
        "ix_approval_task_snapshots_business_type",
        "approval_task_snapshots",
        ["business_type"],
        unique=False,
    )
    op.create_index(
        "ix_approval_task_snapshots_status",
        "approval_task_snapshots",
        ["status"],
        unique=False,
    )

    op.create_table(
        "approval_action_logs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("approval_instance_id", sa.String(), nullable=False),
        sa.Column("approval_task_snapshot_id", sa.String(), nullable=True),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.Column("operator_id", sa.String(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("context", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["approval_instance_id"], ["approval_instances.id"]),
        sa.ForeignKeyConstraint(
            ["approval_task_snapshot_id"],
            ["approval_task_snapshots.id"],
        ),
        sa.ForeignKeyConstraint(["operator_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_approval_action_logs_action",
        "approval_action_logs",
        ["action"],
        unique=False,
    )
    op.create_index(
        "ix_approval_action_logs_approval_instance_id",
        "approval_action_logs",
        ["approval_instance_id"],
        unique=False,
    )
    op.create_index(
        "ix_approval_action_logs_approval_task_snapshot_id",
        "approval_action_logs",
        ["approval_task_snapshot_id"],
        unique=False,
    )
    op.create_index(
        "ix_approval_action_logs_operator_id",
        "approval_action_logs",
        ["operator_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_approval_action_logs_operator_id", table_name="approval_action_logs")
    op.drop_index(
        "ix_approval_action_logs_approval_task_snapshot_id",
        table_name="approval_action_logs",
    )
    op.drop_index(
        "ix_approval_action_logs_approval_instance_id",
        table_name="approval_action_logs",
    )
    op.drop_index("ix_approval_action_logs_action", table_name="approval_action_logs")
    op.drop_table("approval_action_logs")

    op.drop_index(
        "ix_approval_task_snapshots_status",
        table_name="approval_task_snapshots",
    )
    op.drop_index(
        "ix_approval_task_snapshots_business_type",
        table_name="approval_task_snapshots",
    )
    op.drop_index(
        "ix_approval_task_snapshots_business_id",
        table_name="approval_task_snapshots",
    )
    op.drop_index(
        "ix_approval_task_snapshots_assignee_user_id",
        table_name="approval_task_snapshots",
    )
    op.drop_index(
        "ix_approval_task_snapshots_approval_instance_id",
        table_name="approval_task_snapshots",
    )
    op.drop_table("approval_task_snapshots")

    op.drop_index(
        "ix_approval_instances_assignee_user_id",
        table_name="approval_instances",
    )
    op.drop_index("ix_approval_instances_starter_id", table_name="approval_instances")
    op.drop_index("ix_approval_instances_status", table_name="approval_instances")
    op.drop_index(
        "ix_approval_instances_business_type",
        table_name="approval_instances",
    )
    op.drop_index(
        "ix_approval_instances_business_status",
        table_name="approval_instances",
    )
    op.drop_index(
        "ix_approval_instances_business_id",
        table_name="approval_instances",
    )
    op.drop_table("approval_instances")
