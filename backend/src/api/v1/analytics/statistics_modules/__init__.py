"""
统计模块导出

导出所有子模块的路由器，用于在 statistics.py 中聚合
"""

from .area_stats import router as area_stats_router
from .basic_stats import router as basic_stats_router
from .distribution import router as distribution_router
from .financial_stats import router as financial_stats_router
from .occupancy_stats import router as occupancy_stats_router
from .trend_stats import router as trend_stats_router

__all__ = [
    "distribution_router",
    "occupancy_stats_router",
    "area_stats_router",
    "financial_stats_router",
    "trend_stats_router",
    "basic_stats_router",
]
