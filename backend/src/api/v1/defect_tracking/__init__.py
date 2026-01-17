"""
缺陷跟踪模块 - 路由聚合

将所有缺陷跟踪相关的子路由合并到一个主路由器
"""

from fastapi import APIRouter

from . import analysis, defects, prevention
from .database import init_defect_db

# 初始化数据库
init_defect_db()

# 创建主路由器
router = APIRouter(prefix="/defects", tags=["defect-tracking"])

# 包含所有子路由
router.include_router(defects.router)
router.include_router(analysis.router)
router.include_router(prevention.router)

# 向后兼容导出
__all__ = ["router"]
