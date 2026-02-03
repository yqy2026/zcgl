
from typing import Any

from sqlalchemy.orm import Session

from ..models.security_event import SecurityEvent


class SecurityEventCRUD:
    """安全事件CRUD操作"""

    def _base_query(self, db: Session) -> Any:
        return db.query(SecurityEvent)

    def get_multi_with_count(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        event_type: str | None = None,
        severity: str | None = None,
        user_id: str | None = None,
        ip_address: str | None = None,
    ) -> tuple[list[SecurityEvent], int]:
        query = self._base_query(db)

        if event_type:
            query = query.filter(SecurityEvent.event_type == event_type)
        if severity:
            query = query.filter(SecurityEvent.severity == severity)
        if user_id:
            query = query.filter(SecurityEvent.user_id == user_id)
        if ip_address:
            query = query.filter(SecurityEvent.ip_address == ip_address)

        total = query.count()
        items = (
            query.order_by(SecurityEvent.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return items, total


security_event_crud = SecurityEventCRUD()
