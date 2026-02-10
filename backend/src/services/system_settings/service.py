"""系统设置服务层。"""

import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ...crud.auth import AuditLogCRUD
from ...crud.security_event import security_event_crud

logger = logging.getLogger(__name__)


class SystemSettingsService:
    """系统设置相关服务。"""

    def create_audit_log(
        self,
        db: Any,
        *,
        user_id: str,
        action: str,
        resource_type: str,
        ip_address: str,
        user_agent: str,
        request_body: str,
    ) -> None:
        audit_crud: Any = AuditLogCRUD()
        audit_crud.create(
            db,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            ip_address=ip_address,
            user_agent=user_agent,
            request_body=request_body,
        )

    async def create_audit_log_async(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        action: str,
        resource_type: str,
        ip_address: str,
        user_agent: str,
        request_body: str,
    ) -> None:
        audit_crud = AuditLogCRUD()
        await audit_crud.create_async(
            db=db,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            ip_address=ip_address,
            user_agent=user_agent,
            request_body=request_body,
        )

    async def get_security_events(
        self,
        db: AsyncSession,
        *,
        skip: int,
        limit: int,
    ) -> tuple[list[Any], int]:
        return await security_event_crud.get_multi_with_count_async(
            db,
            skip=skip,
            limit=limit,
        )

    async def check_database_connection(self, db: AsyncSession) -> bool:
        try:
            await db.execute(text("SELECT 1"))
            return True
        except SQLAlchemyError:
            logger.error("数据库连接检查失败", exc_info=True)
            return False


system_settings_service = SystemSettingsService()


def get_system_settings_service() -> SystemSettingsService:
    return system_settings_service
