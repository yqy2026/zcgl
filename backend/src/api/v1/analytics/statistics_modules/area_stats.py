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
from sqlalchemy.orm import Session

from src.constants.cache_constants import CACHE_TTL_SHORT_SECONDS
from src.crud.asset import asset_crud
from src.database import get_db
from src.middleware.auth import get_current_active_user
from src.models.auth import User
from src.schemas.statistics import AreaSummaryResponse
from src.services.analytics import AreaService
from src.utils.cache_manager import cache_statistics
from src.utils.numeric import to_float

logger = logging.getLogger(__name__)

# 创建面积统计路由器
router = APIRouter()


@cache_statistics(expire=CACHE_TTL_SHORT_SECONDS)  # 10分钟缓存
@router.get("/area-summary", response_model=AreaSummaryResponse)
def get_area_summary(
    should_include_deleted: bool = False,
    should_use_aggregation: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
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

    # 构建筛选条件
    filters: dict[str, Any] = {}
    if not should_include_deleted:
        filters["data_status"] = "正常"

    # 使用 AreaService 计算面积汇总
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


@router.get("/area-statistics", summary="获取面积统计")
def get_area_statistics(
    ownership_status: str | None = Query(None, description="确权状态筛选"),
    property_nature: str | None = Query(None, description="物业性质筛选"),
    usage_status: str | None = Query(None, description="使用状态筛选"),
    should_include_deleted: bool = Query(False, description="是否包含已删除资产"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
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
    # 构建筛选条件
    filters: dict[str, Any] = {}
    if ownership_status:
        filters["ownership_status"] = ownership_status
    if property_nature:
        filters["property_nature"] = property_nature
    if usage_status:
        filters["usage_status"] = usage_status
    if not should_include_deleted:
        filters["data_status"] = "正常"

    # 获取资产数据
    assets, _ = asset_crud.get_multi_with_search(
        db=db, skip=0, limit=10000, filters=filters
    )

    # 计算面积统计
    total_land_area = 0.0
    total_rentable_area = 0.0
    total_rented_area = 0.0

    for asset in assets:
        if getattr(asset, "land_area", None):
            total_land_area += to_float(getattr(asset, "land_area"))
        if getattr(asset, "rentable_area", None):
            total_rentable_area += to_float(getattr(asset, "rentable_area"))
        if getattr(asset, "rented_area", None):
            total_rented_area += to_float(getattr(asset, "rented_area"))

    # 计算占用率
    occupancy_rate = (
        (total_rented_area / total_rentable_area * 100)
        if total_rentable_area > 0
        else 0.0
    )

    return {
        "success": True,
        "data": {
            "total_land_area": round(total_land_area, 2),
            "total_rentable_area": round(total_rentable_area, 2),
            "total_rented_area": round(total_rented_area, 2),
            "total_unrented_area": round(total_rentable_area - total_rented_area, 2),
            "occupancy_rate": round(occupancy_rate, 2),
            "total_assets": len(assets),
            "filters_applied": filters,
        },
        "message": "面积统计数据获取成功",
    }
