"""add phone and make email nullable

Revision ID: 20260208_phone_email
Revises: 20260208_simplify_organization_schema
Create Date: 2026-02-08

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260208_phone_email"
down_revision: str | None = "20260208_simplify_organization_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. 先添加 phone 为可空
    op.add_column(
        "users",
        sa.Column("phone", sa.String(20), nullable=True, comment="手机号码"),
    )

    # 2. 为现有用户生成唯一占位手机号（11位），避免唯一索引创建失败
    op.execute(
        """
        WITH numbered_users AS (
            SELECT id, ROW_NUMBER() OVER (ORDER BY id) AS rn
            FROM users
        )
        UPDATE users AS u
        SET phone = LPAD(numbered_users.rn::text, 11, '0')
        FROM numbered_users
        WHERE u.id = numbered_users.id
        """
    )

    # 3. 改为非空
    op.alter_column("users", "phone", nullable=False)

    # 4. 添加唯一索引
    op.create_index("ix_users_phone", "users", ["phone"], unique=True)

    # 5. 修改 email 为可空
    op.alter_column(
        "users",
        "email",
        existing_type=sa.String(100),
        nullable=True,
    )


def downgrade() -> None:
    # 恢复 email 为非空（需先处理空值）
    op.execute("UPDATE users SET email = username || '@placeholder.local' WHERE email IS NULL")
    op.alter_column(
        "users",
        "email",
        existing_type=sa.String(100),
        nullable=False,
    )

    # 删除 phone 索引和字段
    op.drop_index("ix_users_phone", table_name="users")
    op.drop_column("users", "phone")
