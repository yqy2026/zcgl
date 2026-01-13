"""
联系人模型

支持权属方、项目、租户等多实体的联系人管理
"""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, Column, DateTime, String, Text
from sqlalchemy import Enum as SQLEnum

from ..database import Base


class ContactType(str, Enum):
    """联系人类型枚举"""

    PRIMARY = "primary"  # 主要联系人
    FINANCE = "finance"  # 财务联系人
    OPERATIONS = "operations"  # 运营联系人
    LEGAL = "legal"  # 法务联系人
    GENERAL = "general"  # 一般联系人


class Contact(Base):  # type: ignore[valid-type, misc]
    """
    联系人模型

    支持多种实体类型（权属方、项目、租户等）的联系人管理
    每个实体可以有多个联系人，其中可以指定一个主要联系人
    """

    __tablename__ = "contacts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # 关联实体信息
    entity_type = Column(
        String(50),
        nullable=False,
        index=True,
        comment="关联实体类型: ownership/project/tenant",
    )
    entity_id = Column(String, nullable=False, index=True, comment="关联实体ID")

    # 联系人基本信息
    name = Column(String(100), nullable=False, comment="联系人姓名")
    title = Column(String(100), comment="职位/头衔")
    department = Column(String(100), comment="部门")

    # 联系方式
    phone = Column(String(20), comment="手机号码")
    office_phone = Column(String(20), comment="办公电话")
    email = Column(String(200), comment="电子邮箱")
    wechat = Column(String(100), comment="微信号")
    address = Column(String(500), comment="地址")

    # 联系人分类
    contact_type: "Column[ContactType]" = Column(
        SQLEnum(ContactType),
        default=ContactType.GENERAL,
        nullable=False,
        comment="联系人类型: primary/finance/operations/legal/general",
    )
    is_primary = Column(
        Boolean, default=False, nullable=False, comment="是否主要联系人"
    )

    # 备注信息
    notes = Column(Text, comment="备注")
    preferred_contact_time = Column(String(100), comment="偏好联系时间")
    preferred_contact_method = Column(
        String(50), comment="偏好联系方式: phone/email/wechat"
    )

    # 系统字段
    is_active = Column(Boolean, default=True, nullable=False, comment="是否启用")

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间"
    )
    created_by = Column(String(100), comment="创建人")
    updated_by = Column(String(100), comment="更新人")

    def __repr__(self) -> str:
        return f"<Contact(id={self.id}, name={self.name}, entity_type={self.entity_type}, is_primary={self.is_primary})>"
