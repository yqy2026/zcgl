from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...models.auth import AuditLog, User
from ...models.rbac import Role, UserRoleAssignment


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
        stmt = select(User).where(User.id == user_id)
        user = (await self.db.execute(stmt)).scalars().first()
        if not user:
            return None

        audit_log = AuditLog()
        audit_log.user_id = user_id
        audit_log.username = user.username
        role_stmt = (
            select(Role.display_name)
            .join(UserRoleAssignment, UserRoleAssignment.role_id == Role.id)
            .where(
                UserRoleAssignment.user_id == user_id,
                UserRoleAssignment.is_active.is_(True),
                UserRoleAssignment.expires_at.is_(None)
                | (UserRoleAssignment.expires_at > datetime.utcnow()),
            )
            .order_by(Role.level.asc())
            .limit(1)
        )
        audit_log.user_role = (await self.db.execute(role_stmt)).scalar()
        audit_log.user_organization = getattr(user, "default_organization_id", None)
        audit_log.action = action
        audit_log.resource_type = resource_type
        audit_log.resource_id = resource_id
        audit_log.resource_name = resource_name
        audit_log.api_endpoint = api_endpoint
        audit_log.http_method = http_method
        audit_log.request_params = request_params
        audit_log.request_body = request_body
        audit_log.response_status = response_status
        audit_log.response_message = response_message
        audit_log.ip_address = ip_address
        audit_log.user_agent = user_agent
        audit_log.session_id = session_id

        self.db.add(audit_log)
        await self.db.commit()
        await self.db.refresh(audit_log)

        return audit_log

    async def get_login_statistics(self, days: int = 7) -> dict[str, Any]:
        """获取登录统计信息。"""
        start_date = datetime.now() - timedelta(days=days)
        total_stmt = (
            select(func.count(AuditLog.id))
            .where(
                AuditLog.action == "user_login",
                AuditLog.created_at >= start_date,
            )
            .select_from(AuditLog)
        )
        success_stmt = (
            select(func.count(AuditLog.id))
            .where(
                AuditLog.action == "user_login",
                AuditLog.created_at >= start_date,
                AuditLog.response_status == 200,
            )
            .select_from(AuditLog)
        )

        total_logins = int((await self.db.execute(total_stmt)).scalar() or 0)
        successful_logins = int((await self.db.execute(success_stmt)).scalar() or 0)
        failed_logins = max(total_logins - successful_logins, 0)

        return {
            "total_logins": total_logins,
            "successful_logins": successful_logins,
            "failed_logins": failed_logins,
            "success_rate": round(successful_logins / total_logins * 100, 2)
            if total_logins > 0
            else 0,
        }


class AuditLogServiceAdapter:
    """兼容旧调用方式的审计记录适配器（服务层）。"""

    async def create_async(
        self,
        db: AsyncSession,
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
        audit_service = AuditService(db)
        return await audit_service.create_audit_log(
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
