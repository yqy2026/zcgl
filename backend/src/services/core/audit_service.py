from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...crud.auth import AuditLogCRUD
from ...models.auth import AuditLog

_audit_crud = AuditLogCRUD()


class AuditService:
    """审计日志服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_audit_log(
        self,
        user_id: str,
        action: str,
        resource_type: str | None = None,
        resource_id: str | None = None,
        resource_name: str | None = None,
        api_endpoint: str | None = None,
        http_method: str | None = None,
        request_params: str | None = None,
        request_body: str | None = None,
        response_status: int | None = None,
        response_message: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        session_id: str | None = None,
    ) -> AuditLog | None:
        """创建审计日志"""
        return await _audit_crud.create_async(
            self.db,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            api_endpoint=api_endpoint,
            http_method=http_method,
            request_params=request_params,
            request_body=request_body,
            response_status=response_status,
            response_message=response_message,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id,
        )

    async def get_login_statistics(self, days: int = 7) -> dict[str, Any]:
        """获取登录统计信息。"""
        return await _audit_crud.get_login_statistics_async(self.db, days=days)
