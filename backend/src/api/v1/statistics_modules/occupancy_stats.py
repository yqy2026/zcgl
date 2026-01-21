"""
占用率统计模块

提供占用率相关的统计端点:
- 整体占用率 (occupancy-rate/overall)
- 分类占用率 (occupancy-rate/by-category)
- 占用率统计 (occupancy-rate)

Created: 2026-01-17 (Phase 2 - Large File Splitting)
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ....core.exception_handler import bad_request
from ....database import get_db
from ....middleware.auth import get_current_active_user
from ....models.auth import User
from ....schemas.statistics import (
    CategoryOccupancyRateListResponse,
    CategoryOccupancyRateResponse,
    OccupancyRateStatsResponse,
)
from ....services.analytics import OccupancyService
from ....utils.cache_manager import cache_statistics

logger = logging.getLogger(__name__)

# 创建占用率统计路由器
router = APIRouter()


@router.get("/occupancy-rate/overall", response_model=OccupancyRateStatsResponse)
def get_overall_occupancy_rate(
    include_deleted: bool = False,
    use_aggregation: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> OccupancyRateStatsResponse:
    """
    获取整体出租率统计

    使用数据库聚合查询计算总体占用率，包括：
    - 总可租面积
    - 已出租面积
    - 占用率百分比

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

    # 使用 OccupancyService 计算占用率
    service = OccupancyService(db)
    stats = service.calculate_with_aggregation(filters)

    logger.info(f"出租率计算完成: {stats}")

    return OccupancyRateStatsResponse(
        overall_occupancy_rate=stats["overall_rate"],
        total_rentable_area=stats["total_rentable_area"],
        total_rented_area=stats["total_rented_area"],
        calculated_at=datetime.now(),
    )


@cache_statistics(expire=600)  # 10分钟缓存  # type: ignore[misc]
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

    根据指定的分类字段（如业务类别、物业性质等）分组计算占用率。

    Args:
        category_field: 分类字段名（必须在白名单中）
        include_deleted: 是否包含已删除的资产
        use_aggregation: 是否使用数据库聚合查询（推荐，性能更好）
        db: 数据库会话

    Returns:
        按类别的出租率统计信息

    Raises:
        HTTPException: 如果 category_field 不在允许的字段列表中
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
        raise bad_request(f"无效的分类字段。支持的字段: {', '.join(valid_fields)}")

    # 构建筛选条件
    filters: dict[str, Any] = {}
    if not include_deleted:
        filters["data_status"] = "正常"

    # 使用 OccupancyService 计算分类占用率
    service = OccupancyService(db)
    category_results = service.calculate_category_with_aggregation(
        category_field, filters
    )

    # 转换为响应格式
    category_occupancy = []
    for category_name, category_stats in category_results.items():
        category_occupancy.append(
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
        categories=category_occupancy,
        generated_at=datetime.now(),
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
    获取出租率统计数据（支持多维度筛选）

    根据提供的筛选条件计算占用率，返回详细的统计信息。

    Args:
        ownership_status: 确权状态筛选
        property_nature: 物业性质筛选
        usage_status: 使用状态筛选
        business_category: 业务分类筛选

    Returns:
        出租率统计数据，包括：
        - 总体占用率
        - 总可租面积
        - 已出租面积
        - 未出租面积
        - 资产总数
        - 可租资产数
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
