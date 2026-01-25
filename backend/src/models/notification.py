"""
通知模型

支持站内消息通知，用于合同到期提醒、付款逾期提醒、审批待办等场景
"""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, relationship

from ..database import Base

if TYPE_CHECKING:
    from .auth import User


class NotificationType:
    """通知类型常量"""

    CONTRACT_EXPIRING = "contract_expiring"  # 合同即将到期
    CONTRACT_EXPIRED = "contract_expired"  # 合同已到期
    PAYMENT_OVERDUE = "payment_overdue"  # 付款逾期
    PAYMENT_DUE = "payment_due"  # 付款到期提醒
    APPROVAL_PENDING = "approval_pending"  # 审批待办
    SYSTEM_NOTICE = "system_notice"  # 系统通知


class NotificationPriority:
    """通知优先级常量"""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class Notification(Base):
    """
    通知模型

    用于存储站内消息通知，支持多种业务场景
    """

    __tablename__ = "notifications"

    # 基础字段
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    recipient_id = Column(
        String(36), ForeignKey("users.id"), nullable=False, comment="接收用户ID"
    )
    type = Column(String(50), nullable=False, index=True, comment="通知类型")
    priority = Column(
        String(20), default=NotificationPriority.NORMAL, comment="通知优先级"
    )

    # 内容字段
    title = Column(String(200), nullable=False, comment="通知标题")
    content = Column(Text, nullable=False, comment="通知内容")

    # 关联实体字段
    related_entity_type = Column(
        String(50), comment="关联实体类型 (contract/asset/ownership)"
    )
    related_entity_id = Column(String(36), comment="关联实体ID")

    # 状态字段
    is_read = Column(Boolean, default=False, index=True, comment="是否已读")
    read_at = Column(DateTime, comment="已读时间")

    # 企业微信推送状态
    is_sent_wecom = Column(Boolean, default=False, comment="是否已发送企业微信")
    wecom_sent_at = Column(DateTime, comment="企业微信发送时间")
    wecom_send_error = Column(Text, comment="企业微信发送错误信息")

    # 额外数据（JSON格式存储）
    extra_data = Column(Text, comment="额外数据（JSON格式）")

    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC), comment="创建时间"
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        comment="更新时间",
    )

    # 关系
    recipient: Mapped["User"] = relationship("User", back_populates="notifications")

    def mark_as_read(self) -> None:
        """标记通知为已读"""
        if not cast(bool, self.is_read):
            object.__setattr__(self, "is_read", True)
            object.__setattr__(self, "read_at", datetime.now(UTC))

    def mark_as_unread(self) -> None:
        """标记通知为未读"""
        object.__setattr__(self, "is_read", False)
        object.__setattr__(self, "read_at", None)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "recipient_id": self.recipient_id,
            "type": self.type,
            "priority": self.priority,
            "title": self.title,
            "content": self.content,
            "related_entity_type": self.related_entity_type,
            "related_entity_id": self.related_entity_id,
            "is_read": self.is_read,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "is_sent_wecom": self.is_sent_wecom,
            "wecom_sent_at": self.wecom_sent_at.isoformat()
            if self.wecom_sent_at
            else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<Notification(id={self.id}, type={self.type}, title={self.title}, is_read={self.is_read})>"
