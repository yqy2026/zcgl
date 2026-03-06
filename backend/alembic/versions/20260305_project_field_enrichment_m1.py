"""project field enrichment for M1: rename name/code/project_status, add review fields, drop legacy columns

Revision ID: 20260305_project_field_enrichment_m1
Revises: 20260305_asset_field_enrichment_m1
Create Date: 2026-03-05 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260305_project_field_enrichment_m1"
down_revision: str | None = "20260305_asset_field_enrichment_m1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. 改名 name → project_name
    op.alter_column("projects", "name", new_column_name="project_name")

    # 2. 改名 code → project_code（同时更新 UNIQUE 约束名）
    op.alter_column("projects", "code", new_column_name="project_code")
    op.drop_constraint("projects_code_key", "projects", type_="unique")
    op.create_unique_constraint("projects_project_code_key", "projects", ["project_code"])

    # 3. 改名 project_status → status，迁移中文值为英文枚举
    op.alter_column("projects", "project_status", new_column_name="status")
    op.execute("""
        UPDATE projects SET status = CASE status
            WHEN '规划中' THEN 'planning'
            WHEN '进行中' THEN 'active'
            WHEN '暂停'   THEN 'paused'
            WHEN '已完成' THEN 'completed'
            WHEN '已终止' THEN 'terminated'
            WHEN 'doing'  THEN 'active'
            WHEN 'planning' THEN 'planning'
            WHEN 'active' THEN 'active'
            WHEN 'paused' THEN 'paused'
            WHEN 'completed' THEN 'completed'
            WHEN 'terminated' THEN 'terminated'
            ELSE 'planning'
        END
    """)
    # 收紧列长度至 20
    op.alter_column(
        "projects", "status",
        type_=sa.String(20),
        nullable=False,
        server_default="planning",
        existing_nullable=False,
    )

    # 4. 新增审核字段
    op.add_column("projects", sa.Column("review_status", sa.String(20), nullable=True))
    op.add_column("projects", sa.Column("review_by", sa.String(100), nullable=True))
    op.add_column("projects", sa.Column("reviewed_at", sa.DateTime(), nullable=True))
    op.add_column("projects", sa.Column("review_reason", sa.Text(), nullable=True))

    # 5. 回填 review_status（全部存量数据设为 draft）
    op.execute("UPDATE projects SET review_status = 'draft' WHERE review_status IS NULL")
    op.alter_column("projects", "review_status", nullable=False, server_default="draft")

    # 6. 更新索引名（旧索引引用 project_status/is_active）
    op.drop_index("ix_projects_is_active_true", table_name="projects", if_exists=True)
    op.drop_index("ix_projects_status_created_at", table_name="projects", if_exists=True)
    op.create_index(
        "ix_projects_status_created_at",
        "projects",
        ["status", sa.text("created_at DESC")],
    )

    # 7. DROP 25 个废弃列
    _drop_cols = [
        "short_name", "project_type", "project_scale",
        "start_date", "end_date", "expected_completion_date", "actual_completion_date",
        "address", "city", "district", "province",
        "project_manager", "project_phone", "project_email",
        "total_investment", "planned_investment", "actual_investment", "project_budget",
        "project_description", "project_objectives", "project_scope",
        "construction_company", "design_company", "supervision_company",
        "is_active",
    ]
    for col in _drop_cols:
        op.drop_column("projects", col)


def downgrade() -> None:
    # 恢复废弃列（可写空值，不恢复历史数据）
    op.add_column("projects", sa.Column("short_name", sa.String(100), nullable=True))
    op.add_column("projects", sa.Column("project_type", sa.String(50), nullable=True))
    op.add_column("projects", sa.Column("project_scale", sa.String(50), nullable=True))
    op.add_column("projects", sa.Column("start_date", sa.Date(), nullable=True))
    op.add_column("projects", sa.Column("end_date", sa.Date(), nullable=True))
    op.add_column("projects", sa.Column("expected_completion_date", sa.Date(), nullable=True))
    op.add_column("projects", sa.Column("actual_completion_date", sa.Date(), nullable=True))
    op.add_column("projects", sa.Column("address", sa.String(500), nullable=True))
    op.add_column("projects", sa.Column("city", sa.String(100), nullable=True))
    op.add_column("projects", sa.Column("district", sa.String(100), nullable=True))
    op.add_column("projects", sa.Column("province", sa.String(100), nullable=True))
    op.add_column("projects", sa.Column("project_manager", sa.String(100), nullable=True))
    op.add_column("projects", sa.Column("project_phone", sa.String(50), nullable=True))
    op.add_column("projects", sa.Column("project_email", sa.String(100), nullable=True))
    op.add_column("projects", sa.Column("total_investment", sa.DECIMAL(15, 2), nullable=True))
    op.add_column("projects", sa.Column("planned_investment", sa.DECIMAL(15, 2), nullable=True))
    op.add_column("projects", sa.Column("actual_investment", sa.DECIMAL(15, 2), nullable=True))
    op.add_column("projects", sa.Column("project_budget", sa.DECIMAL(15, 2), nullable=True))
    op.add_column("projects", sa.Column("project_description", sa.Text(), nullable=True))
    op.add_column("projects", sa.Column("project_objectives", sa.Text(), nullable=True))
    op.add_column("projects", sa.Column("project_scope", sa.Text(), nullable=True))
    op.add_column("projects", sa.Column("construction_company", sa.String(200), nullable=True))
    op.add_column("projects", sa.Column("design_company", sa.String(200), nullable=True))
    op.add_column("projects", sa.Column("supervision_company", sa.String(200), nullable=True))
    op.add_column("projects", sa.Column("is_active", sa.Boolean(), nullable=True))

    # 恢复审核字段前 DROP
    op.drop_column("projects", "review_status")
    op.drop_column("projects", "review_by")
    op.drop_column("projects", "reviewed_at")
    op.drop_column("projects", "review_reason")

    # 恢复索引
    op.drop_index("ix_projects_status_created_at", table_name="projects", if_exists=True)
    op.create_index("ix_projects_is_active_true", "projects", ["is_active"])

    # 恢复列名
    op.alter_column("projects", "status", new_column_name="project_status")
    op.drop_constraint("projects_project_code_key", "projects", type_="unique")
    op.alter_column("projects", "project_code", new_column_name="code")
    op.create_unique_constraint("projects_code_key", "projects", ["code"])
    op.alter_column("projects", "project_name", new_column_name="name")
