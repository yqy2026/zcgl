"""contract group M1: create five-layer contract model tables

新增表（REQ-RNT-001 合同组作为主业务对象）：
  - contract_groups        合同组主表
  - contract_group_assets  合同组-资产 M2M
  - contracts              合同基表（替代旧 rent_contracts 的合同概念）
  - contract_assets        合同-资产 M2M
  - lease_contract_details 租赁合同明细（1:1 → contracts）
  - agency_agreement_details 代理协议明细（1:1 → contracts）
  - contract_relations     合同间关系（上下游 / 代理-直租 / 续签）

本迁移为 DDL only（仅建表），数据迁移（rent_contracts → contracts）在 M1b 中进行。
旧 rent_contracts 及其子表 FK 在 M1b 中处理。

Revision ID: 20260305_contract_group_m1
Revises: 20260305_project_field_enrichment_m1
Create Date: 2026-03-05 18:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260305_contract_group_m1"
down_revision: str | None = "20260305_project_field_enrichment_m1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── 1. contract_groups ──────────────────────────────────────────────────
    op.create_table(
        "contract_groups",
        sa.Column("contract_group_id", sa.String(), nullable=False),
        sa.Column(
            "group_code",
            sa.String(50),
            nullable=False,
            comment="合同组编码（唯一），格式：GRP-{运营方编码}-{YYYYMM}-{SEQ4}",
        ),
        sa.Column(
            "revenue_mode",
            sa.Enum("LEASE", "AGENCY", name="revenuemode"),
            nullable=False,
            comment="经营模式：LEASE(承租) / AGENCY(代理)",
        ),
        sa.Column(
            "operator_party_id",
            sa.String(),
            nullable=False,
            comment="运营方主体 ID",
        ),
        sa.Column(
            "owner_party_id",
            sa.String(),
            nullable=False,
            comment="产权方主体 ID",
        ),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column(
            "settlement_rule",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="结算规则（必填键：version/cycle/settlement_mode/amount_rule/payment_rule）",
        ),
        sa.Column(
            "revenue_attribution_rule",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "revenue_share_rule",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "risk_tags",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="风险标签列表",
        ),
        sa.Column("predecessor_group_id", sa.String(), nullable=True),
        sa.Column(
            "data_status",
            sa.String(20),
            nullable=False,
            server_default="正常",
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("created_by", sa.String(100), nullable=True),
        sa.Column("updated_by", sa.String(100), nullable=True),
        sa.ForeignKeyConstraint(
            ["operator_party_id"],
            ["parties.id"],
            name="fk_cg_operator_party",
        ),
        sa.ForeignKeyConstraint(
            ["owner_party_id"],
            ["parties.id"],
            name="fk_cg_owner_party",
        ),
        sa.ForeignKeyConstraint(
            ["predecessor_group_id"],
            ["contract_groups.contract_group_id"],
            name="fk_cg_predecessor",
        ),
        sa.PrimaryKeyConstraint("contract_group_id"),
    )
    op.create_index(
        "ix_contract_groups_group_code",
        "contract_groups",
        ["group_code"],
        unique=True,
    )
    op.create_index(
        "ix_contract_groups_operator_party_id",
        "contract_groups",
        ["operator_party_id"],
    )
    op.create_index(
        "ix_contract_groups_owner_party_id",
        "contract_groups",
        ["owner_party_id"],
    )

    # ── 2. contract_group_assets ─────────────────────────────────────────────
    op.create_table(
        "contract_group_assets",
        sa.Column("contract_group_id", sa.String(), nullable=False),
        sa.Column("asset_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["assets.id"],
            name="fk_cga_asset",
        ),
        sa.ForeignKeyConstraint(
            ["contract_group_id"],
            ["contract_groups.contract_group_id"],
            name="fk_cga_contract_group",
        ),
        sa.PrimaryKeyConstraint("contract_group_id", "asset_id"),
        comment="合同组-资产多对多关联",
    )

    # ── 3. contracts（合同基表）──────────────────────────────────────────────
    op.create_table(
        "contracts",
        sa.Column("contract_id", sa.String(), nullable=False),
        sa.Column("contract_group_id", sa.String(), nullable=False),
        sa.Column(
            "contract_direction",
            sa.Enum("LESSOR", "LESSEE", name="contractdirection"),
            nullable=False,
            comment="合同方向：LESSOR(出租) / LESSEE(承租)",
        ),
        sa.Column(
            "group_relation_type",
            sa.Enum("UPSTREAM", "DOWNSTREAM", "ENTRUSTED", "DIRECT_LEASE", name="grouprelationtype"),
            nullable=False,
            comment="合同角色：UPSTREAM(上游) / DOWNSTREAM(下游) / ENTRUSTED(委托) / DIRECT_LEASE(直租)",
        ),
        sa.Column(
            "lessor_party_id",
            sa.String(),
            nullable=False,
            comment="出租方/委托方主体",
        ),
        sa.Column(
            "lessee_party_id",
            sa.String(),
            nullable=False,
            comment="承租方/受托方主体",
        ),
        sa.Column(
            "sign_date",
            sa.Date(),
            nullable=True,
            comment="签订日期（草稿可空）",
        ),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column(
            "currency_code",
            sa.String(10),
            nullable=False,
            server_default="CNY",
        ),
        sa.Column("tax_rate", sa.DECIMAL(5, 4), nullable=True),
        sa.Column(
            "is_tax_included",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
        sa.Column(
            "status",
            sa.Enum(
                "DRAFT",
                "PENDING_REVIEW",
                "ACTIVE",
                "EXPIRED",
                "TERMINATED",
                name="contractlifecyclestatus",
            ),
            nullable=False,
            server_default="DRAFT",
        ),
        sa.Column(
            "review_status",
            sa.Enum(
                "DRAFT",
                "PENDING",
                "APPROVED",
                "REVERSED",
                name="contractreviewstatus",
            ),
            nullable=False,
            server_default="DRAFT",
        ),
        sa.Column("review_by", sa.String(100), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("review_reason", sa.Text(), nullable=True),
        sa.Column(
            "data_status",
            sa.String(20),
            nullable=False,
            server_default="正常",
        ),
        sa.Column("contract_notes", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("created_by", sa.String(100), nullable=True),
        sa.Column("updated_by", sa.String(100), nullable=True),
        sa.Column("source_session_id", sa.String(100), nullable=True),
        sa.ForeignKeyConstraint(
            ["contract_group_id"],
            ["contract_groups.contract_group_id"],
            name="fk_contract_group",
        ),
        sa.ForeignKeyConstraint(
            ["lessor_party_id"],
            ["parties.id"],
            name="fk_contract_lessor",
        ),
        sa.ForeignKeyConstraint(
            ["lessee_party_id"],
            ["parties.id"],
            name="fk_contract_lessee",
        ),
        sa.PrimaryKeyConstraint("contract_id"),
    )
    op.create_index(
        "ix_contracts_contract_group_id",
        "contracts",
        ["contract_group_id"],
    )
    op.create_index("ix_contracts_lessor_party_id", "contracts", ["lessor_party_id"])
    op.create_index("ix_contracts_lessee_party_id", "contracts", ["lessee_party_id"])

    # ── 4. contract_assets ───────────────────────────────────────────────────
    op.create_table(
        "contract_assets",
        sa.Column("contract_id", sa.String(), nullable=False),
        sa.Column("asset_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["assets.id"],
            name="fk_ca_asset",
        ),
        sa.ForeignKeyConstraint(
            ["contract_id"],
            ["contracts.contract_id"],
            name="fk_ca_contract",
        ),
        sa.PrimaryKeyConstraint("contract_id", "asset_id"),
        comment="合同-资产多对多关联",
    )

    # ── 5. lease_contract_details ────────────────────────────────────────────
    op.create_table(
        "lease_contract_details",
        sa.Column("lease_detail_id", sa.String(), nullable=False),
        sa.Column("contract_id", sa.String(), nullable=False),
        sa.Column("total_deposit", sa.DECIMAL(18, 2), nullable=True),
        sa.Column(
            "rent_amount",
            sa.DECIMAL(18, 2),
            nullable=False,
            comment="合同级租金汇总（不替代 RentTerm 分阶段明细）",
        ),
        sa.Column("monthly_rent_base", sa.DECIMAL(15, 2), nullable=True),
        sa.Column(
            "payment_cycle",
            sa.String(20),
            nullable=False,
            server_default="月付",
            comment="付款周期：月付/季付/半年付/年付",
        ),
        sa.Column("payment_terms", sa.Text(), nullable=True),
        sa.Column("tenant_name", sa.String(200), nullable=True),
        sa.Column("tenant_contact", sa.String(100), nullable=True),
        sa.Column("tenant_phone", sa.String(20), nullable=True),
        sa.Column("tenant_address", sa.String(500), nullable=True),
        sa.Column("tenant_usage", sa.String(500), nullable=True),
        sa.Column("owner_name", sa.String(200), nullable=True),
        sa.Column("owner_contact", sa.String(100), nullable=True),
        sa.Column("owner_phone", sa.String(20), nullable=True),
        sa.ForeignKeyConstraint(
            ["contract_id"],
            ["contracts.contract_id"],
            name="fk_lcd_contract",
        ),
        sa.PrimaryKeyConstraint("lease_detail_id"),
        sa.UniqueConstraint("contract_id", name="uq_lcd_contract_id"),
    )
    op.create_index(
        "ix_lease_contract_details_contract_id",
        "lease_contract_details",
        ["contract_id"],
        unique=True,
    )

    # ── 6. agency_agreement_details ──────────────────────────────────────────
    op.create_table(
        "agency_agreement_details",
        sa.Column("agency_detail_id", sa.String(), nullable=False),
        sa.Column("contract_id", sa.String(), nullable=False),
        sa.Column(
            "service_fee_ratio",
            sa.DECIMAL(5, 4),
            nullable=False,
            comment="服务费比例，如 0.0500 = 5%",
        ),
        sa.Column(
            "fee_calculation_base",
            sa.String(30),
            nullable=False,
            server_default="actual_received",
            comment="计费基数：actual_received / due_amount",
        ),
        sa.Column("agency_scope", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["contract_id"],
            ["contracts.contract_id"],
            name="fk_aad_contract",
        ),
        sa.PrimaryKeyConstraint("agency_detail_id"),
        sa.UniqueConstraint("contract_id", name="uq_aad_contract_id"),
    )
    op.create_index(
        "ix_agency_agreement_details_contract_id",
        "agency_agreement_details",
        ["contract_id"],
        unique=True,
    )

    # ── 7. contract_relations ────────────────────────────────────────────────
    op.create_table(
        "contract_relations",
        sa.Column("relation_id", sa.String(), nullable=False),
        sa.Column("parent_contract_id", sa.String(), nullable=False),
        sa.Column("child_contract_id", sa.String(), nullable=False),
        sa.Column(
            "relation_type",
            sa.Enum(
                "UPSTREAM_DOWNSTREAM",
                "AGENCY_DIRECT",
                "RENEWAL",
                name="contractrelationtype",
            ),
            nullable=False,
            comment="关系类型",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["child_contract_id"],
            ["contracts.contract_id"],
            name="fk_cr_child",
        ),
        sa.ForeignKeyConstraint(
            ["parent_contract_id"],
            ["contracts.contract_id"],
            name="fk_cr_parent",
        ),
        sa.PrimaryKeyConstraint("relation_id"),
        sa.UniqueConstraint(
            "parent_contract_id",
            "child_contract_id",
            name="uq_contract_relation_pair",
        ),
    )
    op.create_index(
        "ix_contract_relations_parent_contract_id",
        "contract_relations",
        ["parent_contract_id"],
    )
    op.create_index(
        "ix_contract_relations_child_contract_id",
        "contract_relations",
        ["child_contract_id"],
    )


def downgrade() -> None:
    # 删除顺序与 upgrade 相反，先删依赖表
    op.drop_table("contract_relations")
    op.drop_table("agency_agreement_details")
    op.drop_table("lease_contract_details")
    op.drop_table("contract_assets")
    op.drop_table("contracts")
    op.drop_table("contract_group_assets")
    op.drop_table("contract_groups")

    # 删除 Enum 类型
    op.execute("DROP TYPE IF EXISTS contractrelationtype")
    op.execute("DROP TYPE IF EXISTS contractreviewstatus")
    op.execute("DROP TYPE IF EXISTS contractlifecyclestatus")
    op.execute("DROP TYPE IF EXISTS grouprelationtype")
    op.execute("DROP TYPE IF EXISTS contractdirection")
    op.execute("DROP TYPE IF EXISTS revenuemode")
