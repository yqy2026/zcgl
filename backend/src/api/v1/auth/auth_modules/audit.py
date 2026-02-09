"""
审计日志API路由

包含: 审计日志统计
"""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from .....database import get_async_db
from .....middleware.auth import require_admin
from .....schemas.auth import UserResponse
from .....services.core.audit_service import AuditService

router = APIRouter(prefix="/audit", tags=["审计日志"])


def get_audit_service(
    db: AsyncSession = Depends(get_async_db),
) -> AuditService:
    """创建审计服务依赖。"""
    return AuditService(db)


@router.get("/logs", response_model=dict[str, Any], summary="获取审计日志统计")
async def get_audit_statistics(
    days: int = 30,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserResponse = Depends(require_admin),
    audit_service: AuditService = Depends(get_audit_service),
) -> dict[str, Any]:
    """
    获取审计日志统计（仅管理员）
    """

    return await audit_service.get_login_statistics(days=days)
