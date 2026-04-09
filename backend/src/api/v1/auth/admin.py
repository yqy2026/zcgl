from typing import Any

from fastapi import APIRouter, Depends

from ....core.exception_handler import internal_error
from ....database import create_tables, drop_tables
from ....middleware.auth import get_current_active_user
from ....security.permissions import require_any_role

"""
管理员API路由
"""

# 创建管理员路由器
router = APIRouter(
    prefix="/admin",
    tags=["系统管理"],
    dependencies=[Depends(get_current_active_user)],
)
_SYSTEM_ADMIN_ROLE_CODES = ["admin", "system_admin"]
require_system_admin = require_any_role(_SYSTEM_ADMIN_ROLE_CODES)


@router.get("/health")
def health_check() -> dict[str, str]:
    """
    健康检查
    """
    return {"status": "healthy"}  # pragma: no cover


@router.post("/database/reset")
async def reset_database(
    current_user: dict[str, Any] = Depends(require_system_admin),
) -> dict[str, Any]:
    """
    重置数据库（仅管理员）
    """
    try:  # pragma: no cover
        await drop_tables()  # pragma: no cover
        await create_tables()  # pragma: no cover
        return {"message": "数据库重置成功"}  # pragma: no cover
    except Exception as e:  # pragma: no cover
        raise internal_error(f"数据库重置失败: {str(e)}")  # pragma: no cover
