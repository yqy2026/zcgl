"""
审计日志API路由

包含: 审计日志统计
"""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from .....database import get_async_db
from .....middleware.auth import AuthzContext, require_authz
from .....schemas.auth import UserResponse
from .....security.permissions import require_any_role
from .....services.core.audit_service import AuditService

router = APIRouter(prefix="/audit", tags=["审计日志"])
_SYSTEM_MANAGEMENT_ROLE_CODES = ["admin", "system_admin", "perm_admin"]


def get_audit_service(
    db: AsyncSession = Depends(get_async_db),
) -> AuditService:
    """创建审计服务依赖。"""
    return AuditService(db)


@router.get("/logs", response_model=dict[str, Any], summary="获取审计日志统计")
async def get_audit_statistics(
    days: int = 30,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserResponse = Depends(
        require_any_role(_SYSTEM_MANAGEMENT_ROLE_CODES)
    ),
    audit_service: AuditService = Depends(get_audit_service),
    _authz_ctx: AuthzContext = Depends(
        require_authz(action="read", resource_type="operation_log")
    ),
) -> dict[str, Any]:
    """
    获取审计日志统计（仅管理员）

    **Party 隔离策略**：返回系统全局聚合统计数字（登录成功/失败次数、活跃用户数），
    非行级数据，不存在 party 级数据泄露风险。require_admin 门控，仅超管可见。
    若未来需要按主体分区统计，须在 AuditLog 模型中增加 party_id 列并修改查询。
    """

    return await audit_service.get_login_statistics(days=days)
