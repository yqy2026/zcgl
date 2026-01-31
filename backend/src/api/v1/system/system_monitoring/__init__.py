"""
系统监控模块 - 路由聚合

将所有系统监控相关的子路由合并到一个主路由器。
使用惰性导入以避免测试环境缺失依赖时触发导入失败。
"""

import logging

from fastapi import APIRouter

logger = logging.getLogger(__name__)

# 创建主路由器
router = APIRouter(prefix="/monitoring", tags=["系统监控"])

# 惰性导入子路由，避免导入期依赖问题导致模块不可用
try:
    from . import database_endpoints, endpoints
except Exception as exc:  # pragma: no cover - defensive for missing deps
    logger.warning("系统监控路由未加载: %s", exc)
else:
    router.include_router(endpoints.router)
    router.include_router(database_endpoints.router)

__all__ = ["router"]
