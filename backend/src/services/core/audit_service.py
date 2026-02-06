from datetime import datetime

from sqlalchemy import select
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
