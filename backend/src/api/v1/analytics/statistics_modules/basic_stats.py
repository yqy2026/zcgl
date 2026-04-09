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
from fastapi.params import Depends as DependsParam
from sqlalchemy.ext.asyncio import AsyncSession

from src.constants.cache_constants import CACHE_TTL_SHORT_SECONDS
from src.database import get_async_db
from src.middleware.auth import (
    AuthzContext,
    DataScopeContext,
    get_current_active_user,
    require_authz,
    require_data_scope_context,
)
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
from src.services.analytics.basic_stats_service import (
    BasicStatsService,
    get_basic_stats_service,
)
from src.services.party_scope import build_party_filter_from_scope_context
from src.utils.cache_manager import cache_statistics, get_cache_manager

logger = logging.getLogger(__name__)

router = APIRouter()
_ANALYTICS_UPDATE_UNSCOPED_PARTY_ID = "__unscoped__:analytics:update"
_ANALYTICS_UPDATE_RESOURCE_CONTEXT: dict[str, str] = {
    "party_id": _ANALYTICS_UPDATE_UNSCOPED_PARTY_ID,
    "owner_party_id": _ANALYTICS_UPDATE_UNSCOPED_PARTY_ID,
    "manager_party_id": _ANALYTICS_UPDATE_UNSCOPED_PARTY_ID,
}


def _resolve_basic_stats_service(
    service: BasicStatsService | Any,
) -> BasicStatsService | Any:
    if isinstance(service, DependsParam):
        return get_basic_stats_service()
    return service


@router.get(
    "/basic", response_model=BasicStatisticsResponse, summary="获取基础统计数据"
)
async def get_basic_statistics(
    ownership_status: str | None = Query(None, description="确权状态筛选"),
    property_nature: str | None = Query(None, description="物业性质筛选"),
    usage_status: str | None = Query(None, description="使用状态筛选"),
    ownership_id: str | None = Query(None, description="权属方ID筛选"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    service: BasicStatsService = Depends(get_basic_stats_service),
    _scope_ctx: DataScopeContext = Depends(
        require_data_scope_context(resource_type="analytics")
    ),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="analytics",
        )
    ),
) -> BasicStatisticsResponse:
    _ = current_user
    resolved_service = _resolve_basic_stats_service(service)
    return await resolved_service.calculate_basic_statistics(
        db=db,
        ownership_status=ownership_status,
        property_nature=property_nature,
        usage_status=usage_status,
        ownership_id=ownership_id,
        party_filter=build_party_filter_from_scope_context(_scope_ctx),
    )


@router.get("/summary", response_model=BasicStatisticsResponse, summary="获取统计摘要")
async def get_statistics_summary(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    service: BasicStatsService = Depends(get_basic_stats_service),
    _scope_ctx: DataScopeContext = Depends(
        require_data_scope_context(resource_type="analytics")
    ),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="analytics",
        )
    ),
) -> BasicStatisticsResponse:
    _ = current_user
    resolved_service = _resolve_basic_stats_service(service)
    return await resolved_service.calculate_basic_statistics(
        db=db,
        ownership_status=None,
        property_nature=None,
        usage_status=None,
        ownership_id=None,
        party_filter=build_party_filter_from_scope_context(_scope_ctx),
    )


@cache_statistics(expire=CACHE_TTL_SHORT_SECONDS)
@router.get("/dashboard", response_model=DashboardDataResponse, summary="获取看板数据")
async def get_dashboard_data(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    service: BasicStatsService = Depends(get_basic_stats_service),
    _scope_ctx: DataScopeContext = Depends(
        require_data_scope_context(resource_type="analytics")
    ),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="analytics",
        )
    ),
) -> DashboardDataResponse:
    _ = current_user
    resolved_service = _resolve_basic_stats_service(service)
    basic_stats = await resolved_service.calculate_basic_statistics(
        db=db,
        ownership_status=None,
        property_nature=None,
        usage_status=None,
        ownership_id=None,
        party_filter=build_party_filter_from_scope_context(_scope_ctx),
    )
    filters = basic_stats.filters_applied or {}
    party_filter = build_party_filter_from_scope_context(_scope_ctx)

    area_service = AreaService(db)
    area_summary_stats = await area_service.calculate_summary_with_aggregation(
        filters,
        party_filter=party_filter,
    )

    financial_service = FinancialService(db)
    financial_summary_stats = await financial_service.calculate_summary(
        filters,
        party_filter=party_filter,
    )

    occupancy_service = OccupancyService(db)
    occupancy_stats_data = await occupancy_service.calculate_with_aggregation(
        filters,
        party_filter=party_filter,
    )
    category_occupancy_stats = (
        await occupancy_service.calculate_category_with_aggregation(
            "business_category",
            filters,
            party_filter=party_filter,
        )
    )

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
    service: BasicStatsService = Depends(get_basic_stats_service),
    _scope_ctx: DataScopeContext = Depends(
        require_data_scope_context(resource_type="analytics")
    ),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="analytics",
        )
    ),
) -> dict[str, Any]:
    _ = current_user
    resolved_service = _resolve_basic_stats_service(service)
    return await resolved_service.calculate_comprehensive_statistics(
        db=db,
        should_include_deleted=should_include_deleted,
        party_filter=build_party_filter_from_scope_context(_scope_ctx),
    )


@router.post("/cache/clear", summary="清除统计数据缓存")
async def clear_statistics_cache(
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="update",
            resource_type="analytics",
            resource_context=_ANALYTICS_UPDATE_RESOURCE_CONTEXT,
        )
    ),
) -> dict[str, Any]:
    cache_mgr = await get_cache_manager()
    cleared_count = await cache_mgr.clear_pattern("statistics:*")

    logger.info("清除统计数据缓存，清理 %s 条缓存", cleared_count)

    return {
        "success": True,
        "message": f"统计数据缓存已清除，共清除 {cleared_count} 个缓存条目",
        "data": {"cleared_count": cleared_count},
    }


@router.get("/cache/info", summary="获取缓存信息")
async def get_cache_info(
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="analytics",
        )
    ),
) -> dict[str, Any]:
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
