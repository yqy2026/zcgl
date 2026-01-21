"""
基础统计模块

提供基础统计相关的端点:
- 基础统计 (basic)
- 统计摘要 (summary)
- 仪表板数据 (dashboard)
- 综合统计 (comprehensive)
- 缓存管理 (cache/clear, cache/info)

Created: 2026-01-17 (Phase 2 - Large File Splitting)
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ....crud.asset import asset_crud
from ....database import get_db
from ....middleware.auth import get_current_active_user
from ....models.auth import User
from ....schemas.statistics import (
    BasicStatisticsResponse,
    ChartDataItem,
    DashboardDataResponse,
)
from ....utils.cache_manager import cache_statistics, get_cache_manager
from ....utils.numeric import to_float

logger = logging.getLogger(__name__)

# 创建基础统计路由器
router = APIRouter()


@router.get(
    "/basic", response_model=BasicStatisticsResponse, summary="获取基础统计数据"
)
async def get_basic_statistics(
    ownership_status: str | None = Query(None, description="确权状态筛选"),
    property_nature: str | None = Query(None, description="物业性质筛选"),
    usage_status: str | None = Query(None, description="使用状态筛选"),
    ownership_entity: str | None = Query(None, description="权属方筛选"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> BasicStatisticsResponse:
    """
    获取基础统计数据

    支持多维度筛选的基础统计，包括资产总数和各类分布。

    Args:
        ownership_status: 确权状态筛选
        property_nature: 物业性质筛选
        usage_status: 使用状态筛选
        ownership_entity: 权属方筛选
        db: 数据库会话

    Returns:
        基础统计数据
    """
    # 构建筛选条件
    filters: dict[str, Any] = {}
    if ownership_status is not None:
        filters["ownership_status"] = ownership_status
    if property_nature is not None:
        filters["property_nature"] = property_nature
    if usage_status is not None:
        filters["usage_status"] = usage_status
    if ownership_entity is not None:
        filters["ownership_entity"] = ownership_entity

    logger.info(f"开始获取基础统计数据，筛选条件: {filters}")

    # 获取总资产数
    assets, total_count = asset_crud.get_multi_with_search(
        db=db, skip=0, limit=10000, filters=filters
    )
    total_assets = len(assets)

    if total_assets == 0:
        return BasicStatisticsResponse(
            total_assets=0,
            ownership_status={"confirmed": 0, "unconfirmed": 0, "partial": 0},
            property_nature={"commercial": 0, "non_commercial": 0},
            usage_status={"rented": 0, "self_used": 0, "vacant": 0},
            generated_at=datetime.now(),
            filters_applied=filters,
        )

    # 按确权状态统计
    ownership_stats = {"confirmed": 0, "unconfirmed": 0, "partial": 0}
    property_stats = {"commercial": 0, "non_commercial": 0}
    usage_stats = {"rented": 0, "self_used": 0, "vacant": 0}

    for asset in assets:
        # 统计确权状态
        if getattr(asset, "ownership_status", None) == "已确权":
            ownership_stats["confirmed"] += 1
        elif getattr(asset, "ownership_status", None) == "未确权":
            ownership_stats["unconfirmed"] += 1
        elif getattr(asset, "ownership_status", None) == "部分确权":
            ownership_stats["partial"] += 1

        # 统计物业性质
        if getattr(asset, "property_nature", None) == "经营性":
            property_stats["commercial"] += 1
        elif getattr(asset, "property_nature", None) == "非经营性":
            property_stats["non_commercial"] += 1

        # 统计使用状态
        if getattr(asset, "usage_status", None) == "出租":
            usage_stats["rented"] += 1
        elif getattr(asset, "usage_status", None) == "自用":
            usage_stats["self_used"] += 1
        elif getattr(asset, "usage_status", None) == "空置":
            usage_stats["vacant"] += 1

    return BasicStatisticsResponse(
        total_assets=total_assets,
        ownership_status=ownership_stats,
        property_nature=property_stats,
        usage_status=usage_stats,
        generated_at=datetime.now(),
        filters_applied=filters,
    )


@router.get("/summary", response_model=BasicStatisticsResponse, summary="获取统计摘要")
async def get_statistics_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> BasicStatisticsResponse:
    """
    获取统计摘要（无筛选条件）

    快速获取所有资产的统计概览。

    Returns:
        统计摘要数据
    """
    return await get_basic_statistics(
        ownership_status=None,
        property_nature=None,
        usage_status=None,
        ownership_entity=None,
        db=db,
        current_user=current_user,
    )


@cache_statistics(expire=600)  # 10分钟缓存  # type: ignore[misc]
@router.get(
    "/dashboard", response_model=DashboardDataResponse, summary="获取仪表板数据"
)
async def get_dashboard_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> DashboardDataResponse:
    """
    获取仪表板综合数据

    汇总所有关键统计指标，用于仪表板显示。

    Returns:
        仪表板综合数据
    """
    # 获取基础统计
    assets, _ = asset_crud.get_multi_with_search(db=db, skip=0, limit=10000)
    total_assets = len(assets)

    # 计算占用率（暂时未使用，endpoint需要重构）
    total_rentable_area = 0.0
    total_rented_area = 0.0

    for asset in assets:
        if getattr(asset, "rentable_area", None):
            total_rentable_area += to_float(getattr(asset, "rentable_area"))
        if getattr(asset, "rented_area", None):
            total_rented_area += to_float(getattr(asset, "rented_area"))

    # 按确权状态分布
    ownership_distribution = [
        ChartDataItem(
            name="已确权",
            value=sum(
                1 for a in assets if getattr(a, "ownership_status", None) == "已确权"
            ),
            percentage=0.0,  # 计算在下面
        ),
        ChartDataItem(
            name="未确权",
            value=sum(
                1 for a in assets if getattr(a, "ownership_status", None) == "未确权"
            ),
            percentage=0.0,
        ),
        ChartDataItem(
            name="部分确权",
            value=sum(
                1 for a in assets if getattr(a, "ownership_status", None) == "部分确权"
            ),
            percentage=0.0,
        ),
    ]

    # 计算百分比
    for item in ownership_distribution:
        item.percentage = (item.value / total_assets * 100) if total_assets > 0 else 0.0

    # TODO: 实现财务汇总和出租率统计
    # 这需要从其他服务获取数据
    # 注意：BasicStatisticsResponse的schema与原有实现不匹配
    # 需要重构整个endpoint以匹配正确的schema
    from ....core.exception_handler import service_unavailable

    raise service_unavailable(
        "仪表板数据的财务汇总和详细出租率统计尚未实现，需要重构schema"
    )
    # 临时返回不完整数据 - 最终需要实现完整的仪表板数据聚合
    # return DashboardDataResponse(
    #     basic_stats=basic_stats_data,
    #     area_summary=area_summary_data,
    #     financial_summary=...,  # 需要实现
    #     occupancy_stats=...,  # 需要实现
    #     category_occupancy=[],
    #     generated_at=datetime.now(),
    # )


@router.get("/comprehensive", summary="获取综合统计")
async def get_comprehensive_statistics(
    include_deleted: bool = Query(False, description="是否包含已删除资产"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    """
    获取综合统计数据

    包含所有维度的统计信息，用于全面的数据分析。

    Args:
        include_deleted: 是否包含已删除的资产

    Returns:
        综合统计数据
    """
    # 构建筛选条件
    filters: dict[str, Any] = {}
    if not include_deleted:
        filters["data_status"] = "正常"

    # 获取资产数据
    assets, _ = asset_crud.get_multi_with_search(
        db=db, skip=0, limit=10000, filters=filters
    )

    # 计算各类统计
    total_assets = len(assets)
    total_land_area = sum(
        to_float(getattr(a, "land_area"))
        for a in assets
        if getattr(a, "land_area", None)
    )
    total_rentable_area = sum(
        to_float(getattr(a, "rentable_area"))
        for a in assets
        if getattr(a, "rentable_area", None)
    )
    total_rented_area = sum(
        to_float(getattr(a, "rented_area"))
        for a in assets
        if getattr(a, "rented_area", None)
    )

    occupancy_rate = (
        (total_rented_area / total_rentable_area * 100)
        if total_rentable_area > 0
        else 0.0
    )

    comprehensive_data = {
        "total_assets": total_assets,
        "total_land_area": round(total_land_area, 2),
        "total_rentable_area": round(total_rentable_area, 2),
        "total_rented_area": round(total_rented_area, 2),
        "occupancy_rate": round(occupancy_rate, 2),
        "generated_at": datetime.now().isoformat(),
        "filters_applied": filters,
    }

    return {
        "success": True,
        "data": comprehensive_data,
        "message": "综合统计数据获取成功",
    }


@router.post("/cache/clear", summary="清除统计数据缓存")
async def clear_statistics_cache() -> dict[str, Any]:
    """
    清除统计数据缓存

    清除所有统计相关的缓存条目。

    Returns:
        清除结果
    """
    cache_mgr = await get_cache_manager()
    cleared_count = await cache_mgr.clear_pattern("statistics:*")

    logger.info(f"用户请求清除统计数据缓存，清除了 {cleared_count} 个缓存条目")

    return {
        "success": True,
        "message": f"统计数据缓存已清除，共清除 {cleared_count} 个缓存条目",
        "data": {"cleared_count": cleared_count},
    }


@router.get("/cache/info", summary="获取缓存信息")
async def get_cache_info() -> dict[str, Any]:
    """
    获取缓存信息

    返回统计缓存的使用情况。

    Returns:
        缓存信息
    """
    cache_mgr = await get_cache_manager()
    # CacheManager 不支持列出所有键，这是 Redis 特有的功能
    # 返回缓存管理器信息作为替代
    backend_type = (
        cache_mgr.backend.__class__.__name__
        if hasattr(cache_mgr, "backend")
        else "Unknown"
    )
    backend_info = {
        "backend_type": backend_type,
        "namespace": "statistics",
    }

    return {
        "success": True,
        "message": "统计缓存正在使用",
        "data": {
            "cache_backend": backend_info,
            "note": "当前缓存后端不支持列出所有缓存键",
        },
    }
