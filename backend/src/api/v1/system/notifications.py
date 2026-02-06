"""
通知API端点

提供站内消息通知的查询、标记已读、删除等功能
"""

from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.exception_handler import forbidden, not_found
from ....core.response_handler import APIResponse, PaginatedData, ResponseHandler
from ....database import get_async_db
from ....middleware.auth import get_current_active_user
from ....services.permission.rbac_service import RBACService
from ....models.auth import User
from ....services.notification.notification_service import notification_service
from ....services.notification.scheduler import run_notification_tasks

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


@router.get("", response_model=APIResponse[PaginatedData[NotificationResponse]])
@router.get("/", response_model=APIResponse[PaginatedData[NotificationResponse]])
async def get_notifications(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    is_read: bool | None = Query(None, description="筛选已读/未读"),
    type: str | None = Query(None, description="通知类型筛选"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> JSONResponse:
    """
    获取当前用户的通知列表

    - **page**: 页码，从1开始
    - **limit**: 每页数量，最大100
    - **is_read**: 筛选已读/未读通知
    - **type**: 按通知类型筛选
    """

    result = await notification_service.list_notifications_async(
        db,
        user_id=str(current_user.id),
        page=page,
        page_size=page_size,
        is_read=is_read,
        type=type,
    )
    notifications = result["items"]
    total = result["total"]
    unread_count = result["unread_count"]

    return ResponseHandler.paginated(
        data=[NotificationResponse.model_validate(n) for n in notifications],
        page=page,
        page_size=page_size,
        total=total,
        message="获取通知列表成功",
        extra={"unread_count": unread_count, "count": unread_count},
    )


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> UnreadCountResponse:
    """
    获取当前用户的未读通知数量
    """

    unread_count = await notification_service.get_unread_count_async(
        db, user_id=str(current_user.id)
    )

    return UnreadCountResponse(
        unread_count=unread_count,
        count=unread_count,
    )


@router.post("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_as_read(
    notification_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> NotificationResponse:
    """
    标记通知为已读
    """

    notification = await notification_service.mark_as_read_async(
        db, user_id=str(current_user.id), notification_id=notification_id
    )

    if not notification:
        raise not_found(
            "通知不存在", resource_type="notification", resource_id=notification_id
        )

    return NotificationResponse.model_validate(notification)


@router.post("/read-all", response_model=dict)
async def mark_all_as_read(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, str]:
    """
    标记所有通知为已读
    """

    await notification_service.mark_all_as_read_async(db, user_id=str(current_user.id))

    return {"message": "已标记所有通知为已读"}


@router.delete("/{notification_id}", response_model=dict)
async def delete_notification(
    notification_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, str]:
    """
    删除通知
    """

    deleted = await notification_service.delete_notification_async(
        db, user_id=str(current_user.id), notification_id=notification_id
    )
    if not deleted:
        raise not_found(
            "通知不存在", resource_type="notification", resource_id=notification_id
        )

    return {"message": "通知已删除"}


@router.post("/run-tasks", response_model=dict)
async def run_notification_tasks_endpoint(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, str]:
    """
    手动触发通知任务（用于测试和管理）

    扫描合同到期和付款逾期，并生成相应的通知
    """
    # 检查用户权限（只有管理员可以手动触发）
    rbac_service = RBACService(db)
    if not await rbac_service.is_admin(current_user.id):
        raise forbidden("只有管理员可以手动触发通知任务")

    # 在后台运行任务
    async def run_tasks() -> dict[str, str]:
        try:
            result = await run_notification_tasks()
            return result
        except Exception as e:
            return {"error": str(e)}

    background_tasks.add_task(run_tasks)

    return {
        "message": "通知任务已启动，正在后台执行",
        "note": "任务包括：扫描合同到期、扫描付款逾期、扫描即将到期的付款",
    }
