"""
通知API端点

提供站内消息通知的查询、标记已读、删除等功能
"""

from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ...database import get_db
from ...middleware.auth import get_current_active_user
from ...models.auth import User
from ...models.notification import Notification
from ...services.notification.scheduler import run_notification_tasks

router = APIRouter(tags=["Notifications"])


# ==================== Pydantic 模型 ====================


class NotificationResponse(BaseModel):
    """通知响应模型"""

    id: str
    type: str
    priority: str
    title: str
    content: str
    related_entity_type: str | None
    related_entity_id: str | None
    is_read: bool
    read_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    """通知列表响应模型"""

    items: list[NotificationResponse]
    total: int
    unread_count: int
    count: int  # 别名字段，兼容前端期望的 "count"


class MarkAsReadRequest(BaseModel):
    """标记已读请求模型"""

    notification_ids: list[str]


class UnreadCountResponse(BaseModel):
    """未读数量响应模型"""

    unread_count: int
    count: int  # 别名字段，兼容前端期望的 "count"


# ==================== API 端点 ====================


@router.get("/", response_model=NotificationListResponse)
async def get_notifications(
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(10, ge=1, le=100, description="每页数量"),
    is_read: bool | None = Query(None, description="筛选已读/未读"),
    type: str | None = Query(None, description="通知类型筛选"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    获取当前用户的通知列表

    - **page**: 页码，从1开始
    - **limit**: 每页数量，最大100
    - **is_read**: 筛选已读/未读通知
    - **type**: 按通知类型筛选
    """
    # 构建查询
    query = db.query(Notification).filter(Notification.recipient_id == current_user.id)

    if is_read is not None:
        query = query.filter(Notification.is_read == is_read)

    if type is not None:
        query = query.filter(Notification.type == type)

    # 按创建时间倒序排序
    query = query.order_by(Notification.created_at.desc())

    # 获取总数
    total = query.count()

    # 获取未读数量
    unread_count = (
        db.query(Notification)
        .filter(
            Notification.recipient_id == current_user.id, Notification.is_read == False
        )
        .count()
    )

    # 分页
    offset = (page - 1) * limit
    notifications = query.offset(offset).limit(limit).all()

    return NotificationListResponse(
        items=[NotificationResponse.model_validate(n) for n in notifications],
        total=total,
        unread_count=unread_count,
        count=unread_count,  # count 字段值等于 unread_count
    )


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    获取当前用户的未读通知数量
    """
    unread_count = (
        db.query(Notification)
        .filter(
            Notification.recipient_id == current_user.id, Notification.is_read == False
        )
        .count()
    )

    return UnreadCountResponse(
        unread_count=unread_count,
        count=unread_count,  # count 字段值等于 unread_count
    )


@router.post("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_as_read(
    notification_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    标记通知为已读
    """
    notification = (
        db.query(Notification)
        .filter(
            Notification.id == notification_id,
            Notification.recipient_id == current_user.id,
        )
        .first()
    )

    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="通知不存在")

    notification.mark_as_read()
    db.commit()

    return NotificationResponse.model_validate(notification)


@router.post("/read-all", response_model=dict)
async def mark_all_as_read(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    标记所有通知为已读
    """
    # 更新所有未读通知
    db.query(Notification).filter(
        Notification.recipient_id == current_user.id, Notification.is_read == False
    ).update({"is_read": True, "read_at": datetime.utcnow()})

    db.commit()

    return {"message": "已标记所有通知为已读"}


@router.delete("/{notification_id}", response_model=dict)
async def delete_notification(
    notification_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    删除通知
    """
    notification = (
        db.query(Notification)
        .filter(
            Notification.id == notification_id,
            Notification.recipient_id == current_user.id,
        )
        .first()
    )

    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="通知不存在")

    db.delete(notification)
    db.commit()

    return {"message": "通知已删除"}


@router.post("/run-tasks", response_model=dict)
async def run_notification_tasks_endpoint(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
):
    """
    手动触发通知任务（用于测试和管理）

    扫描合同到期和付款逾期，并生成相应的通知
    """
    # 检查用户权限（只有管理员可以手动触发）
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以手动触发通知任务",
        )

    # 在后台运行任务
    def run_tasks():
        try:
            result = run_notification_tasks()
            return result
        except Exception as e:
            return {"error": str(e)}

    background_tasks.add_task(run_tasks)

    return {
        "message": "通知任务已启动，正在后台执行",
        "note": "任务包括：扫描合同到期、扫描付款逾期、扫描即将到期的付款",
    }
