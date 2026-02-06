"""
审计日志API路由

包含: 审计日志统计
"""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from .....crud.auth import AuditLogCRUD
from .....database import get_async_db
from .....middleware.auth import require_admin
from .....schemas.auth import UserResponse

router = APIRouter(prefix="/audit", tags=["审计日志"])


@router.get("/logs", response_model=dict[str, Any], summary="获取审计日志统计")
async def get_audit_statistics(
    days: int = 30,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserResponse = Depends(require_admin),
) -> dict[str, Any]:
    """
    获取审计日志统计（仅管理员）
    """

    audit_crud = AuditLogCRUD()
    return await audit_crud.get_login_statistics_async(db, days)
