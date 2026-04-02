"""
通知服务
"""

from datetime import date, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...crud.notification import notification_crud
from ...models.auth import User
from ...models.notification import Notification, NotificationPriority, NotificationType


class NotificationService:
    """通知服务层"""

    async def list_active_users_async(self, db: AsyncSession) -> list[User]:
        return await notification_crud.get_active_users_async(db)

    async def list_notifications_async(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        page: int,
        page_size: int,
        is_read: bool | None = None,
        type: str | None = None,
    ) -> dict[str, Any]:
        skip = (page - 1) * page_size
        items, total = await notification_crud.get_multi_with_filters_async(
            db,
            recipient_id=user_id,
            skip=skip,
            limit=page_size,
            is_read=is_read,
            type=type,
        )
        unread_count = await notification_crud.count_unread_async(
            db, recipient_id=user_id
        )
        return {
            "items": items,
            "total": total,
            "unread_count": unread_count,
        }

    async def find_existing_notification_async(
        self,
        db: AsyncSession,
        *,
        recipient_id: str,
        related_entity_type: str,
        related_entity_id: str,
        notification_type: str,
        require_unread: bool = False,
        created_since: date | datetime | None = None,
    ) -> Notification | None:
        return await notification_crud.find_existing_notification_async(
            db,
            recipient_id=recipient_id,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            notification_type=notification_type,
            require_unread=require_unread,
            created_since=created_since,
        )

    async def find_existing_notification_pairs_async(
        self,
        db: AsyncSession,
        *,
        recipient_ids: list[str],
        related_entity_type: str,
        related_entity_ids: list[str],
        notification_type: str,
        require_unread: bool = False,
        created_since: date | datetime | None = None,
    ) -> set[tuple[str, str]]:
        return await notification_crud.find_existing_notification_pairs_async(
            db,
            recipient_ids=recipient_ids,
            related_entity_type=related_entity_type,
            related_entity_ids=related_entity_ids,
            notification_type=notification_type,
            require_unread=require_unread,
            created_since=created_since,
        )

    async def get_unread_count_async(self, db: AsyncSession, *, user_id: str) -> int:
        return await notification_crud.count_unread_async(db, recipient_id=user_id)

    async def mark_as_read_async(
        self, db: AsyncSession, *, user_id: str, notification_id: str
    ) -> Notification | None:
        return await notification_crud.mark_as_read_async(
            db, notification_id=notification_id, recipient_id=user_id
        )

    async def mark_all_as_read_async(self, db: AsyncSession, *, user_id: str) -> int:
        return await notification_crud.mark_all_as_read_async(db, recipient_id=user_id)

    async def delete_notification_async(
        self, db: AsyncSession, *, user_id: str, notification_id: str
    ) -> bool:
        return await notification_crud.delete_async(
            db, notification_id=notification_id, recipient_id=user_id
        )

    async def create_approval_pending_notification(
        self,
        db: AsyncSession,
        *,
        recipient_id: str,
        approval_instance_id: str,
        business_type: str,
        business_id: str,
        starter_id: str,
        priority: str = NotificationPriority.HIGH,
    ) -> Notification:
        existing = await notification_crud.find_existing_notification_async(
            db,
            recipient_id=recipient_id,
            related_entity_type="approval",
            related_entity_id=approval_instance_id,
            notification_type=NotificationType.APPROVAL_PENDING,
            require_unread=True,
        )
        if existing is not None:
            return existing

        notification = Notification(
            recipient_id=recipient_id,
            type=NotificationType.APPROVAL_PENDING,
            priority=priority,
            title="待处理审批",
            content=f"您有一条待处理审批：{business_type} {business_id}（发起人：{starter_id}）",
            related_entity_type="approval",
            related_entity_id=approval_instance_id,
            is_read=False,
        )
        db.add(notification)
        await db.flush()
        return notification

    async def mark_approval_notifications_read(
        self,
        db: AsyncSession,
        *,
        approval_instance_id: str,
    ) -> int:
        return await notification_crud.mark_related_notifications_as_read_async(
            db,
            related_entity_type="approval",
            related_entity_id=approval_instance_id,
            notification_type=NotificationType.APPROVAL_PENDING,
        )


notification_service = NotificationService()
