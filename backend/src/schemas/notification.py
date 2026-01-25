"""
通知相关的 Pydantic schemas
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class NotificationType(str, Enum):
    """通知类型枚举"""

    CONTRACT_EXPIRING = "contract_expiring"  # 合同即将到期
    CONTRACT_EXPIRED = "contract_expired"  # 合同已到期
    PAYMENT_OVERDUE = "payment_overdue"  # 付款逾期
    PAYMENT_DUE = "payment_due"  # 付款到期提醒
    APPROVAL_PENDING = "approval_pending"  # 审批待办
    SYSTEM_NOTICE = "system_notice"  # 系统通知


class NotificationPriority(str, Enum):
    """通知优先级枚举"""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationBase(BaseModel):
    """通知基础Schema"""

    type: NotificationType = Field(..., description="通知类型")
    priority: NotificationPriority = Field(
        default=NotificationPriority.NORMAL, description="通知优先级"
    )
    title: str = Field(..., max_length=200, description="通知标题")
    content: str = Field(..., description="通知内容")
    related_entity_type: str | None = Field(
        None, max_length=50, description="关联实体类型 (contract/asset/ownership)"
    )
    related_entity_id: str | None = Field(None, max_length=36, description="关联实体ID")
    extra_data: dict[str, Any] | None = Field(None, description="额外数据")


class NotificationCreate(NotificationBase):
    """创建通知Schema"""

    recipient_id: str = Field(..., max_length=36, description="接收用户ID")


class NotificationUpdate(BaseModel):
    """更新通知Schema"""

    is_read: bool | None = Field(None, description="是否已读")


class NotificationResponse(NotificationBase):
    """通知响应Schema"""

    id: str
    recipient_id: str
    is_read: bool = Field(default=False, description="是否已读")
    read_at: datetime | None = Field(None, description="已读时间")
    is_sent_wecom: bool = Field(default=False, description="是否已发送企业微信")
    wecom_sent_at: datetime | None = Field(None, description="企业微信发送时间")
    wecom_send_error: str | None = Field(None, description="企业微信发送错误信息")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationListResponse(BaseModel):
    """通知列表响应Schema"""

    items: list[NotificationResponse]
    total: int
    page: int
    page_size: int
    pages: int


class NotificationMarkReadRequest(BaseModel):
    """批量标记已读请求"""

    notification_ids: list[str] = Field(..., description="通知ID列表")


class NotificationSummary(BaseModel):
    """通知摘要统计"""

    total_count: int = Field(..., description="通知总数")
    unread_count: int = Field(..., description="未读数量")
    urgent_count: int = Field(..., description="紧急通知数量")
    today_count: int = Field(..., description="今日通知数量")
