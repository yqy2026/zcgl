"""
合同组及合同体系数据模型（五层合同架构 v1.0）

层级：
  ContractGroup（交易包）
    └── Contract 基表（N 条）
          ├── LeaseContractDetail（租赁明细，1:1）
          └── AgencyAgreementDetail（代理明细，1:1）
  ContractRelation（合同间关系）

对应需求：REQ-RNT-001（合同组作为主业务对象）
字段附录：docs/features/requirements-appendix-fields.md §3.3–§3.7
"""

import enum
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .asset import Asset
    from .party import Party

from sqlalchemy import (
    DECIMAL,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .associations import contract_assets, contract_group_assets

# ===================== Enums =====================


class RevenueMode(str, enum.Enum):
    """经营模式"""

    LEASE = "lease"    # 承租模式
    AGENCY = "agency"  # 代理模式


class ContractDirection(str, enum.Enum):
    """合同方向（从哪个视角看这份合同）"""

    LESSOR = "出租"
    LESSEE = "承租"


class GroupRelationType(str, enum.Enum):
    """合同在合同组内的角色

    承租模式: 上游（内部入约）/ 下游（对外出约）
    代理模式: 委托（内部入约）/ 直租（对外出约，产权方-终端租户直签）
    """

    UPSTREAM = "上游"
    DOWNSTREAM = "下游"
    ENTRUSTED = "委托"
    DIRECT_LEASE = "直租"


class ContractLifecycleStatus(str, enum.Enum):
    """合同生命周期状态"""

    DRAFT = "草稿"
    PENDING_REVIEW = "待审"
    ACTIVE = "生效"
    EXPIRED = "已到期"
    TERMINATED = "已终止"


class ContractReviewStatus(str, enum.Enum):
    """合同审核状态"""

    DRAFT = "草稿"
    PENDING = "待审"
    APPROVED = "已审"
    REVERSED = "反审核"


class ContractRelationType(str, enum.Enum):
    """合同间关系类型"""

    UPSTREAM_DOWNSTREAM = "upstream_downstream"  # 上下游（承租模式）
    AGENCY_DIRECT = "agency_direct"               # 代理-直租（代理模式）
    RENEWAL = "renewal"                           # 续签


# ===================== Models =====================


class ContractGroup(Base):
    """合同组（交易包）—— 以一笔经营关系为单位的业务容器。

    定位：纯容器，不拥有独立生命周期状态。
    状态（derived_status）由 Service 层从组内合同状态实时计算，不写库。
    """

    __tablename__ = "contract_groups"

    contract_group_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    group_code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="合同组编码（唯一），格式：GRP-{运营方编码}-{YYYYMM}-{SEQ4}",
    )
    revenue_mode: Mapped[RevenueMode] = mapped_column(
        Enum(RevenueMode, values_callable=lambda e: [m.name for m in e]),
        nullable=False,
        comment="经营模式：lease(承租) / agency(代理)；DB 存储成员 name（LEASE/AGENCY）",
    )
    operator_party_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("parties.id"),
        nullable=False,
        index=True,
        comment="运营方主体 ID",
    )
    owner_party_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("parties.id"),
        nullable=False,
        index=True,
        comment="产权方主体 ID",
    )
    effective_from: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="合同组生效开始日",
    )
    effective_to: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="合同组生效结束日（手动设定初始值 or 由组内合同 MAX 派生）",
    )
    settlement_rule: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        comment=(
            "结算规则（必填键：version/cycle/settlement_mode/amount_rule/payment_rule）"
        ),
    )
    revenue_attribution_rule: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="收入归集口径配置",
    )
    revenue_share_rule: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="分润规则配置（MVP 仅留存，不做自动分润计算）",
    )
    risk_tags: Mapped[list[str] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="风险标签列表",
    )
    predecessor_group_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("contract_groups.contract_group_id"),
        nullable=True,
        comment="续签时指向前一周期的合同组",
    )
    data_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="正常",
        comment="数据状态：正常 / 已删除（仅逻辑删除）",
    )
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="乐观锁版本号（由 ORM 自动维护）",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        onupdate=lambda: datetime.now(UTC).replace(tzinfo=None),
    )
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # --- Relationships ---
    operator_party: Mapped["Party"] = relationship(
        "Party",
        foreign_keys=[operator_party_id],
    )
    owner_party: Mapped["Party"] = relationship(
        "Party",
        foreign_keys=[owner_party_id],
    )
    contracts: Mapped[list["Contract"]] = relationship(
        "Contract",
        back_populates="contract_group",
        cascade="all, delete-orphan",
    )
    assets: Mapped[list["Asset"]] = relationship(
        "Asset",
        secondary=contract_group_assets,
    )
    predecessor_group: Mapped["ContractGroup | None"] = relationship(
        "ContractGroup",
        remote_side=[contract_group_id],
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ContractGroup(group_code={self.group_code}, mode={self.revenue_mode})>"


class Contract(Base):
    """合同基表 —— 所有合同类型的公共字段。

    类型差异字段下沉到明细表：
    - LeaseContractDetail（租赁类：上游承租 / 下游出租 / 直租）
    - AgencyAgreementDetail（代理类：委托协议）

    台账（RentLedger / ServiceFeeLedger）的 FK 在 M1b 迁移中从
    rent_contracts.id 切换为 contracts.contract_id。
    """

    __tablename__ = "contracts"

    contract_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    contract_group_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("contract_groups.contract_group_id"),
        nullable=False,
        index=True,
        comment="所属合同组",
    )
    contract_direction: Mapped[ContractDirection] = mapped_column(
        Enum(ContractDirection, values_callable=lambda e: [m.name for m in e]),
        nullable=False,
        comment="合同方向；DB 存储成员 name（LESSOR/LESSEE）",
    )
    group_relation_type: Mapped[GroupRelationType] = mapped_column(
        Enum(GroupRelationType, values_callable=lambda e: [m.name for m in e]),
        nullable=False,
        comment="合同角色；DB 存储成员 name（UPSTREAM/DOWNSTREAM/ENTRUSTED/DIRECT_LEASE）",
    )
    lessor_party_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("parties.id"),
        nullable=False,
        index=True,
        comment="出租方/委托方主体（代理模式下 lessor = 委托方）",
    )
    lessee_party_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("parties.id"),
        nullable=False,
        index=True,
        comment="承租方/受托方主体（代理模式下 lessee = 受托方）",
    )
    sign_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="签订日期（草稿可空，进入待审/生效前必填）",
    )
    effective_from: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="合同生效开始日",
    )
    effective_to: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="合同生效结束日",
    )
    currency_code: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="CNY",
        comment="币种，MVP 固定 CNY",
    )
    tax_rate: Mapped[Decimal | None] = mapped_column(
        DECIMAL(5, 4),
        nullable=True,
        comment="税率，范围 [0, 1]",
    )
    is_tax_included: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="是否含税，默认 true",
    )
    status: Mapped[ContractLifecycleStatus] = mapped_column(
        Enum(ContractLifecycleStatus, values_callable=lambda e: [m.name for m in e]),
        nullable=False,
        default=ContractLifecycleStatus.DRAFT,
        comment="合同生命周期状态；DB 存储成员 name（DRAFT/PENDING_REVIEW/ACTIVE/EXPIRED/TERMINATED）",
    )
    review_status: Mapped[ContractReviewStatus] = mapped_column(
        Enum(ContractReviewStatus, values_callable=lambda e: [m.name for m in e]),
        nullable=False,
        default=ContractReviewStatus.DRAFT,
        comment="审核状态；DB 存储成员 name（DRAFT/PENDING/APPROVED/REVERSED）",
    )
    review_by: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="审核人（通过/反审核时必填）",
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        comment="审核时间（通过/反审核时必填）",
    )
    review_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="审核原因（反审核时必填）",
    )
    data_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="正常",
        comment="数据状态：正常 / 已删除（仅逻辑删除）",
    )
    contract_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="合同备注",
    )
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="乐观锁版本号",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        onupdate=lambda: datetime.now(UTC).replace(tzinfo=None),
    )
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_session_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="PDF 导入会话 ID",
    )

    # --- Relationships ---
    contract_group: Mapped["ContractGroup"] = relationship(
        "ContractGroup",
        back_populates="contracts",
    )
    lessor_party: Mapped["Party"] = relationship(
        "Party",
        foreign_keys=[lessor_party_id],
    )
    lessee_party: Mapped["Party"] = relationship(
        "Party",
        foreign_keys=[lessee_party_id],
    )
    assets: Mapped[list["Asset"]] = relationship(
        "Asset",
        secondary=contract_assets,
    )
    lease_detail: Mapped["LeaseContractDetail | None"] = relationship(
        "LeaseContractDetail",
        back_populates="contract",
        uselist=False,
        cascade="all, delete-orphan",
    )
    agency_detail: Mapped["AgencyAgreementDetail | None"] = relationship(
        "AgencyAgreementDetail",
        back_populates="contract",
        uselist=False,
        cascade="all, delete-orphan",
    )
    # 本合同作为 child 时的父合同关系
    parent_relations: Mapped[list["ContractRelation"]] = relationship(
        "ContractRelation",
        foreign_keys="[ContractRelation.child_contract_id]",
        back_populates="child_contract",
        cascade="all, delete-orphan",
    )
    # 本合同作为 parent 时的子合同关系
    child_relations: Mapped[list["ContractRelation"]] = relationship(
        "ContractRelation",
        foreign_keys="[ContractRelation.parent_contract_id]",
        back_populates="parent_contract",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<Contract(contract_id={self.contract_id}, "
            f"type={self.group_relation_type}, status={self.status})>"
        )


class LeaseContractDetail(Base):
    """租赁合同明细 —— 租赁类合同（上游承租/下游出租/直租）的专有字段。

    一份 Contract 最多关联一条 LeaseContractDetail（UNIQUE contract_id）。
    派生字段 rent_amount_excl_tax 由 Service 层按 is_tax_included/tax_rate 计算，不写库。
    """

    __tablename__ = "lease_contract_details"

    lease_detail_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    contract_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("contracts.contract_id"),
        nullable=False,
        unique=True,
        index=True,
        comment="FK → Contract 基表（1:1）",
    )
    total_deposit: Mapped[Decimal | None] = mapped_column(
        DECIMAL(18, 2),
        nullable=True,
        default=Decimal("0"),
        comment="总押金金额 ≥ 0",
    )
    rent_amount: Mapped[Decimal] = mapped_column(
        DECIMAL(18, 2),
        nullable=False,
        comment="合同级租金汇总金额（不替代 RentTerm 分阶段明细）",
    )
    monthly_rent_base: Mapped[Decimal | None] = mapped_column(
        DECIMAL(15, 2),
        nullable=True,
        comment="基础月租金",
    )
    payment_cycle: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="月付",
        comment="付款周期：月付 / 季付 / 半年付 / 年付",
    )
    payment_terms: Mapped[str | None] = mapped_column(Text, nullable=True)
    tenant_name: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="承租方名称（冗余展示，主数据以 lessee_party_id 为准）",
    )
    tenant_contact: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tenant_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    tenant_address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    tenant_usage: Mapped[str | None] = mapped_column(String(500), nullable=True)
    owner_name: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="甲方/出租方名称（冗余展示，主数据以 lessor_party_id 为准）",
    )
    owner_contact: Mapped[str | None] = mapped_column(String(100), nullable=True)
    owner_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # --- Relationships ---
    contract: Mapped["Contract"] = relationship(
        "Contract",
        back_populates="lease_detail",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<LeaseContractDetail(contract_id={self.contract_id}, "
            f"rent_amount={self.rent_amount})>"
        )


class AgencyAgreementDetail(Base):
    """代理协议明细 —— 代理模式委托协议的专有字段。

    一份 Contract 最多关联一条 AgencyAgreementDetail（UNIQUE contract_id）。
    代理协议中：lessor_party_id = 委托方（产权方），lessee_party_id = 受托方（运营方）。
    """

    __tablename__ = "agency_agreement_details"

    agency_detail_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    contract_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("contracts.contract_id"),
        nullable=False,
        unique=True,
        index=True,
        comment="FK → Contract 基表（1:1）",
    )
    service_fee_ratio: Mapped[Decimal] = mapped_column(
        DECIMAL(5, 4),
        nullable=False,
        comment="服务费比例，如 0.0500 = 5%",
    )
    fee_calculation_base: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="actual_received",
        comment="计费基数：actual_received(实收租金) / due_amount(应收租金)",
    )
    agency_scope: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="代理范围描述（自由文本）",
    )

    # --- Relationships ---
    contract: Mapped["Contract"] = relationship(
        "Contract",
        back_populates="agency_detail",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<AgencyAgreementDetail(contract_id={self.contract_id}, "
            f"ratio={self.service_fee_ratio})>"
        )


class ContractRelation(Base):
    """合同间关系 —— 记录合同的上下游、代理-直租、续签关系。

    采用 parent/child 模型，不做反向冗余存储。
    ContractGroup 的 upstream_contract_ids / downstream_contract_ids 由本表派生。
    约束：(parent_contract_id, child_contract_id) 联合唯一。
    """

    __tablename__ = "contract_relations"
    __table_args__ = (
        UniqueConstraint(
            "parent_contract_id",
            "child_contract_id",
            name="uq_contract_relation_pair",
        ),
    )

    relation_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    parent_contract_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("contracts.contract_id"),
        nullable=False,
        index=True,
        comment="上级合同（上游 / 委托协议 / 旧合同）",
    )
    child_contract_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("contracts.contract_id"),
        nullable=False,
        index=True,
        comment="下级合同（下游 / 终端合同 / 新合同）",
    )
    relation_type: Mapped[ContractRelationType] = mapped_column(
        Enum(ContractRelationType, values_callable=lambda e: [m.name for m in e]),
        nullable=False,
        comment="关系类型；DB 存储成员 name（UPSTREAM_DOWNSTREAM/AGENCY_DIRECT/RENEWAL）",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
    )

    # --- Relationships ---
    parent_contract: Mapped["Contract"] = relationship(
        "Contract",
        foreign_keys=[parent_contract_id],
        back_populates="child_relations",
    )
    child_contract: Mapped["Contract"] = relationship(
        "Contract",
        foreign_keys=[child_contract_id],
        back_populates="parent_relations",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<ContractRelation(type={self.relation_type}, "
            f"parent={self.parent_contract_id}, child={self.child_contract_id})>"
        )
