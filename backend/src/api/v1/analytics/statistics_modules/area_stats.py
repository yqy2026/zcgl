"""
面积统计模块

提供面积相关的统计端点:
- 面积汇总 (area-summary)
- 面积统计 (area-statistics)

Created: 2026-01-17 (Phase 2 - Large File Splitting)
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.params import Depends as DependsParam
from sqlalchemy.ext.asyncio import AsyncSession

from src.constants.cache_constants import CACHE_TTL_SHORT_SECONDS
from src.database import get_async_db
from src.middleware.auth import get_current_active_user
from src.models.auth import User
from src.schemas.statistics import AreaSummaryResponse
from src.services.analytics.area_stats_service import (
    AreaStatsService,
    get_area_stats_service,
)
from src.utils.cache_manager import cache_statistics

logger = logging.getLogger(__name__)

# 创建面积统计路由器
router = APIRouter()


def _resolve_service(service: AreaStatsService | Any) -> AreaStatsService | Any:
    if isinstance(service, DependsParam):
        return get_area_stats_service()
    return service


@cache_statistics(expire=CACHE_TTL_SHORT_SECONDS)  # 10分钟缓存
@router.get("/area-summary", response_model=AreaSummaryResponse)
async def get_area_summary(
    should_include_deleted: bool = False,
    should_use_aggregation: bool = True,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    service: AreaStatsService = Depends(get_area_stats_service),
) -> AreaSummaryResponse:
    """
    获取面积汇总统计
    使用数据库聚合查询计算总面积、可租面积、已租面积等。
    Args:
        include_deleted: 是否包含已删除的资产
        use_aggregation: 是否使用数据库聚合查询（推荐，性能更好）
        db: 数据库会话
    Returns:
        面积汇总统计信息
    """

    logger.info(f"开始计算面积汇总，聚合模式: {should_use_aggregation}")

    _ = current_user
    resolved_service = _resolve_service(service)
    result = await resolved_service.calculate_area_summary(
        db=db,
        should_include_deleted=should_include_deleted,
        should_use_aggregation=should_use_aggregation,
    )
    logger.info("面积汇总计算完成")
    return result


@router.get("/area-statistics", summary="获取面积统计")
async def get_area_statistics(
    ownership_status: str | None = Query(None, description="确权状态筛选"),
    property_nature: str | None = Query(None, description="物业性质筛选"),
    usage_status: str | None = Query(None, description="使用状态筛选"),
    should_include_deleted: bool = Query(False, description="是否包含已删除资产"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    service: AreaStatsService = Depends(get_area_stats_service),
) -> dict[str, Any]:
    """
    获取面积统计数据（支持多维度筛选）

    根据提供的筛选条件计算各类面积统计，包括：
    - 总土地面积
    - 总可租面积
    - 已出租面积
    - 未出租面积
    - 占用率
    Args:
        ownership_status: 确权状态筛选
        property_nature: 物业性质筛选
        usage_status: 使用状态筛选
        include_deleted: 是否包含已删除资产
    Returns:
        面积统计数据
    """
    _ = current_user
    resolved_service = _resolve_service(service)
    return await resolved_service.calculate_area_statistics(
        db=db,
        ownership_status=ownership_status,
        property_nature=property_nature,
        usage_status=usage_status,
        should_include_deleted=should_include_deleted,
    )
