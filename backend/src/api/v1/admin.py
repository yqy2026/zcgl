from typing import Any
"""
管理员API路由
"""

from fastapi import APIRouter, Depends, HTTPException

from ...database import create_tables, drop_tables
from ...middleware.auth import require_admin

# 创建管理员路由器
router = APIRouter(prefix="/admin", tags=["系统管理"])


@router.get("/health")
async def health_check():
    """
    健康检查
    """
    return {"status": "healthy"}


@router.post("/database/reset")
async def reset_database(current_user: dict[str, Any] = Depends(require_admin)):
    """
    重置数据库（仅管理员）
    """
    try:
        drop_tables()
        create_tables()
        return {"message": "数据库重置成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据库重置失败: {str(e)}")
