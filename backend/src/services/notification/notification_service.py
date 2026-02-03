"""
通知服务
"""

from datetime import date, datetime
from typing import Any

from sqlalchemy.orm import Session

from ...crud.notification import notification_crud
from ...models.auth import User
from ...models.notification import Notification


class NotificationService:
    """通知服务层"""

    def list_active_users(self, db: Session) -> list[User]:
        return db.query(User).filter(User.is_active.is_(True)).all()

    def list_notifications(
        self,
        db: Session,
        *,
        user_id: str,
        page: int,
        page_size: int,
        is_read: bool | None = None,
        type: str | None = None,
    ) -> dict[str, Any]:
        skip = (page - 1) * page_size
        items, total = notification_crud.get_multi_with_filters(
            db,
            recipient_id=user_id,
            skip=skip,
            limit=page_size,
            is_read=is_read,
            type=type,
        )
        unread_count = notification_crud.count_unread(db, recipient_id=user_id)
        return {
            "items": items,
            "total": total,
            "unread_count": unread_count,
        }

    def find_existing_notification(
        self,
        db: Session,
        *,
        recipient_id: str,
        related_entity_type: str,
        related_entity_id: str,
        notification_type: str,
        require_unread: bool = False,
        created_since: date | datetime | None = None,
    ) -> Notification | None:
        query = db.query(Notification).filter(
            Notification.recipient_id == recipient_id,
            Notification.related_entity_type == related_entity_type,
            Notification.related_entity_id == related_entity_id,
            Notification.type == notification_type,
        )

        if require_unread:
            query = query.filter(Notification.is_read.is_(False))

        if created_since is not None:
            query = query.filter(Notification.created_at >= created_since)

        return query.first()

    def get_unread_count(self, db: Session, *, user_id: str) -> int:
        return notification_crud.count_unread(db, recipient_id=user_id)

    def mark_as_read(
        self, db: Session, *, user_id: str, notification_id: str
    ) -> Notification | None:
        return notification_crud.mark_as_read(
            db, notification_id=notification_id, recipient_id=user_id
        )

    def mark_all_as_read(self, db: Session, *, user_id: str) -> int:
        return notification_crud.mark_all_as_read(db, recipient_id=user_id)

    def delete_notification(
        self, db: Session, *, user_id: str, notification_id: str
    ) -> bool:
        return notification_crud.delete(
            db, notification_id=notification_id, recipient_id=user_id
        )


notification_service = NotificationService()
