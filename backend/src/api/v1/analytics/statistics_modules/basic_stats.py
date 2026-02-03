"""
基础统计模块

提供基础统计相关端点:
- 基础统计 (basic)
- 统计摘要 (summary)
- 看板数据 (dashboard)
- 综合统计 (comprehensive)
- 缓存管理 (cache/clear, cache/info)
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from src.constants.cache_constants import CACHE_TTL_SHORT_SECONDS
from src.crud.asset import asset_crud
from src.database import get_async_db
from src.middleware.auth import get_current_active_user
from src.models.auth import User
from src.schemas.statistics import (
    AreaSummaryResponse,
    BasicStatisticsResponse,
    CategoryOccupancyRateResponse,
    DashboardDataResponse,
    FinancialSummaryResponse,
    OccupancyRateStatsResponse,
)
from src.services.analytics import AreaService, FinancialService, OccupancyService
from src.utils.cache_manager import cache_statistics, get_cache_manager
from src.utils.numeric import to_float

logger = logging.getLogger(__name__)

router = APIRouter()


def _build_basic_filters(
    ownership_status: str | None,
    property_nature: str | None,
    usage_status: str | None,
    ownership_entity: str | None,
) -> dict[str, Any]:
    filters: dict[str, Any] = {}
    if ownership_status is not None:
        filters["ownership_status"] = ownership_status
    if property_nature is not None:
        filters["property_nature"] = property_nature
    if usage_status is not None:
        filters["usage_status"] = usage_status
    if ownership_entity is not None:
        filters["ownership_entity"] = ownership_entity
    return filters


def _calculate_basic_statistics(
    db: Session,
    ownership_status: str | None,
    property_nature: str | None,
    usage_status: str | None,
    ownership_entity: str | None,
) -> BasicStatisticsResponse:
    filters = _build_basic_filters(
        ownership_status,
        property_nature,
        usage_status,
        ownership_entity,
    )

    logger.info("开始获取基础统计数据，筛选条件: %s", filters)

    assets, _ = asset_crud.get_multi_with_search(
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

    ownership_stats = {"confirmed": 0, "unconfirmed": 0, "partial": 0}
    property_stats = {"commercial": 0, "non_commercial": 0}
    usage_stats = {"rented": 0, "self_used": 0, "vacant": 0}

    for asset in assets:
        if getattr(asset, "ownership_status", None) == "已确权":
            ownership_stats["confirmed"] += 1
        elif getattr(asset, "ownership_status", None) == "未确权":
            ownership_stats["unconfirmed"] += 1
        elif getattr(asset, "ownership_status", None) == "部分确权":
            ownership_stats["partial"] += 1

        if getattr(asset, "property_nature", None) == "经营性":
            property_stats["commercial"] += 1
        elif getattr(asset, "property_nature", None) == "非经营性":
            property_stats["non_commercial"] += 1

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


@router.get(
    "/basic", response_model=BasicStatisticsResponse, summary="获取基础统计数据"
)
async def get_basic_statistics(
    ownership_status: str | None = Query(None, description="确权状态筛选"),
    property_nature: str | None = Query(None, description="物业性质筛选"),
    usage_status: str | None = Query(None, description="使用状态筛选"),
    ownership_entity: str | None = Query(None, description="权属方筛选"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> BasicStatisticsResponse:
    return await db.run_sync(
        lambda sync_db: _calculate_basic_statistics(
            sync_db, ownership_status, property_nature, usage_status, ownership_entity
        )
    )


@router.get("/summary", response_model=BasicStatisticsResponse, summary="获取统计摘要")
async def get_statistics_summary(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> BasicStatisticsResponse:
    return await db.run_sync(
        lambda sync_db: _calculate_basic_statistics(sync_db, None, None, None, None)
    )


@cache_statistics(expire=CACHE_TTL_SHORT_SECONDS)
@router.get("/dashboard", response_model=DashboardDataResponse, summary="获取看板数据")
async def get_dashboard_data(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> DashboardDataResponse:
    def _sync(
        sync_db: Session,
    ) -> tuple[
        BasicStatisticsResponse,
        dict[str, Any],
        dict[str, Any],
        dict[str, Any],
        dict[str, Any],
        dict[str, Any],
    ]:
        basic_stats = _calculate_basic_statistics(sync_db, None, None, None, None)
        filters = basic_stats.filters_applied or {}

        area_service = AreaService(sync_db)
        area_summary_stats = area_service.calculate_summary_with_aggregation(filters)

        financial_service = FinancialService(sync_db)
        financial_summary_stats = financial_service.calculate_summary(filters)

        occupancy_service = OccupancyService(sync_db)
        occupancy_stats_data = occupancy_service.calculate_with_aggregation(filters)
        category_occupancy_stats = (
            occupancy_service.calculate_category_with_aggregation(
                "business_category", filters
            )
        )

        return (
            basic_stats,
            filters,
            area_summary_stats,
            financial_summary_stats,
            occupancy_stats_data,
            category_occupancy_stats,
        )

    (
        basic_stats,
        filters,
        area_summary_stats,
        financial_summary_stats,
        occupancy_stats_data,
        category_occupancy_stats,
    ) = await db.run_sync(_sync)

    area_summary = AreaSummaryResponse(
        total_area=area_summary_stats["total_land_area"],
        rentable_area=area_summary_stats["total_rentable_area"],
        rented_area=area_summary_stats["total_rented_area"],
        unrented_area=area_summary_stats["total_unrented_area"],
        occupancy_rate=area_summary_stats["overall_occupancy_rate"],
    )

    financial_summary = FinancialSummaryResponse(
        total_assets=financial_summary_stats["total_assets"],
        total_annual_income=financial_summary_stats["total_annual_income"],
        total_annual_expense=financial_summary_stats["total_annual_expense"],
        net_annual_income=financial_summary_stats["net_annual_income"],
        income_per_sqm=financial_summary_stats["income_per_sqm"],
        expense_per_sqm=financial_summary_stats["expense_per_sqm"],
    )

    occupancy_stats = OccupancyRateStatsResponse(
        overall_occupancy_rate=occupancy_stats_data["overall_rate"],
        total_rentable_area=occupancy_stats_data["total_rentable_area"],
        total_rented_area=occupancy_stats_data["total_rented_area"],
        calculated_at=datetime.now(),
    )

    category_occupancy = [
        CategoryOccupancyRateResponse(
            category=category_name,
            occupancy_rate=category_stats.get("overall_rate", 0.0),
            rentable_area=category_stats.get("total_rentable_area", 0.0),
            rented_area=category_stats.get("total_rented_area", 0.0),
            asset_count=category_stats.get("asset_count", 0),
        )
        for category_name, category_stats in category_occupancy_stats.items()
    ]

    return DashboardDataResponse(
        basic_stats=basic_stats,
        area_summary=area_summary,
        financial_summary=financial_summary,
        occupancy_stats=occupancy_stats,
        category_occupancy=category_occupancy,
        generated_at=datetime.now(),
        filters_applied=filters,
    )


@router.get("/comprehensive", summary="获取综合统计")
async def get_comprehensive_statistics(
    should_include_deleted: bool = Query(False, description="是否包含已删除资产"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    filters: dict[str, Any] = {}
    if not should_include_deleted:
        filters["data_status"] = "正常"

    assets, _ = await db.run_sync(
        lambda sync_db: asset_crud.get_multi_with_search(
            db=sync_db, skip=0, limit=10000, filters=filters
        )
    )

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
    cache_mgr = await get_cache_manager()
    cleared_count = await cache_mgr.clear_pattern("statistics:*")

    logger.info("清除统计数据缓存，清理 %s 条缓存", cleared_count)

    return {
        "success": True,
        "message": f"统计数据缓存已清除，共清除 {cleared_count} 个缓存条目",
        "data": {"cleared_count": cleared_count},
    }


@router.get("/cache/info", summary="获取缓存信息")
async def get_cache_info() -> dict[str, Any]:
    cache_mgr = await get_cache_manager()
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
