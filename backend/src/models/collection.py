"""
催缴管理相关数据库模型
"""

import enum
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    DECIMAL,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

if TYPE_CHECKING:
    from .rent_contract import RentContract
    from .rent_ledger import RentLedger


class CollectionMethod(str, enum.Enum):
    """催缴方式枚举"""

    PHONE = "phone"  # 电话催缴
    SMS = "sms"  # 短信催缴
    EMAIL = "email"  # 邮件催缴
    WECOM = "wecom"  # 企业微信催缴
    VISIT = "visit"  # 上门催缴
    LETTER = "letter"  # 催缴函
    OTHER = "other"  # 其他


class CollectionStatus(str, enum.Enum):
    """催缴状态枚举"""

    PENDING = "pending"  # 待催缴
    IN_PROGRESS = "in_progress"  # 催缴中
    SUCCESS = "success"  # 催缴成功
    FAILED = "failed"  # 催缴失败
    PARTIAL = "partial"  # 部分成功


class CollectionRecord(Base):
    """催缴记录模型 - V2 新增"""

    __tablename__ = "collection_records"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # 关联信息
    ledger_id = Column(
        String,
        ForeignKey("rent_ledger.id"),
        nullable=False,
        comment="关联的租金台账ID",
    )
    contract_id = Column(
        String,
        ForeignKey("rent_contracts.id"),
        nullable=False,
        comment="关联合同ID",
    )

    # 催缴信息
    collection_method: Mapped[CollectionMethod] = mapped_column(
        Enum(CollectionMethod),
        nullable=False,
        comment="催缴方式：电话/短信/邮件/企业微信/上门/催缴函",
    )
    collection_date = Column(Date, nullable=False, comment="催缴日期")
    collection_status: Mapped[CollectionStatus] = mapped_column(
        Enum(CollectionStatus),
        default=CollectionStatus.PENDING,
        comment="催缴状态",
    )

    # 联系人信息
    contacted_person = Column(String(100), comment="被联系人")
    contact_phone = Column(String(20), comment="联系电话")

    # 催缴结果
    promised_amount: Mapped[Decimal | None] = mapped_column(
        DECIMAL(15, 2), comment="承诺付款金额"
    )
    promised_date = Column(Date, comment="承诺付款日期")
    actual_payment_amount: Mapped[Decimal | None] = mapped_column(
        DECIMAL(15, 2), comment="实际付款金额"
    )

    # 备注信息
    collection_notes = Column(Text, comment="催缴备注")
    next_follow_up_date = Column(Date, comment="下次跟进日期")

    # 操作人信息
    operator = Column(String(100), comment="操作人")
    operator_id = Column(String(50), comment="操作人ID")

    # 时间戳
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), comment="创建时间")
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        comment="更新时间",
    )

    # 关联关系
    ledger: Mapped["RentLedger"] = relationship("RentLedger")
    contract: Mapped["RentContract"] = relationship("RentContract")

    def __repr__(self) -> str:
        return f"<CollectionRecord(ledger_id={self.ledger_id}, method={self.collection_method}, status={self.collection_status})>"  # pragma: no cover
