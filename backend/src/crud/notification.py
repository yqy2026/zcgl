"""
通知 CRUD 操作
"""

from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.auth import User
from ..models.notification import Notification


class NotificationCRUD:
    """通知 CRUD 操作类"""

    def _apply_filters_stmt(
        self,
        stmt: Any,
        *,
        recipient_id: str,
        is_read: bool | None = None,
        type: str | None = None,
    ) -> Any:
        stmt = stmt.where(Notification.recipient_id == recipient_id)

        if is_read is not None:
            stmt = stmt.where(Notification.is_read == is_read)

        if type is not None:
            stmt = stmt.where(Notification.type == type)

        return stmt

    async def get_async(
        self,
        db: AsyncSession,
        *,
        notification_id: str,
        recipient_id: str | None = None,
    ) -> Notification | None:
        stmt = select(Notification).where(Notification.id == notification_id)
        if recipient_id is not None:
            stmt = stmt.where(Notification.recipient_id == recipient_id)
        return (await db.execute(stmt)).scalars().first()

    async def get_multi_with_filters_async(
        self,
        db: AsyncSession,
        *,
        recipient_id: str,
        skip: int = 0,
        limit: int = 100,
        is_read: bool | None = None,
        type: str | None = None,
    ) -> tuple[list[Notification], int]:
        base_stmt = self._apply_filters_stmt(
            select(Notification),
            recipient_id=recipient_id,
            is_read=is_read,
            type=type,
        )
        count_stmt = select(func.count()).select_from(Notification)
        count_stmt = self._apply_filters_stmt(
            count_stmt, recipient_id=recipient_id, is_read=is_read, type=type
        )
        total = int((await db.execute(count_stmt)).scalar() or 0)
        result = await db.execute(
            base_stmt.order_by(Notification.created_at.desc()).offset(skip).limit(limit)
        )
        items = list(result.scalars().all())
        return items, total

    async def count_unread_async(self, db: AsyncSession, *, recipient_id: str) -> int:
        stmt = (
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.recipient_id == recipient_id,
                Notification.is_read.is_(False),
            )
        )
        return int((await db.execute(stmt)).scalar() or 0)

    async def mark_as_read_async(
        self, db: AsyncSession, *, notification_id: str, recipient_id: str
    ) -> Notification | None:
        notification = await self.get_async(
            db, notification_id=notification_id, recipient_id=recipient_id
        )
        if not notification:
            return None

        notification.mark_as_read()
        await db.commit()
        await db.refresh(notification)
        return notification

    async def mark_all_as_read_async(
        self, db: AsyncSession, *, recipient_id: str
    ) -> int:
        stmt = (
            update(Notification)
            .where(
                Notification.recipient_id == recipient_id,
                Notification.is_read.is_(False),
            )
            .values(is_read=True, read_at=datetime.now(UTC).replace(tzinfo=None))
        )
        result = await db.execute(stmt)
        await db.commit()
        return int(getattr(result, "rowcount", 0) or 0)

    async def delete_async(
        self, db: AsyncSession, *, notification_id: str, recipient_id: str
    ) -> bool:
        notification = await self.get_async(
            db, notification_id=notification_id, recipient_id=recipient_id
        )
        if not notification:
            return False

        await db.delete(notification)
        await db.commit()
        return True

    async def get_active_users_async(self, db: AsyncSession) -> list[User]:
        stmt = select(User).where(User.is_active.is_(True))
        return list((await db.execute(stmt)).scalars().all())

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

        return (await db.execute(stmt)).scalars().first()

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
        if len(recipient_ids) == 0 or len(related_entity_ids) == 0:
            return set()

        stmt = select(Notification.recipient_id, Notification.related_entity_id).where(
            Notification.recipient_id.in_(recipient_ids),
            Notification.related_entity_type == related_entity_type,
            Notification.related_entity_id.in_(related_entity_ids),
            Notification.type == notification_type,
        )

        if require_unread:
            stmt = stmt.where(Notification.is_read.is_(False))

        if created_since is not None:
            stmt = stmt.where(Notification.created_at >= created_since)

        rows = (await db.execute(stmt)).all()
        return {
            (str(recipient_id), str(related_entity_id))
            for recipient_id, related_entity_id in rows
            if related_entity_id is not None
        }


notification_crud = NotificationCRUD()
