"""
通知服务
"""

import re
from datetime import date, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exception_handler import BusinessValidationError
from ...crud.notification import notification_crud
from ...models.auth import User
from ...models.notification import Notification, NotificationPriority, NotificationType

_PII_PATTERNS = (
    re.compile(r"1[3-9]\d{9}"),
    re.compile(r"\d{17}[\dXx]"),
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
)


def _contains_pii(value: str) -> bool:
    return any(pattern.search(value) is not None for pattern in _PII_PATTERNS)


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
        priority: str | None = None,
        require_unread: bool = False,
        created_since: date | datetime | None = None,
    ) -> Notification | None:
        return await notification_crud.find_existing_notification_async(
            db,
            recipient_id=recipient_id,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            notification_type=notification_type,
            priority=priority,
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
        priority: str | None = None,
        require_unread: bool = False,
        created_since: date | datetime | None = None,
    ) -> set[tuple[str, str]]:
        return await notification_crud.find_existing_notification_pairs_async(
            db,
            recipient_ids=recipient_ids,
            related_entity_type=related_entity_type,
            related_entity_ids=related_entity_ids,
            notification_type=notification_type,
            priority=priority,
            require_unread=require_unread,
            created_since=created_since,
        )

    async def get_unread_count_async(self, db: AsyncSession, *, user_id: str) -> int:
        return await notification_crud.count_unread_async(db, recipient_id=user_id)

    async def create_system_notice_async(
        self,
        db: AsyncSession,
        *,
        title: str,
        content: str,
        priority: str = NotificationPriority.NORMAL,
        related_entity_type: str | None = None,
        related_entity_id: str | None = None,
    ) -> list[Notification]:
        normalized_title = title.strip()
        normalized_content = content.strip()
        if normalized_title == "" or normalized_content == "":
            raise BusinessValidationError(
                "System notice title and content are required"
            )

        allowed_priorities = {
            NotificationPriority.LOW,
            NotificationPriority.NORMAL,
            NotificationPriority.HIGH,
            NotificationPriority.URGENT,
        }
        if priority not in allowed_priorities:
            raise BusinessValidationError(
                "Invalid system notice priority",
                field_errors={"priority": [str(priority)]},
            )

        if related_entity_type is not None or related_entity_id is not None:
            raise BusinessValidationError(
                "System notices must not bind business entities"
            )

        if _contains_pii(normalized_title) or _contains_pii(normalized_content):
            raise BusinessValidationError("System notice content must not contain PII")

        active_users = await notification_crud.get_active_users_async(db)
        notifications: list[Notification] = []
        for user in active_users:
            notification = Notification(
                recipient_id=str(user.id),
                type=NotificationType.SYSTEM_NOTICE,
                priority=priority,
                title=normalized_title,
                content=normalized_content,
                related_entity_type=None,
                related_entity_id=None,
                is_read=False,
                is_sent_wecom=False,
            )
            db.add(notification)
            notifications.append(notification)

        await db.flush()
        await db.commit()
        return notifications

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


notification_service = NotificationService()
