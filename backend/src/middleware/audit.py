"""Audit dependency helpers for authenticated API routes."""

from __future__ import annotations

import logging

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..crud.auth import AuditLogCRUD
from ..database import get_async_db
from ..models.auth import User
from .identity import get_optional_current_user

logger = logging.getLogger(__name__)


class AuditLogger:
    """审计日志记录器"""

    def __init__(
        self,
        action: str,
        resource_type: str | None = None,
    ):
        self.action = action
        self.resource_type = resource_type

    async def __call__(
        self,
        request: Request,
        current_user: User | None = Depends(get_optional_current_user),
        db: AsyncSession = Depends(get_async_db),
    ) -> User | None:
        """记录审计日志"""
        return await self.resolve(request=request, current_user=current_user, db=db)

    async def resolve(
        self,
        *,
        request: Request,
        current_user: User | None,
        db: AsyncSession,
    ) -> User | None:
        if current_user is None:
            return None

        try:
            from ..middleware.security_middleware import get_client_ip

            ip_address = get_client_ip(request)
            user_agent = request.headers.get("user-agent", "")
            request_params = str(request.query_params) if request.query_params else None

            await self.log_action(
                db=db,
                user=current_user,
                api_endpoint=request.url.path,
                http_method=request.method,
                request_params=request_params,
                ip_address=ip_address,
                user_agent=user_agent,
            )
        except Exception as error:
            logger.warning("审计日志记录失败: %s", error)
        return current_user

    async def log_action(
        self,
        db: AsyncSession,
        user: User,
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
    ) -> None:
        audit_crud = AuditLogCRUD()
        await audit_crud.create_async(
            db=db,
            user_id=user.id,
            action=self.action,
            resource_type=self.resource_type,
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


def audit_action(action: str, resource_type: str | None = None) -> AuditLogger:
    """审计装饰器工厂函数"""
    return AuditLogger(action, resource_type)
