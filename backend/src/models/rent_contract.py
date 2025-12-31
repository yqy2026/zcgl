"""
租金台账相关数据库模型
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    DECIMAL,
    JSON,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from ..database import Base


class RentContract(Base):
    """租金合同模型"""

    __tablename__ = "rent_contracts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # 基本信息
    contract_number = Column(
        String(100), unique=True, nullable=False, comment="合同编号"
    )
    asset_id = Column(
        String, ForeignKey("assets.id"), nullable=False, comment="关联资产ID"
    )
    ownership_id = Column(
        String, ForeignKey("ownerships.id"), nullable=False, comment="权属方ID"
    )

    # 承租方信息
    tenant_name = Column(String(200), nullable=False, comment="承租方名称")
    tenant_contact = Column(String(100), comment="承租方联系人")
    tenant_phone = Column(String(20), comment="承租方联系电话")
    tenant_address = Column(String(500), comment="承租方地址")

    # 合同日期信息
    sign_date = Column(Date, nullable=False, comment="签订日期")
    start_date = Column(Date, nullable=False, comment="租期开始日期")
    end_date = Column(Date, nullable=False, comment="租期结束日期")

    # 金额信息
    total_deposit = Column(DECIMAL(15, 2), default=0, comment="总押金金额")
    monthly_rent_base = Column(DECIMAL(15, 2), comment="基础月租金")

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

    # 关联关系
    asset = relationship("Asset", back_populates="rent_contracts")
    ownership = relationship("Ownership", back_populates="owned_rent_contracts")
    rent_terms = relationship(
        "RentTerm", back_populates="contract", cascade="all, delete-orphan"
    )
    rent_ledger = relationship(
        "RentLedger", back_populates="contract", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<RentContract(contract_number={self.contract_number}, tenant_name={self.tenant_name})>"  # pragma: no cover


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
        String, ForeignKey("assets.id"), nullable=False, comment="关联资产ID"
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
