"""
统计分析API路由
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from ...crud.asset import asset_crud
from ...database import get_db
from ...middleware.auth import get_current_active_user
from ...models.auth import User
from ...schemas.statistics import (
    AreaSummaryResponse,
    BasicStatisticsResponse,
    CategoryOccupancyRateListResponse,
    CategoryOccupancyRateResponse,
    ChartDataItem,
    DashboardDataResponse,
    DistributionResponse,
    FinancialSummaryResponse,
    OccupancyRateStatsResponse,
    TrendDataResponse,
)
from ...services.analytics import AreaService, OccupancyService
from ...utils.cache_manager import cache_statistics, get_cache_manager
from ...utils.numeric import to_float

# 配置日志
logger = logging.getLogger(__name__)

# 创建统计路由器
router = APIRouter(tags=["统计分析"])

# Phase 2 架构改进：集成模块化路由
# 分布统计端点已迁移到 statistics_modules/distribution.py
# 占用率统计端点已迁移到 statistics_modules/occupancy_stats.py
from .statistics_modules import distribution_router, occupancy_stats_router

# 集成模块路由
router.include_router(distribution_router)
router.include_router(occupancy_stats_router)


# 私有函数已迁移到 Service 层:
# - _calculate_occupancy_with_aggregation -> OccupancyService.calculate_with_aggregation
# - _calculate_occupancy_in_memory -> OccupancyService._calculate_in_memory
# - _calculate_category_occupancy_with_aggregation -> OccupancyService.calculate_category_with_aggregation
# - _calculate_category_occupancy_in_memory -> OccupancyService._calculate_category_in_memory
# - _calculate_area_summary_with_aggregation -> AreaService.calculate_summary_with_aggregation
# - _calculate_area_summary_in_memory -> AreaService._calculate_summary_in_memory


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
    assets, _ = asset_crud.get_multi_with_search(
        db=db, skip=0, limit=1, filters=filters
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
    confirmed_assets, _ = asset_crud.get_multi_with_search(
        db=db,
        skip=0,
        limit=10000,
        filters={**filters, "ownership_status": "已确权"},
    )
    confirmed_count = len(confirmed_assets)

    unconfirmed_assets, _ = asset_crud.get_multi_with_search(
        db=db,
        skip=0,
        limit=10000,
        filters={**filters, "ownership_status": "未确权"},
    )
    unconfirmed_count = len(unconfirmed_assets)

    partial_assets, _ = asset_crud.get_multi_with_search(
        db=db,
        skip=0,
        limit=10000,
        filters={**filters, "ownership_status": "部分确权"},
    )
    partial_count = len(partial_assets)

    # 按物业性质统计
    commercial_assets, _ = asset_crud.get_multi_with_search(
        db=db, skip=0, limit=10000, filters={**filters, "property_nature": "经营性"}
    )
    commercial_count = len(commercial_assets)

    non_commercial_assets, _ = asset_crud.get_multi_with_search(
        db=db,
        skip=0,
        limit=10000,
        filters={**filters, "property_nature": "非经营性"},
    )
    non_commercial_count = len(non_commercial_assets)

    # 按使用状态统计
    rented_assets, _ = asset_crud.get_multi_with_search(
        db=db, skip=0, limit=10000, filters={**filters, "usage_status": "出租"}
    )
    rented_count = len(rented_assets)

    self_used_assets, _ = asset_crud.get_multi_with_search(
        db=db, skip=0, limit=10000, filters={**filters, "usage_status": "自用"}
    )
    self_used_count = len(self_used_assets)

    vacant_assets, _ = asset_crud.get_multi_with_search(
        db=db, skip=0, limit=10000, filters={**filters, "usage_status": "空置"}
    )
    vacant_count = len(vacant_assets)

    # 构建统计数据
    _basic_stats = {
        "total_assets": total_assets,
        "ownership_status": {
            "confirmed": confirmed_count,
            "unconfirmed": unconfirmed_count,
            "partial": partial_count,
        },
        "property_nature": {
            "commercial": commercial_count,
            "non_commercial": non_commercial_count,
        },
        "usage_status": {
            "rented": rented_count,
            "self_used": self_used_count,
            "vacant": vacant_count,
        },
        "generated_at": datetime.now().isoformat(),
        "filters_applied": filters,
    }

    logger.info(f"基础统计数据获取完成，包含 {total_assets} 条资产")

    return BasicStatisticsResponse(
        total_assets=total_assets,
        ownership_status={
            "confirmed": confirmed_count,
            "unconfirmed": unconfirmed_count,
            "partial": partial_count,
        },
        property_nature={
            "commercial": commercial_count,
            "non_commercial": non_commercial_count,
        },
        usage_status={
            "rented": rented_count,
            "self_used": self_used_count,
            "vacant": vacant_count,
        },
        generated_at=datetime.now(),
        filters_applied=filters,
    )


# 仪表板端点已移除，请使用以下替代端点：
# - /api/v1/statistics/basic - 基础统计
# - /api/v1/statistics/summary - 统计摘要
# - /api/v1/statistics/area-summary - 面积汇总
# - /api/v1/statistics/financial-summary - 财务汇总


# @cache_statistics(expire=1800)  # 30分钟缓存 - 临时禁用
@router.get("/summary", response_model=BasicStatisticsResponse, summary="获取统计摘要")
async def get_statistics_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> BasicStatisticsResponse:
    """
    获取统计摘要信息
    """
    # DEBUG: 添加调试日志
    logger.debug("statistics.py get_statistics_summary called")

    # 总资产数
    assets_list: list[Any] = asset_crud.get_multi(db=db, skip=0, limit=1)
    total_assets = len(assets_list)

    # 按确权状态统计
    confirmed_assets, _ = asset_crud.get_multi_with_search(
        db=db, skip=0, limit=10000, filters={"ownership_status": "已确权"}
    )
    confirmed_count = len(confirmed_assets)

    unconfirmed_assets, _ = asset_crud.get_multi_with_search(
        db=db, skip=0, limit=10000, filters={"ownership_status": "未确权"}
    )
    unconfirmed_count = len(unconfirmed_assets)

    partial_assets, _ = asset_crud.get_multi_with_search(
        db=db, skip=0, limit=10000, filters={"ownership_status": "部分确权"}
    )
    partial_count = len(partial_assets)

    # 按物业性质统计
    commercial_assets, _ = asset_crud.get_multi_with_search(
        db=db, skip=0, limit=10000, filters={"property_nature": "经营性"}
    )
    commercial_count = len(commercial_assets)

    non_commercial_assets, _ = asset_crud.get_multi_with_search(
        db=db, skip=0, limit=10000, filters={"property_nature": "非经营性"}
    )
    non_commercial_count = len(non_commercial_assets)

    # 按使用状态统计
    rented_assets, _ = asset_crud.get_multi_with_search(
        db=db, skip=0, limit=10000, filters={"usage_status": "出租"}
    )
    rented_count = len(rented_assets)

    self_used_assets, _ = asset_crud.get_multi_with_search(
        db=db, skip=0, limit=10000, filters={"usage_status": "自用"}
    )
    self_used_count = len(self_used_assets)

    vacant_assets, _ = asset_crud.get_multi_with_search(
        db=db, skip=0, limit=10000, filters={"usage_status": "空置"}
    )
    vacant_count = len(vacant_assets)

    return BasicStatisticsResponse(
        total_assets=total_assets,
        ownership_status={
            "confirmed": confirmed_count,
            "unconfirmed": unconfirmed_count,
            "partial": partial_count,
        },
        property_nature={
            "commercial": commercial_count,
            "non_commercial": non_commercial_count,
        },
        usage_status={
            "rented": rented_count,
            "self_used": self_used_count,
            "vacant": vacant_count,
        },
        generated_at=datetime.now(),
        filters_applied={},
    )


@cache_statistics(expire=600)  # 10分钟缓存  # type: ignore[misc]  # type: ignore[misc]
@router.get("/occupancy-rate/overall", response_model=OccupancyRateStatsResponse)
def get_overall_occupancy_rate(
    include_deleted: bool = False,
    use_aggregation: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> OccupancyRateStatsResponse:
    """
    获取整体出租率统计

    Args:
        include_deleted: 是否包含已删除的资产
        use_aggregation: 是否使用数据库聚合查询（推荐，性能更好）
        db: 数据库会话

    Returns:
        整体出租率统计信息
    """
    logger.info(
        f"开始计算整体出租率，包含已删除: {include_deleted}, 使用聚合: {use_aggregation}"
    )

    # 构建筛选条件
    filters: dict[str, Any] = {}
    if not include_deleted:
        filters["data_status"] = "正常"

    # 使用新的Service层
    service = OccupancyService(db)
    stats = service.calculate_with_aggregation(filters)

    logger.info(f"出租率计算完成: {stats}")

    return OccupancyRateStatsResponse(
        overall_occupancy_rate=stats["overall_rate"],
        total_rentable_area=stats["total_rentable_area"],
        total_rented_area=stats["total_rented_area"],
        calculated_at=datetime.now(),
    )


@cache_statistics(expire=600)  # 10分钟缓存  # type: ignore[misc]  # type: ignore[misc]
@router.get(
    "/occupancy-rate/by-category", response_model=CategoryOccupancyRateListResponse
)
def get_occupancy_rate_by_category(
    category_field: str = "business_category",
    include_deleted: bool = False,
    use_aggregation: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CategoryOccupancyRateListResponse:
    """
    按类别获取出租率统计

    Args:
        category_field: 分类字段名
        include_deleted: 是否包含已删除的资产
        use_aggregation: 是否使用数据库聚合查询（推荐，性能更好）
        db: 数据库会话

    Returns:
        按类别的出租率统计信息
    """
    # 验证分类字段
    valid_fields = [
        "business_category",
        "property_nature",
        "usage_status",
        "ownership_status",
        "manager_name",
        "business_model",
        "operation_status",
        "project_name",
    ]

    if category_field not in valid_fields:
        raise HTTPException(
            status_code=400,
            detail=f"无效的分类字段。支持的字段: {', '.join(valid_fields)}",
        )

    logger.info(
        f"开始计算分类出租率，字段: {category_field}, 聚合模式: {use_aggregation}"
    )

    # 构建筛选条件
    filters: dict[str, Any] = {}
    if not include_deleted:
        filters["data_status"] = "正常"

    # 使用新的Service层
    service = OccupancyService(db)
    stats = service.calculate_category_with_aggregation(category_field, filters)

    logger.info(f"分类出租率计算完成: {category_field}, 共{len(stats)}个分类")

    # Transform stats dict to list of CategoryOccupancyRateResponse
    category_items = []
    for category_name, category_stats in stats.items():
        category_items.append(
            CategoryOccupancyRateResponse(
                category=category_name,
                occupancy_rate=category_stats.get("overall_rate", 0.0),
                rentable_area=category_stats.get("total_rentable_area", 0.0),
                rented_area=category_stats.get("total_rented_area", 0.0),
                asset_count=category_stats.get("asset_count", 0),
            )
        )

    return CategoryOccupancyRateListResponse(
        category_field=category_field,
        categories=category_items,
        generated_at=datetime.now(),
    )


@cache_statistics(expire=600)  # 10分钟缓存  # type: ignore[misc]  # type: ignore[misc]
@router.get("/area-summary", response_model=AreaSummaryResponse)
def get_area_summary(
    include_deleted: bool = False,
    use_aggregation: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> AreaSummaryResponse:
    """
    获取面积汇总统计

    Args:
        include_deleted: 是否包含已删除的资产
        use_aggregation: 是否使用数据库聚合查询（推荐，性能更好）
        db: 数据库会话

    Returns:
        面积汇总统计信息
    """
    logger.info(f"开始计算面积汇总，聚合模式: {use_aggregation}")

    # 构建筛选条件
    filters: dict[str, Any] = {}
    if not include_deleted:
        filters["data_status"] = "正常"

    # 使用新的Service层
    service = AreaService(db)
    summary = service.calculate_summary_with_aggregation(filters)

    logger.info(f"面积汇总计算完成: {summary}")

    return AreaSummaryResponse(
        total_area=summary["total_land_area"],
        rentable_area=summary["total_rentable_area"],
        rented_area=summary["total_rented_area"],
        unrented_area=summary["total_unrented_area"],
        occupancy_rate=summary["overall_occupancy_rate"],
    )


@cache_statistics(expire=1800)  # 30分钟缓存  # type: ignore[misc]  # type: ignore[misc]
@router.get("/financial-summary", response_model=FinancialSummaryResponse)
def get_financial_summary(
    include_deleted: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FinancialSummaryResponse:
    """
    获取财务汇总统计

    Args:
        include_deleted: 是否包含已删除的资产
        db: 数据库会话

    Returns:
        财务汇总统计信息
    """
    # 获取所有资产
    filters: dict[str, Any] = {}
    if not include_deleted:
        filters["data_status"] = "正常"

    assets, _ = asset_crud.get_multi_with_search(
        db=db,
        skip=0,
        limit=10000,  # 获取所有资产
        filters=filters,
    )

    # 计算财务汇总
    summary = {
        "total_assets": len(assets),
        "total_annual_income": 0.0,
        "total_annual_expense": 0.0,
        "total_net_income": 0.0,
        "total_monthly_rent": 0.0,
        "total_deposit": 0.0,
        "total_rentable_area": 0.0,
        "assets_with_income_data": 0,
        "assets_with_rent_data": 0,
    }

    for asset in assets:
        # 累计可出租面积
        if getattr(asset, "rentable_area", None):
            summary["total_rentable_area"] += to_float(getattr(asset, "rentable_area"))

        if getattr(asset, "annual_income", None):
            summary["total_annual_income"] += to_float(getattr(asset, "annual_income"))
            summary["assets_with_income_data"] += 1

        if getattr(asset, "annual_expense", None):
            summary["total_annual_expense"] += to_float(
                getattr(asset, "annual_expense")
            )

        if getattr(asset, "net_income", None):
            summary["total_net_income"] += to_float(getattr(asset, "net_income"))

        if getattr(asset, "monthly_rent", None):
            summary["total_monthly_rent"] += to_float(getattr(asset, "monthly_rent"))
            summary["assets_with_rent_data"] += 1

        if getattr(asset, "deposit", None):
            summary["total_deposit"] += to_float(getattr(asset, "deposit"))

    # 格式化数据，保留2位小数
    for key in [
        "total_annual_income",
        "total_annual_expense",
        "total_net_income",
        "total_monthly_rent",
        "total_deposit",
        "total_rentable_area",
    ]:
        if summary[key] is not None:
            summary[key] = round(summary[key], 2)
        else:
            summary[key] = 0.0

    # 计算每平方米收入和支出
    total_rentable_area = summary.get("total_rentable_area", 0)
    income_per_sqm = (
        summary["total_annual_income"] / total_rentable_area
        if total_rentable_area > 0
        else 0.0
    )
    expense_per_sqm = (
        summary["total_annual_expense"] / total_rentable_area
        if total_rentable_area > 0
        else 0.0
    )

    return FinancialSummaryResponse(
        total_assets=int(summary["total_assets"]),
        total_annual_income=summary["total_annual_income"],
        total_annual_expense=summary["total_annual_expense"],
        net_annual_income=summary["total_net_income"],
        income_per_sqm=round(income_per_sqm, 2),
        expense_per_sqm=round(expense_per_sqm, 2),
    )


@router.post("/cache/clear", summary="清除统计数据缓存")
async def clear_statistics_cache() -> dict[str, Any]:
    """
    清除统计数据缓存
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
    """
    cache_mgr = await get_cache_manager()

    # 简单的缓存状态检查
    cache_status = {
        "cache_type": "Redis" if cache_mgr.redis_client else "In-Memory",
        "cache_enabled": cache_mgr.redis_client is not None,
        "description": "统计数据使用Redis缓存，TTL为30分钟",
    }

    return {"success": True, "message": "获取缓存信息成功", "data": cache_status}


@cache_statistics(expire=600)  # 10分钟缓存  # type: ignore[misc]  # type: ignore[misc]
@router.get(
    "/dashboard", response_model=DashboardDataResponse, summary="获取仪表板数据"
)
async def get_dashboard_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> DashboardDataResponse:
    """
    获取仪表板综合数据
    """
    # 获取基础统计
    assets: list[Any] = asset_crud.get_multi(db=db, skip=0, limit=1)
    total_assets = len(assets)

    # 计算各类统计
    # 按确权状态统计
    confirmed_assets, _ = asset_crud.get_multi_with_search(
        db=db, skip=0, limit=10000, filters={"ownership_status": "已确权"}
    )
    confirmed_count = len(confirmed_assets)

    unconfirmed_assets, _ = asset_crud.get_multi_with_search(
        db=db, skip=0, limit=10000, filters={"ownership_status": "未确权"}
    )
    unconfirmed_count = len(unconfirmed_assets)

    partial_assets, _ = asset_crud.get_multi_with_search(
        db=db, skip=0, limit=10000, filters={"ownership_status": "部分确权"}
    )
    partial_count = len(partial_assets)

    # 按物业性质统计
    commercial_assets, _ = asset_crud.get_multi_with_search(
        db=db, skip=0, limit=10000, filters={"property_nature": "经营性"}
    )
    commercial_count = len(commercial_assets)

    non_commercial_assets, _ = asset_crud.get_multi_with_search(
        db=db, skip=0, limit=10000, filters={"property_nature": "非经营性"}
    )
    non_commercial_count = len(non_commercial_assets)

    # 按使用状态统计
    rented_assets, _ = asset_crud.get_multi_with_search(
        db=db, skip=0, limit=10000, filters={"usage_status": "出租"}
    )
    rented_count = len(rented_assets)

    vacant_assets, _ = asset_crud.get_multi_with_search(
        db=db, skip=0, limit=10000, filters={"usage_status": "空置"}
    )
    vacant_count = len(vacant_assets)

    self_used_assets, _ = asset_crud.get_multi_with_search(
        db=db, skip=0, limit=10000, filters={"usage_status": "自用"}
    )
    self_used_count = len(self_used_assets)

    # 获取面积和财务数据
    assets, _ = asset_crud.get_multi_with_search(db=db, skip=0, limit=10000)

    total_area = 0.0
    total_income = 0.0
    total_expense = 0.0
    total_rentable_area = 0.0
    total_rented_area = 0.0

    for asset in assets:
        if getattr(asset, "land_area", None):
            total_area += to_float(getattr(asset, "land_area"))
        if getattr(asset, "annual_income", None):
            total_income += to_float(getattr(asset, "annual_income"))
        if getattr(asset, "annual_expense", None):
            total_expense += to_float(getattr(asset, "annual_expense"))
        if getattr(asset, "rentable_area", None):
            total_rentable_area += to_float(getattr(asset, "rentable_area"))
        if getattr(asset, "rented_area", None):
            total_rented_area += to_float(getattr(asset, "rented_area"))

    net_income = total_income - total_expense
    occupancy_rate = (
        (total_rented_area / total_rentable_area * 100)
        if total_rentable_area > 0
        else 0.0
    )

    return DashboardDataResponse(
        basic_stats=BasicStatisticsResponse(
            total_assets=total_assets,
            ownership_status={
                "confirmed": confirmed_count,
                "unconfirmed": unconfirmed_count,
                "partial": partial_count,
            },
            property_nature={
                "commercial": commercial_count,
                "non_commercial": non_commercial_count,
            },
            usage_status={
                "rented": rented_count,
                "self_used": self_used_count,
                "vacant": vacant_count,
            },
            generated_at=datetime.now(),
            filters_applied={},
        ),
        area_summary=AreaSummaryResponse(
            total_area=round(total_area, 2),
            rentable_area=round(total_rentable_area, 2),
            rented_area=round(total_rented_area, 2),
            unrented_area=round(total_rentable_area - total_rented_area, 2)
            if total_rentable_area > total_rented_area
            else 0.0,
            occupancy_rate=round(occupancy_rate, 2),
        ),
        financial_summary=FinancialSummaryResponse(
            total_assets=total_assets,
            total_annual_income=round(total_income, 2),
            total_annual_expense=round(total_expense, 2),
            net_annual_income=round(net_income, 2),
            income_per_sqm=round(total_income / total_area, 2)
            if total_area > 0
            else 0.0,
            expense_per_sqm=round(total_expense / total_area, 2)
            if total_area > 0
            else 0.0,
        ),
        occupancy_stats=OccupancyRateStatsResponse(
            overall_occupancy_rate=round(occupancy_rate, 2),
            total_rentable_area=round(total_rentable_area, 2),
            total_rented_area=round(total_rented_area, 2),
            calculated_at=datetime.now(),
        ),
        category_occupancy=[],
        generated_at=datetime.now(),
        filters_applied={},
    )


@router.get(
    "/ownership-distribution",
    response_model=DistributionResponse,
    summary="获取权属分布统计",
)
async def get_ownership_distribution(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> DistributionResponse:
    """
    获取按权属状态的资产分布统计
    """
    assets: list[Any] = asset_crud.get_multi(db=db, skip=0, limit=1)
    total_assets = len(assets)

    confirmed_assets, _ = asset_crud.get_multi_with_search(
        db=db, skip=0, limit=10000, filters={"ownership_status": "已确权"}
    )
    confirmed_count = len(confirmed_assets)

    unconfirmed_assets, _ = asset_crud.get_multi_with_search(
        db=db, skip=0, limit=10000, filters={"ownership_status": "未确权"}
    )
    unconfirmed_count = len(unconfirmed_assets)

    partial_assets, _ = asset_crud.get_multi_with_search(
        db=db, skip=0, limit=10000, filters={"ownership_status": "部分确权"}
    )
    partial_count = len(partial_assets)

    distribution = [
        ChartDataItem(
            name="已确权",
            value=confirmed_count,
            percentage=(confirmed_count / total_assets * 100)
            if total_assets > 0
            else 0,
        ),
        ChartDataItem(
            name="未确权",
            value=unconfirmed_count,
            percentage=(unconfirmed_count / total_assets * 100)
            if total_assets > 0
            else 0,
        ),
        ChartDataItem(
            name="部分确权",
            value=partial_count,
            percentage=(partial_count / total_assets * 100) if total_assets > 0 else 0,
        ),
    ]

    return DistributionResponse(
        categories=distribution,
        total=total_assets,
    )


@router.get(
    "/property-nature-distribution",
    response_model=DistributionResponse,
    summary="获取物业性质分布统计",
)
async def get_property_nature_distribution(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> DistributionResponse:
    """
    获取按物业性质的资产分布统计
    """
    assets: list[Any] = asset_crud.get_multi(db=db, skip=0, limit=1)
    total_assets = len(assets)

    commercial_assets, _ = asset_crud.get_multi_with_search(
        db=db, skip=0, limit=10000, filters={"property_nature": "经营性"}
    )
    commercial_count = len(commercial_assets)

    non_commercial_assets, _ = asset_crud.get_multi_with_search(
        db=db, skip=0, limit=10000, filters={"property_nature": "非经营性"}
    )
    non_commercial_count = len(non_commercial_assets)

    distribution = [
        ChartDataItem(
            name="经营性",
            value=commercial_count,
            percentage=(commercial_count / total_assets * 100)
            if total_assets > 0
            else 0,
        ),
        ChartDataItem(
            name="非经营性",
            value=non_commercial_count,
            percentage=(non_commercial_count / total_assets * 100)
            if total_assets > 0
            else 0,
        ),
    ]

    return DistributionResponse(
        categories=distribution,
        total=total_assets,
    )


@router.get(
    "/usage-status-distribution",
    response_model=DistributionResponse,
    summary="获取使用状态分布统计",
)
async def get_usage_status_distribution(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> DistributionResponse:
    """
    获取按使用状态的资产分布统计
    """
    assets: list[Any] = asset_crud.get_multi(db=db, skip=0, limit=1)
    total_assets = len(assets)

    rented_assets, _ = asset_crud.get_multi_with_search(
        db=db, skip=0, limit=10000, filters={"usage_status": "出租"}
    )
    rented_count = len(rented_assets)

    vacant_assets, _ = asset_crud.get_multi_with_search(
        db=db, skip=0, limit=10000, filters={"usage_status": "空置"}
    )
    vacant_count = len(vacant_assets)

    self_used_assets, _ = asset_crud.get_multi_with_search(
        db=db, skip=0, limit=10000, filters={"usage_status": "自用"}
    )
    self_used_count = len(self_used_assets)

    distribution = [
        ChartDataItem(
            name="出租",
            value=rented_count,
            percentage=(rented_count / total_assets * 100) if total_assets > 0 else 0,
        ),
        ChartDataItem(
            name="空置",
            value=vacant_count,
            percentage=(vacant_count / total_assets * 100) if total_assets > 0 else 0,
        ),
        ChartDataItem(
            name="自用",
            value=self_used_count,
            percentage=(self_used_count / total_assets * 100)
            if total_assets > 0
            else 0,
        ),
    ]

    return DistributionResponse(
        categories=distribution,
        total=total_assets,
    )


@router.get("/trend/{metric}", response_model=TrendDataResponse, summary="获取趋势数据")
async def get_trend_data(
    metric: str = Path(..., description="指标名称"),
    period: str = Query(
        "monthly", pattern="^(daily|weekly|monthly|yearly)$", description="时间周期"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> TrendDataResponse:
    """
    获取指标趋势数据

    Args:
        metric: 指标名称 (occupancy_rate, income, expense等)
        period: 时间周期 (daily, weekly, monthly, yearly)
    """
    # 这里简化实现,实际项目中可以根据时间周期和指标从历史数据中计算趋势
    # 目前返回模拟数据
    from ...schemas.statistics import TimeSeriesDataPoint

    time_series: list[TimeSeriesDataPoint] = []

    if metric == "occupancy_rate":
        # 模拟最近6个月的出租率趋势
        for i in range(6):
            month_value = 75 + (i * 2) + (hash(f"{metric}_{i}") % 10)
            time_series.append(
                TimeSeriesDataPoint(
                    date=datetime.strptime(f"2024-{i + 1:02d}-01", "%Y-%m-%d"),
                    value=float(round(min(month_value, 95), 1)),
                    label=f"2024-{i + 1:02d}",
                )
            )
    elif metric == "income":
        # 模拟最近6个月的收入趋势
        base_income = 1000000
        for i in range(6):
            month_income = base_income + (i * 50000) + (hash(f"{metric}_{i}") % 100000)
            time_series.append(
                TimeSeriesDataPoint(
                    date=datetime.strptime(f"2024-{i + 1:02d}-01", "%Y-%m-%d"),
                    value=float(round(month_income, 2)),
                    label=f"2024-{i + 1:02d}",
                )
            )
    else:
        # 默认返回简单的趋势数据
        for i in range(6):
            time_series.append(
                TimeSeriesDataPoint(
                    date=datetime.strptime(f"2024-{i + 1:02d}-01", "%Y-%m-%d"),
                    value=float(100 + i * 10),
                    label=f"2024-{i + 1:02d}",
                )
            )

    return TrendDataResponse(
        metric_name=metric,
        time_series=time_series,
        trend_direction="up" if metric == "income" else "stable",
        change_percentage=5.0 if metric == "income" else None,
    )


@router.get("/occupancy-rate", summary="获取出租率统计")
async def get_occupancy_rate_statistics(
    ownership_status: str | None = Query(None, description="确权状态筛选"),
    property_nature: str | None = Query(None, description="物业性质筛选"),
    usage_status: str | None = Query(None, description="使用状态筛选"),
    business_category: str | None = Query(None, description="业务分类筛选"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    """
    获取出租率统计数据
    """
    # 构建筛选条件
    filters: dict[str, Any] = {}
    if ownership_status:
        filters["ownership_status"] = ownership_status
    if property_nature:
        filters["property_nature"] = property_nature
    if usage_status:
        filters["usage_status"] = usage_status
    if business_category:
        filters["business_category"] = business_category

    # 计算出租率
    occupancy_service = OccupancyService(db)
    stats = occupancy_service.calculate_with_aggregation(filters)

    return {
        "success": True,
        "data": {
            "overall_occupancy_rate": stats["overall_rate"],
            "total_rentable_area": stats["total_rentable_area"],
            "total_rented_area": stats["total_rented_area"],
            "total_unrented_area": stats["total_rentable_area"]
            - stats["total_rented_area"],
            "total_assets": stats["total_assets"],
            "rentable_assets": stats["rentable_assets_count"],
            "generated_at": datetime.now().isoformat(),
            "filters_applied": filters,
        },
        "message": "出租率统计数据获取成功",
    }


# asset-distribution endpoint also migrated to statistics_modules/distribution.py

@router.get("/area-statistics", summary="获取面积统计")
async def get_area_statistics(
    ownership_status: str | None = Query(None, description="确权状态筛选"),
    property_nature: str | None = Query(None, description="物业性质筛选"),
    usage_status: str | None = Query(None, description="使用状态筛选"),
    include_deleted: bool = Query(False, description="是否包含已删除资产"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    """
    获取面积统计数据
    """
    # 构建筛选条件
    filters: dict[str, Any] = {}
    if ownership_status:
        filters["ownership_status"] = ownership_status
    if property_nature:
        filters["property_nature"] = property_nature
    if usage_status:
        filters["usage_status"] = usage_status
    if not include_deleted:
        filters["data_status"] = "正常"

    # 计算面积汇总
    area_service = AreaService(db)
    summary = area_service.calculate_summary_with_aggregation(filters)

    return {
        "success": True,
        "data": {
            "total_assets": summary["total_assets"],
            "total_land_area": summary["total_land_area"],
            "total_property_area": summary["total_land_area"],  # 土地面积作为物业面积
            "total_rentable_area": summary["total_rentable_area"],
            "total_rented_area": summary["total_rented_area"],
            "total_unrented_area": summary["total_unrented_area"],
            "total_non_commercial_area": summary["total_non_commercial_area"],
            "assets_with_area_data": summary["assets_with_area_data"],
            "overall_occupancy_rate": summary["overall_occupancy_rate"],
            "generated_at": datetime.now().isoformat(),
            "filters_applied": filters,
        },
        "message": "面积统计数据获取成功",
    }


@router.get("/comprehensive", summary="获取综合统计")
async def get_comprehensive_statistics(
    ownership_status: str | None = Query(None, description="确权状态筛选"),
    property_nature: str | None = Query(None, description="物业性质筛选"),
    usage_status: str | None = Query(None, description="使用状态筛选"),
    include_deleted: bool = Query(False, description="是否包含已删除资产"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    """
    获取综合统计数据
    """
    # 构建筛选条件
    filters: dict[str, Any] = {}
    if ownership_status:
        filters["ownership_status"] = ownership_status
    if property_nature:
        filters["property_nature"] = property_nature
    if usage_status:
        filters["usage_status"] = usage_status
    if not include_deleted:
        filters["data_status"] = "正常"

    # 基础统计
    assets_list, _ = asset_crud.get_multi_with_search(
        db=db, skip=0, limit=1, filters=filters
    )
    total_assets = len(assets_list)

    if total_assets == 0:
        return {
            "success": False,
            "message": "没有找到符合条件的资产数据",
            "data": None,
        }

    # 获取面积统计
    area_service = AreaService(db)
    area_stats = area_service.calculate_summary_with_aggregation(filters)

    # 获取出租率统计
    occupancy_service = OccupancyService(db)
    occupancy_stats = occupancy_service.calculate_with_aggregation(filters)

    # 获取财务统计
    assets, _ = asset_crud.get_multi_with_search(
        db=db, skip=0, limit=10000, filters=filters
    )

    financial_stats = {
        "total_annual_income": 0.0,
        "total_annual_expense": 0.0,
        "total_net_income": 0.0,
        "total_monthly_rent": 0.0,
        "assets_with_financial_data": 0,
    }

    for asset in assets:
        if getattr(asset, "annual_income", None):
            financial_stats["total_annual_income"] += to_float(
                getattr(asset, "annual_income")
            )
            financial_stats["assets_with_financial_data"] += 1

        if getattr(asset, "annual_expense", None):
            financial_stats["total_annual_expense"] += to_float(
                getattr(asset, "annual_expense")
            )

        if getattr(asset, "net_income", None):
            financial_stats["total_net_income"] += to_float(
                getattr(asset, "net_income")
            )

        if getattr(asset, "monthly_rent", None):
            financial_stats["total_monthly_rent"] += to_float(
                getattr(asset, "monthly_rent")
            )

    # 按状态统计
    ownership_distribution: dict[str, int] = {}
    property_nature_distribution: dict[str, int] = {}
    usage_status_distribution: dict[str, int] = {}

    for asset in assets:
        # 权属状态分布
        ownership = getattr(asset, "ownership_status", None) or "未知"
        ownership_distribution[ownership] = ownership_distribution.get(ownership, 0) + 1

        # 物业性质分布
        nature = getattr(asset, "property_nature", None) or "未知"
        property_nature_distribution[nature] = (
            property_nature_distribution.get(nature, 0) + 1
        )

        # 使用状态分布
        usage = getattr(asset, "usage_status", None) or "未知"
        usage_status_distribution[usage] = usage_status_distribution.get(usage, 0) + 1

    comprehensive_data = {
        # 基础统计
        "basic_stats": {
            "total_assets": total_assets,
            "ownership_distribution": ownership_distribution,
            "property_nature_distribution": property_nature_distribution,
            "usage_status_distribution": usage_status_distribution,
        },
        # 面积统计
        "area_stats": area_stats,
        # 出租率统计
        "occupancy_stats": occupancy_stats,
        # 财务统计
        "financial_stats": {
            **financial_stats,
            "total_annual_income": round(financial_stats["total_annual_income"], 2),
            "total_annual_expense": round(financial_stats["total_annual_expense"], 2),
            "total_net_income": round(financial_stats["total_net_income"], 2),
            "total_monthly_rent": round(financial_stats["total_monthly_rent"], 2),
        },
        "generated_at": datetime.now().isoformat(),
        "filters_applied": filters,
    }

    return {
        "success": True,
        "data": comprehensive_data,
        "message": "综合统计数据获取成功",
    }
