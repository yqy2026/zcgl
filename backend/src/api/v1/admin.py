from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from ...database import create_tables, drop_tables
from ...middleware.auth import require_admin

"""
管理员API路由
"""

# 创建管理员路由器
router = APIRouter(prefix="/admin", tags=["系统管理"])


@router.get("/health")
async def health_check():
    """
    健康检查
    """
    return {"status": "healthy"}  # pragma: no cover


@router.post("/database/reset")
async def reset_database(current_user: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    """
    重置数据库（仅管理员）
    """
    try:  # pragma: no cover
        drop_tables()  # type: ignore[no-untyped-call]  # pragma: no cover
        create_tables()  # type: ignore[no-untyped-call]  # pragma: no cover
        return {"message": "数据库重置成功"}  # pragma: no cover
    except Exception as e:  # pragma: no cover
        raise HTTPException(
            status_code=500, detail=f"数据库重置失败: {str(e)}"
        )  # pragma: no cover
