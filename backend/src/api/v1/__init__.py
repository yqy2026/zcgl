"""
API v1版本路由
"""

from fastapi import APIRouter
from .assets import router as assets_router
from .excel import router as excel_router
from .history import router as history_router
from .statistics import router as statistics_router
from .occupancy import router as occupancy_router
from .backup import router as backup_router

# 创建API v1路由器
api_router = APIRouter(prefix="/api/v1")

# 包含各个模块的路由
api_router.include_router(
    assets_router,
    prefix="/assets",
    tags=["资产管理"]
)

api_router.include_router(
    excel_router,
    prefix="/excel",
    tags=["Excel导入导出"]
)

api_router.include_router(
    history_router,
    prefix="",
    tags=["变更历史"]
)

api_router.include_router(
    statistics_router,
    prefix="",
    tags=["数据统计和报表"]
)

api_router.include_router(
    occupancy_router,
    prefix="",
    tags=["出租率计算"]
)

api_router.include_router(
    backup_router,
    prefix="",
    tags=["数据备份和恢复"]
)

__all__ = ["api_router"]