"""
统计分析API路由 - 主路由聚合器

本文件已完全重构为模块化架构：
- 所有业务逻辑已迁移到 statistics_modules/ 子模块
- 6个子模块包含所有17个端点的实现
- 本文件仅负责路由聚合，保持向后兼容

模块结构:
- distribution.py (4 endpoints): 分布统计
- occupancy_stats.py (3 endpoints): 占用率统计
- area_stats.py (2 endpoints): 面积统计
- financial_stats.py (1 endpoint): 财务统计
- trend_stats.py (1 endpoint): 趋势分析
- basic_stats.py (6 endpoints): 基础统计和缓存管理

重构完成日期: 2026-01-17
原始文件大小: 1,259 lines
重构后大小: ~60 lines (纯路由聚合器)
"""

import logging
from fastapi import APIRouter

# 配置日志
logger = logging.getLogger(__name__)

# 创建统计路由器
router = APIRouter(tags=["统计分析"])

# Phase 2 架构改进：集成模块化路由
# 所有 17 个端点已模块化到 6 个子模块：
# - distribution.py (4 endpoints): 分布统计
# - occupancy_stats.py (3 endpoints): 占用率统计
# - area_stats.py (2 endpoints): 面积统计
# - financial_stats.py (1 endpoint): 财务统计
# - trend_stats.py (1 endpoint): 趋势分析
# - basic_stats.py (6 endpoints): 基础统计和缓存管理
from .statistics_modules import (
    basic_stats_router,
    distribution_router,
    financial_stats_router,
    occupancy_stats_router,
    area_stats_router,
    trend_stats_router,
)

# 集成所有模块路由
# 注意：路由注册顺序决定了端点匹配优先级
# 更具体的路由应该先注册，更通用的路由后注册
router.include_router(basic_stats_router)
router.include_router(distribution_router)
router.include_router(occupancy_stats_router)
router.include_router(area_stats_router)
router.include_router(financial_stats_router)
router.include_router(trend_stats_router)

