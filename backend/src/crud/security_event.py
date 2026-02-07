
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.security_event import SecurityEvent


class SecurityEventCRUD:
    """安全事件CRUD操作"""

    async def get_multi_with_count_async(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        event_type: str | None = None,
        severity: str | None = None,
        user_id: str | None = None,
        ip_address: str | None = None,
    ) -> tuple[list[SecurityEvent], int]:
        stmt = select(SecurityEvent)
        count_stmt = select(func.count()).select_from(SecurityEvent)

        if event_type:
            stmt = stmt.where(SecurityEvent.event_type == event_type)
            count_stmt = count_stmt.where(SecurityEvent.event_type == event_type)
        if severity:
            stmt = stmt.where(SecurityEvent.severity == severity)
            count_stmt = count_stmt.where(SecurityEvent.severity == severity)
        if user_id:
            stmt = stmt.where(SecurityEvent.user_id == user_id)
            count_stmt = count_stmt.where(SecurityEvent.user_id == user_id)
        if ip_address:
            stmt = stmt.where(SecurityEvent.ip_address == ip_address)
            count_stmt = count_stmt.where(SecurityEvent.ip_address == ip_address)

        total = int((await db.execute(count_stmt)).scalar() or 0)
        result = await db.execute(
            stmt.order_by(SecurityEvent.created_at.desc()).offset(skip).limit(limit)
        )
        items = list(result.scalars().all())
        return items, total


security_event_crud = SecurityEventCRUD()
