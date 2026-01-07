"""
租金台账相关数据库模型
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    DECIMAL,
    JSON,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import relationship

from ..database import Base


# ===================== Enums =====================
class ContractType(str, enum.Enum):
    """合同类型枚举"""

    LEASE_UPSTREAM = "lease_upstream"  # 上游租赁合同（运营方承租）
    LEASE_DOWNSTREAM = "lease_downstream"  # 下游租赁合同（转租给终端租户）
    ENTRUSTED = "entrusted"  # 委托运营合同


class DepositTransactionType(str, enum.Enum):
    """押金交易类型枚举"""

    RECEIPT = "receipt"  # 收取押金
    REFUND = "refund"  # 退还押金
    DEDUCTION = "deduction"  # 抵扣（如欠租抵扣）
    TRANSFER_OUT = "transfer_out"  # 转出（续签时转到新合同）
    TRANSFER_IN = "transfer_in"  # 转入（从旧合同续签转入）


class PaymentCycle(str, enum.Enum):
    """付款周期枚举"""

    MONTHLY = "monthly"  # 月付
    QUARTERLY = "quarterly"  # 季付
    SEMI_ANNUAL = "semi_annual"  # 半年付
    ANNUAL = "annual"  # 年付


# ===================== Association Tables =====================
# 合同-资产 多对多关联表
rent_contract_assets = Table(
    "rent_contract_assets",
    Base.metadata,
    Column("contract_id", String, ForeignKey("rent_contracts.id"), primary_key=True),
    Column("asset_id", String, ForeignKey("assets.id"), primary_key=True),
    Column("created_at", DateTime, default=datetime.utcnow, comment="关联创建时间"),
)


class RentContract(Base):
    """租金合同模型 - V2"""

    __tablename__ = "rent_contracts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # 基本信息
    contract_number = Column(
        String(100), unique=True, nullable=False, comment="合同编号"
    )
    # V2: 移除 asset_id，改用多对多关联
    ownership_id = Column(
        String, ForeignKey("ownerships.id"), nullable=False, comment="权属方ID"
    )

    # V2: 合同类型
    contract_type = Column(
        Enum(ContractType),
        nullable=False,
        default=ContractType.LEASE_DOWNSTREAM,
        comment="合同类型：上游租赁/下游租赁/委托运营",
    )

    # V2: 上游合同关联（可选，用于将下游合同关联到上游）
    upstream_contract_id = Column(
        String,
        ForeignKey("rent_contracts.id"),
        nullable=True,
        comment="上游合同ID（下游合同可选填）",
    )

    # V2: 委托运营服务费率（仅委托运营合同使用）
    service_fee_rate = Column(
        DECIMAL(5, 4),
        nullable=True,
        comment="服务费率（如 0.0500 表示 5%），仅委托运营合同适用",
    )

    # 承租方信息
    tenant_name = Column(String(200), nullable=False, comment="承租方名称")
    tenant_contact = Column(String(100), comment="承租方联系人")
    tenant_phone = Column(String(20), comment="承租方联系电话")
    tenant_address = Column(String(500), comment="承租方地址")
    # V2: 下游合同额外字段
    tenant_usage = Column(String(500), nullable=True, comment="用途说明（下游合同）")

    # 合同日期信息
    sign_date = Column(Date, nullable=False, comment="签订日期")
    start_date = Column(Date, nullable=False, comment="租期开始日期")
    end_date = Column(Date, nullable=False, comment="租期结束日期")

    # 金额信息
    total_deposit = Column(DECIMAL(15, 2), default=0, comment="总押金金额")
    monthly_rent_base = Column(DECIMAL(15, 2), comment="基础月租金")
    # V2: 付款周期
    payment_cycle = Column(
        Enum(PaymentCycle),
        nullable=True,
        default=PaymentCycle.MONTHLY,
        comment="付款周期：月付/季付/半年付/年付",
    )

    # 合同状态
    contract_status = Column(
        String(20), default="有效", comment="合同状态：有效/到期/终止"
    )

    # 其他信息
    payment_terms = Column(Text, comment="支付条款")
    contract_notes = Column(Text, comment="合同备注")

    # 系统字段
    data_status = Column(String(20), default="正常", comment="数据状态")
    version = Column(Integer, default=1, comment="版本号")

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间"
    )

    # 多租户支持
    tenant_id = Column(String(50), nullable=True, comment="租户ID")

    # PDF导入追踪
    source_session_id = Column(String(100), nullable=True, comment="PDF导入会话ID")

    # 关联关系 - V2: 改为多对多
    assets = relationship(
        "Asset", secondary=rent_contract_assets, back_populates="rent_contracts"
    )
    ownership = relationship("Ownership", back_populates="owned_rent_contracts")
    rent_terms = relationship(
        "RentTerm", back_populates="contract", cascade="all, delete-orphan"
    )
    rent_ledger = relationship(
        "RentLedger", back_populates="contract", cascade="all, delete-orphan"
    )
    # V2: 押金账本
    deposit_ledger = relationship(
        "RentDepositLedger",
        back_populates="contract",
        cascade="all, delete-orphan",
        foreign_keys="[RentDepositLedger.contract_id]",
    )
    # V2: 上游合同关联（自关联）
    upstream_contract = relationship(
        "RentContract", remote_side=[id], backref="downstream_contracts"
    )
    # V2: 合同附件
    attachments = relationship(
        "RentContractAttachment",
        back_populates="contract",
        cascade="all, delete-orphan",
    )
    # V2: 服务费台账（委托运营）
    service_fee_ledger = relationship(
        "ServiceFeeLedger", back_populates="contract", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<RentContract(contract_number={self.contract_number}, tenant_name={self.tenant_name})>"  # pragma: no cover


class RentDepositLedger(Base):
    """押金台账模型 - V2 新增"""

    __tablename__ = "rent_deposit_ledger"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # 关联信息
    contract_id = Column(
        String, ForeignKey("rent_contracts.id"), nullable=False, comment="关联合同ID"
    )

    # 交易类型
    transaction_type = Column(
        Enum(DepositTransactionType),
        nullable=False,
        comment="交易类型：收取/退还/抵扣/转出/转入",
    )

    # 金额（正数表示增加，负数表示减少）
    amount = Column(DECIMAL(15, 2), nullable=False, comment="金额")

    # 交易日期
    transaction_date = Column(Date, nullable=False, comment="交易日期")

    # 关联其他合同（用于续签转移）
    related_contract_id = Column(
        String,
        ForeignKey("rent_contracts.id"),
        nullable=True,
        comment="关联合同ID（续签转移时使用）",
    )

    # 备注
    notes = Column(Text, comment="备注")

    # 操作人信息
    operator = Column(String(100), comment="操作人")
    operator_id = Column(String(50), comment="操作人ID")

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")

    # 关联关系
    contract = relationship(
        "RentContract",
        back_populates="deposit_ledger",
        foreign_keys=[contract_id],
    )
    related_contract = relationship(
        "RentContract",
        foreign_keys=[related_contract_id],
    )

    def __repr__(self):
        return f"<RentDepositLedger(contract_id={self.contract_id}, type={self.transaction_type}, amount={self.amount})>"  # pragma: no cover


class RentTerm(Base):
    """租金条款模型"""

    __tablename__ = "rent_terms"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    contract_id = Column(
        String, ForeignKey("rent_contracts.id"), nullable=False, comment="关联合同ID"
    )

    # 时间段
    start_date = Column(Date, nullable=False, comment="条款开始日期")
    end_date = Column(Date, nullable=False, comment="条款结束日期")

    # 租金信息
    monthly_rent = Column(DECIMAL(15, 2), nullable=False, comment="月租金金额")
    rent_description = Column(String(500), comment="租金描述")

    # 其他费用
    management_fee = Column(DECIMAL(15, 2), default=0, comment="管理费")
    other_fees = Column(DECIMAL(15, 2), default=0, comment="其他费用")
    total_monthly_amount = Column(DECIMAL(15, 2), comment="月总金额")

    # 系统字段
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间"
    )

    # 关联关系
    contract = relationship("RentContract", back_populates="rent_terms")

    def __repr__(self):
        return f"<RentTerm(contract_id={self.contract_id}, monthly_rent={self.monthly_rent})>"  # pragma: no cover


class RentLedger(Base):
    """租金台账模型"""

    __tablename__ = "rent_ledger"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # 关联信息
    contract_id = Column(
        String, ForeignKey("rent_contracts.id"), nullable=False, comment="关联合同ID"
    )
    asset_id = Column(
        String, ForeignKey("assets.id"), nullable=True, comment="关联资产ID"
    )
    ownership_id = Column(
        String, ForeignKey("ownerships.id"), nullable=False, comment="权属方ID"
    )

    # 时间信息
    year_month = Column(String(7), nullable=False, comment="年月，格式：YYYY-MM")
    due_date = Column(Date, nullable=False, comment="应缴日期")

    # 金额信息
    due_amount = Column(DECIMAL(15, 2), nullable=False, comment="应收金额")
    paid_amount = Column(DECIMAL(15, 2), default=0, comment="实收金额")
    overdue_amount = Column(DECIMAL(15, 2), default=0, comment="逾期金额")

    # 支付状态
    payment_status = Column(
        String(20), default="未支付", comment="支付状态：未支付/部分支付/已支付/逾期"
    )
    payment_date = Column(Date, comment="支付日期")
    payment_method = Column(String(50), comment="支付方式")
    payment_reference = Column(String(100), comment="支付参考号")

    # 滞纳金
    late_fee = Column(DECIMAL(15, 2), default=0, comment="滞纳金")
    late_fee_days = Column(Integer, default=0, comment="滞纳天数")

    # 备注
    notes = Column(Text, comment="备注")

    # 系统字段
    data_status = Column(String(20), default="正常", comment="数据状态")
    version = Column(Integer, default=1, comment="版本号")

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间"
    )

    # 关联关系
    contract = relationship("RentContract", back_populates="rent_ledger")
    asset = relationship("Asset")
    ownership = relationship("Ownership")

    def __repr__(self):
        return f"<RentLedger(contract_id={self.contract_id}, year_month={self.year_month}, payment_status={self.payment_status})>"  # pragma: no cover


class ServiceFeeLedger(Base):
    """服务费台账模型 - V2 新增（用于委托运营模式）"""

    __tablename__ = "service_fee_ledger"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # 关联信息
    contract_id = Column(
        String,
        ForeignKey("rent_contracts.id"),
        nullable=False,
        comment="关联委托运营合同ID",
    )
    source_ledger_id = Column(
        String,
        ForeignKey("rent_ledger.id"),
        nullable=True,
        comment="关联的租金台账ID（触发来源）",
    )

    # 服务费信息
    year_month = Column(String(7), nullable=False, comment="年月，格式：YYYY-MM")
    paid_rent_amount = Column(
        DECIMAL(15, 2), nullable=False, comment="实收租金（计算基数）"
    )
    fee_rate = Column(DECIMAL(5, 4), nullable=False, comment="服务费率")
    fee_amount = Column(DECIMAL(15, 2), nullable=False, comment="服务费金额")

    # 结算状态
    settlement_status = Column(
        String(20), default="待结算", comment="结算状态：待结算/已结算"
    )
    settlement_date = Column(Date, comment="结算日期")

    # 备注
    notes = Column(Text, comment="备注")

    # 操作人信息
    operator = Column(String(100), comment="操作人")
    operator_id = Column(String(50), comment="操作人ID")

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间"
    )

    # 关联关系
    contract = relationship("RentContract", back_populates="service_fee_ledger")
    source_ledger = relationship("RentLedger")

    def __repr__(self):
        return f"<ServiceFeeLedger(contract_id={self.contract_id}, fee_amount={self.fee_amount})>"  # pragma: no cover


class RentContractHistory(Base):
    """租金合同历史记录模型"""

    __tablename__ = "rent_contract_history"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    contract_id = Column(
        String, ForeignKey("rent_contracts.id"), nullable=False, comment="关联合同ID"
    )

    # 变更信息
    change_type = Column(
        String(50), nullable=False, comment="变更类型：创建/更新/删除/状态变更"
    )
    change_description = Column(Text, comment="变更描述")

    # 变更前数据
    old_data = Column(JSON, comment="变更前数据")

    # 变更后数据
    new_data = Column(JSON, comment="变更后数据")

    # 操作人信息
    operator = Column(String(100), comment="操作人")
    operator_id = Column(String(50), comment="操作人ID")

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")

    # 关联关系
    contract = relationship("RentContract")

    def __repr__(self):
        return f"<RentContractHistory(contract_id={self.contract_id}, change_type={self.change_type})>"  # pragma: no cover


class RentContractAttachment(Base):
    """合同附件模型 - V2 新增"""

    __tablename__ = "rent_contract_attachments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # 关联信息
    contract_id = Column(
        String, ForeignKey("rent_contracts.id"), nullable=False, comment="关联合同ID"
    )

    # 附件信息
    file_name = Column(String(255), nullable=False, comment="文件名")
    file_path = Column(String(500), nullable=False, comment="文件存储路径")
    file_size = Column(Integer, comment="文件大小(字节)")
    mime_type = Column(String(100), comment="文件MIME类型")
    file_type = Column(
        String(50), default="other", comment="文件类型：contract_scan/id_card/other"
    )

    # 描述
    description = Column(Text, comment="附件描述")

    # 上传信息
    uploader = Column(String(100), comment="上传人")
    uploader_id = Column(String(50), comment="上传人ID")

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, comment="上传时间")

    # 关联关系
    contract = relationship("RentContract", back_populates="attachments")

    def __repr__(self):
        return f"<RentContractAttachment(contract_id={self.contract_id}, file_name={self.file_name})>"  # pragma: no cover
