"""drop generic contacts in favor of party contacts

Revision ID: 20260603_drop_generic_contacts
Revises: 20260513_project_contract_relation_phase1a
Create Date: 2026-06-03 11:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260603_drop_generic_contacts"
down_revision: str | None = "20260513_project_contract_relation_phase1a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _table_exists(
    inspector: sa.engine.reflection.Inspector,
    table_name: str,
) -> bool:
    return inspector.has_table(table_name)


def _drop_generic_contact_permissions(inspector: sa.engine.reflection.Inspector) -> None:
    bind = op.get_bind()

    if _table_exists(inspector, "abac_policy_rules"):
        bind.execute(
            sa.text(
                """
                DELETE FROM abac_policy_rules
                WHERE resource_type = 'contact'
                """
            )
        )

    if not _table_exists(inspector, "permissions"):
        return

    if _table_exists(inspector, "role_permissions"):
        bind.execute(
            sa.text(
                """
                DELETE FROM role_permissions
                WHERE permission_id IN (
                    SELECT id FROM permissions WHERE resource = 'contact'
                )
                """
            )
        )

    if _table_exists(inspector, "permission_grants"):
        bind.execute(
            sa.text(
                """
                DELETE FROM permission_grants
                WHERE permission_id IN (
                    SELECT id FROM permissions WHERE resource = 'contact'
                )
                """
            )
        )

    bind.execute(sa.text("DELETE FROM permissions WHERE resource = 'contact'"))


def upgrade() -> None:
    """Remove the generic Contact path after PartyContact became the SSOT."""
    inspector = sa.inspect(op.get_bind())
    _drop_generic_contact_permissions(inspector)

    if _table_exists(inspector, "contacts"):
        op.drop_table("contacts")


def downgrade() -> None:
    """Recreate only the retired generic contacts table shape."""
    inspector = sa.inspect(op.get_bind())
    if _table_exists(inspector, "contacts"):
        return

    op.create_table(
        "contacts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False, comment="关联实体类型"),
        sa.Column("entity_id", sa.String(), nullable=False, comment="关联实体ID"),
        sa.Column("name", sa.String(100), nullable=False, comment="联系人姓名"),
        sa.Column("title", sa.String(100), nullable=True, comment="职位/头衔"),
        sa.Column("department", sa.String(100), nullable=True, comment="部门"),
        sa.Column("phone", sa.String(20), nullable=True, comment="手机号码"),
        sa.Column("office_phone", sa.String(20), nullable=True, comment="办公电话"),
        sa.Column("email", sa.String(200), nullable=True, comment="电子邮箱"),
        sa.Column("wechat", sa.String(100), nullable=True, comment="微信号"),
        sa.Column("address", sa.String(500), nullable=True, comment="地址"),
        sa.Column(
            "contact_type",
            sa.String(20),
            nullable=False,
            server_default="general",
            comment="联系人类型",
        ),
        sa.Column(
            "is_primary",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
            comment="是否主要联系人",
        ),
        sa.Column("notes", sa.Text(), nullable=True, comment="备注"),
        sa.Column(
            "preferred_contact_time",
            sa.String(100),
            nullable=True,
            comment="偏好联系时间",
        ),
        sa.Column(
            "preferred_contact_method",
            sa.String(50),
            nullable=True,
            comment="偏好联系方式",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
            comment="是否启用",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=True, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=True, comment="更新时间"),
        sa.Column("created_by", sa.String(100), nullable=True, comment="创建人"),
        sa.Column("updated_by", sa.String(100), nullable=True, comment="更新人"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_contacts_entity_type", "contacts", ["entity_type"])
    op.create_index("ix_contacts_entity_id", "contacts", ["entity_id"])
