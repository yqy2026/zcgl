"""
系统监控模块 - 路由聚合

将所有系统监控相关的子路由合并到一个主路由器
"""

from fastapi import APIRouter

from . import database_endpoints, endpoints

# 创建主路由器
router = APIRouter(prefix="/monitoring", tags=["系统监控"])

# 包含所有子路由
router.include_router(endpoints.router)
router.include_router(database_endpoints.router)

# 向后兼容导出
__all__ = ["router"]
