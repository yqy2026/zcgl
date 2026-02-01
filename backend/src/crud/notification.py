"""
通知 CRUD 操作
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from ..models.notification import Notification


class NotificationCRUD:
    """通知 CRUD 操作类"""

    def _apply_filters(
        self,
        query: Any,
        *,
        recipient_id: str,
        is_read: bool | None = None,
        type: str | None = None,
    ) -> Any:
        query = query.filter(Notification.recipient_id == recipient_id)

        if is_read is not None:
            query = query.filter(Notification.is_read == is_read)

        if type is not None:
            query = query.filter(Notification.type == type)

        return query

    def get(
        self,
        db: Session,
        *,
        notification_id: str,
        recipient_id: str | None = None,
    ) -> Notification | None:
        query = db.query(Notification).filter(Notification.id == notification_id)
        if recipient_id is not None:
            query = query.filter(Notification.recipient_id == recipient_id)
        return query.first()

    def get_multi_with_filters(
        self,
        db: Session,
        *,
        recipient_id: str,
        skip: int = 0,
        limit: int = 100,
        is_read: bool | None = None,
        type: str | None = None,
    ) -> tuple[list[Notification], int]:
        query = self._apply_filters(
            db.query(Notification),
            recipient_id=recipient_id,
            is_read=is_read,
            type=type,
        )

        total = query.count()
        items = (
            query.order_by(Notification.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return items, total

    def count_unread(self, db: Session, *, recipient_id: str) -> int:
        return (
            db.query(Notification)
            .filter(
                Notification.recipient_id == recipient_id,
                Notification.is_read.is_(False),
            )
            .count()
        )

    def mark_as_read(
        self, db: Session, *, notification_id: str, recipient_id: str
    ) -> Notification | None:
        notification = self.get(
            db, notification_id=notification_id, recipient_id=recipient_id
        )
        if not notification:
            return None

        notification.mark_as_read()
        db.commit()
        db.refresh(notification)
        return notification

    def mark_all_as_read(self, db: Session, *, recipient_id: str) -> int:
        updated = (
            db.query(Notification)
            .filter(
                Notification.recipient_id == recipient_id,
                Notification.is_read.is_(False),
            )
            .update({"is_read": True, "read_at": datetime.now(UTC)})
        )
        db.commit()
        return int(updated or 0)

    def delete(self, db: Session, *, notification_id: str, recipient_id: str) -> bool:
        notification = self.get(
            db, notification_id=notification_id, recipient_id=recipient_id
        )
        if not notification:
            return False

        db.delete(notification)
        db.commit()
        return True


notification_crud = NotificationCRUD()
