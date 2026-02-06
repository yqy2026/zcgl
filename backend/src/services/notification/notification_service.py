"""
通知服务
"""

from datetime import date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...crud.notification import notification_crud
from ...models.auth import User
from ...models.notification import Notification


class NotificationService:
    """通知服务层"""

    async def list_active_users_async(self, db: AsyncSession) -> list[User]:
        result = await db.execute(select(User).where(User.is_active.is_(True)))
        return list(result.scalars().all())

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
        stmt = select(Notification).where(
            Notification.recipient_id == recipient_id,
            Notification.related_entity_type == related_entity_type,
            Notification.related_entity_id == related_entity_id,
            Notification.type == notification_type,
        )

        if require_unread:
            stmt = stmt.where(Notification.is_read.is_(False))

        if created_since is not None:
            stmt = stmt.where(Notification.created_at >= created_since)

        result = await db.execute(stmt)
        return result.scalars().first()

    async def get_unread_count_async(self, db: AsyncSession, *, user_id: str) -> int:
        return await notification_crud.count_unread_async(db, recipient_id=user_id)

    async def mark_as_read_async(
        self, db: AsyncSession, *, user_id: str, notification_id: str
    ) -> Notification | None:
        return await notification_crud.mark_as_read_async(
            db, notification_id=notification_id, recipient_id=user_id
        )

    async def mark_all_as_read_async(self, db: AsyncSession, *, user_id: str) -> int:
        return await notification_crud.mark_all_as_read_async(
            db, recipient_id=user_id
        )

    async def delete_notification_async(
        self, db: AsyncSession, *, user_id: str, notification_id: str
    ) -> bool:
        return await notification_crud.delete_async(
            db, notification_id=notification_id, recipient_id=user_id
        )


notification_service = NotificationService()
