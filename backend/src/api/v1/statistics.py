from typing import Any
"""
统计分析API路由
"""

import logging
from datetime import datetime


from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from ...crud.asset import asset_crud
from ...database import get_db
from ...schemas.asset import DataStatus
from ...schemas.statistics import (
    AreaSummaryResponse,
    BasicStatisticsResponse,
    CategoryOccupancyRateResponse,
    ChartDataItem,
    DashboardDataResponse,
    DistributionResponse,
    FinancialSummaryResponse,
    OccupancyRateStatsResponse,
    TrendDataResponse,
)
from ...services.occupancy_calculator import OccupancyRateCalculator
from ...utils.cache_manager import cache_statistics, get_cache_manager

# 配置日志
logger = logging.getLogger(__name__)

# 创建统计路由器
router = APIRouter(tags=["统计分析"])


# 将可能为 None/Decimal/str 的值安全转换为 float
def to_float(value: Any) -> float:
    try:
        if value is None:
            return 0.0
        # 避免 Decimal 与 float 混算
        if hasattr(value, "__float__"):
            return float(value)
        # 处理字符串
        if isinstance(value, str):
            return float(value) if value.strip() else 0.0
        # 直接数字类型
        return float(value)
    except Exception:
        return 0.0


def _calculate_occupancy_with_aggregation(
    db: Session, filters: dict[str, Any]
) -> dict[str, Any][str, float]:
    """
    使用数据库聚合查询计算出租率 - 推荐方法

    Args:
        db: 数据库会话
        filters: 筛选条件

    Returns:
        出租率统计结果
    """
    try:
        from ...models.asset import Asset

        # 构建基础查询
        query = db.query(Asset)

        # 应用筛选条件
        if filters:
            for key, value in filters.items():
                if hasattr(Asset, key) and value is not None:
                    query = query.filter(getattr(Asset, key) == value)

        # 使用数据库聚合函数计算 - 避免加载所有数据到内存
        result = query.with_entities(
            func.cast(
                func.sum(func.coalesce(Asset.rentable_area, 0)), func.Float
            ).label("total_rentable_area"),
            func.cast(func.sum(func.coalesce(Asset.rented_area, 0)), func.Float).label(
                "total_rented_area"
            ),
            func.count(Asset.id).label("total_assets"),
            func.count(case([(Asset.rentable_area > 0, 1)])).label(
                "rentable_assets_count"
            ),
        ).first()

        # 提取结果并转换为float
        total_rentable_area = to_float(result.total_rentable_area)
        total_rented_area = to_float(result.total_rented_area)
        total_assets = int(result.total_assets or 0)
        rentable_assets_count = int(result.rentable_assets_count or 0)

        # 计算出租率
        overall_rate = (
            (total_rented_area / total_rentable_area * 100)
            if total_rentable_area > 0
            else 0.0
        )

        logger.info(
            f"数据库聚合查询完成: 总资产={total_assets}, 可出租资产={rentable_assets_count}"
        )

        return {
            "overall_rate": round(overall_rate, 2),
            "total_rentable_area": round(total_rentable_area, 2),
            "total_rented_area": round(total_rented_area, 2),
            "total_assets": total_assets,
            "rentable_assets_count": rentable_assets_count,
        }

    except Exception as e:
        logger.error(f"数据库聚合查询失败: {str(e)}")
        # 降级到内存计算
        return _calculate_occupancy_in_memory(db, filters)


def _calculate_occupancy_in_memory(
    db: Session, filters: dict[str, Any]
) -> dict[str, Any][str, float]:
    """
    在内存中计算出租率 - 兼容性方法

    Args:
        db: 数据库会话
        filters: 筛选条件

    Returns:
        出租率统计结果
    """
    try:
        # 分批获取数据以避免内存问题
        batch_size = 1000
        offset = 0
        all_assets = []

        while True:
            assets_batch, _ = asset_crud.get_multi_with_search(
                db=db, skip=offset, limit=batch_size, filters=filters
            )

            if not assets_batch:
                break

            all_assets.extend(assets_batch)
            offset += batch_size

            # 防止无限循环
            if len(assets_batch) < batch_size:
                break

        logger.info(f"内存计算模式：获取到 {len(all_assets)} 个资产")

        # 使用现有的计算器
        stats = OccupancyRateCalculator.calculate_overall_occupancy_rate(all_assets)

        return stats

    except Exception as e:
        logger.error(f"内存计算失败: {str(e)}")
        raise


def _calculate_category_occupancy_with_aggregation(
    db: Session, category_field: str, filters: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    """
    使用数据库聚合查询计算分类出租率

    Args:
        db: 数据库会话
        category_field: 分类字段
        filters: 筛选条件

    Returns:
        分类出租率统计结果
    """
    try:
        from ...models.asset import Asset

        # 构建基础查询
        query = db.query(Asset)

        # 应用筛选条件
        if filters:
            for key, value in filters.items():
                if hasattr(Asset, key) and value is not None:
                    query = query.filter(getattr(Asset, key) == value)

        # 按分类字段聚合查询
        results = (
            query.with_entities(
                getattr(Asset, category_field).label("category"),
                func.cast(
                    func.sum(func.coalesce(Asset.rentable_area, 0)), func.Float
                ).label("total_rentable_area"),
                func.cast(
                    func.sum(func.coalesce(Asset.rented_area, 0)), func.Float
                ).label("total_rented_area"),
                func.count(Asset.id).label("total_assets"),
                func.count(case([(Asset.rentable_area > 0, 1)])).label(
                    "rentable_assets_count"
                ),
            )
            .group_by(getattr(Asset, category_field))
            .all()
        )

        # 处理结果
        categories = {}
        for result in results:
            category = result.category or "未知"
            total_rentable = to_float(result.total_rentable_area)
            total_rented = to_float(result.total_rented_area)
            total_assets = int(result.total_assets or 0)
            rentable_assets = int(result.rentable_assets_count or 0)

            # 计算出租率
            overall_rate = (
                (total_rented / total_rentable * 100) if total_rentable > 0 else 0.0
            )

            categories[category] = {
                "overall_rate": round(overall_rate, 2),
                "total_rentable_area": round(total_rentable, 2),
                "total_rented_area": round(total_rented, 2),
                "total_unrented_area": round(total_rentable - total_rented, 2),
                "asset_count": total_assets,
                "rentable_asset_count": rentable_assets,
            }

        return categories

    except Exception as e:
        logger.error(f"分类数据库聚合查询失败: {str(e)}")
        # 降级到内存计算
        return _calculate_category_occupancy_in_memory(db, category_field, filters)


def _calculate_category_occupancy_in_memory(
    db: Session, category_field: str, filters: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    """
    在内存中计算分类出租率

    Args:
        db: 数据库会话
        category_field: 分类字段
        filters: 筛选条件

    Returns:
        分类出租率统计结果
    """
    try:
        # 分批获取数据以避免内存问题
        batch_size = 1000
        offset = 0
        all_assets = []

        while True:
            assets_batch, _ = asset_crud.get_multi_with_search(
                db=db, skip=offset, limit=batch_size, filters=filters
            )

            if not assets_batch:
                break

            all_assets.extend(assets_batch)
            offset += batch_size

            # 防止无限循环
            if len(assets_batch) < batch_size:
                break

        logger.info(f"分类内存计算模式：获取到 {len(all_assets)} 个资产")

        # 使用现有的计算器
        stats = OccupancyRateCalculator.calculate_occupancy_by_category(
            all_assets, category_field
        )

        return stats

    except Exception as e:
        logger.error(f"分类内存计算失败: {str(e)}")
        raise


def _calculate_area_summary_with_aggregation(
    db: Session, filters: dict[str, Any]
) -> dict[str, Any][str, float]:
    """
    使用数据库聚合查询计算面积汇总

    Args:
        db: 数据库会话
        filters: 筛选条件

    Returns:
        面积汇总统计结果
    """
    try:
        from ...models.asset import Asset

        # 构建基础查询
        query = db.query(Asset)

        # 应用筛选条件
        if filters:
            for key, value in filters.items():
                if hasattr(Asset, key) and value is not None:
                    query = query.filter(getattr(Asset, key) == value)

        # 使用数据库聚合函数计算
        result = query.with_entities(
            func.count(Asset.id).label("total_assets"),
            func.cast(func.sum(func.coalesce(Asset.land_area, 0)), func.Float).label(
                "total_land_area"
            ),
            func.cast(
                func.sum(func.coalesce(Asset.rentable_area, 0)), func.Float
            ).label("total_rentable_area"),
            func.cast(func.sum(func.coalesce(Asset.rented_area, 0)), func.Float).label(
                "total_rented_area"
            ),
            func.cast(
                func.sum(func.coalesce(Asset.non_commercial_area, 0)), func.Float
            ).label("total_non_commercial_area"),
            func.count(case([(Asset.land_area.isnot(None), 1)])).label(
                "assets_with_area_data"
            ),
        ).first()

        # 提取并转换结果
        total_assets = int(result.total_assets or 0)
        total_land_area = to_float(result.total_land_area)
        total_rentable_area = to_float(result.total_rentable_area)
        total_rented_area = to_float(result.total_rented_area)
        # 计算未出租面积（可出租面积 - 已出租面积）
        total_unrented_area = max(total_rentable_area - total_rented_area, 0.0)
        total_non_commercial_area = to_float(result.total_non_commercial_area)
        assets_with_area_data = int(result.assets_with_area_data or 0)

        # 计算整体出租率
        overall_occupancy_rate = (
            (total_rented_area / total_rentable_area * 100)
            if total_rentable_area > 0
            else 0.0
        )

        logger.info(
            f"数据库聚合查询完成面积汇总: 总资产={total_assets}, 有面积数据={assets_with_area_data}"
        )

        return {
            "total_assets": total_assets,
            "total_land_area": round(total_land_area, 2),
            "total_rentable_area": round(total_rentable_area, 2),
            "total_rented_area": round(total_rented_area, 2),
            "total_unrented_area": round(total_unrented_area, 2),
            "total_non_commercial_area": round(total_non_commercial_area, 2),
            "assets_with_area_data": assets_with_area_data,
            "overall_occupancy_rate": round(overall_occupancy_rate, 2),
        }

    except Exception as e:
        logger.error(f"面积汇总数据库聚合查询失败: {str(e)}")
        # 降级到内存计算
        return _calculate_area_summary_in_memory(db, filters)


def _calculate_area_summary_in_memory(
    db: Session, filters: dict[str, Any]
) -> dict[str, Any][str, float]:
    """
    在内存中计算面积汇总

    Args:
        db: 数据库会话
        filters: 筛选条件

    Returns:
        面积汇总统计结果
    """
    try:
        # 分批获取数据
        batch_size = 1000
        offset = 0
        all_assets = []

        while True:
            assets_batch, _ = asset_crud.get_multi_with_search(
                db=db, skip=offset, limit=batch_size, filters=filters
            )

            if not assets_batch:
                break

            all_assets.extend(assets_batch)
            offset += batch_size

            if len(assets_batch) < batch_size:
                break

        logger.info(f"面积汇总内存计算模式：获取到 {len(all_assets)} 个资产")

        # 计算面积汇总
        summary = {
            "total_assets": len(all_assets),
            "total_land_area": 0.0,
            "total_rentable_area": 0.0,
            "total_rented_area": 0.0,
            "total_unrented_area": 0.0,
            "total_non_commercial_area": 0.0,
            "assets_with_area_data": 0,
        }

        for asset in all_assets:
            if getattr(asset, "land_area", None):
                summary["total_land_area"] += to_float(getattr(asset, "land_area"))
                summary["assets_with_area_data"] += 1

            if getattr(asset, "rentable_area", None):
                summary["total_rentable_area"] += to_float(
                    getattr(asset, "rentable_area")
                )

            if getattr(asset, "rented_area", None):
                summary["total_rented_area"] += to_float(getattr(asset, "rented_area"))

            if getattr(asset, "unrented_area", None):
                summary["total_unrented_area"] += to_float(
                    getattr(asset, "unrented_area")
                )

            if getattr(asset, "non_commercial_area", None):
                summary["total_non_commercial_area"] += to_float(
                    getattr(asset, "non_commercial_area")
                )

        # 计算整体出租率
        if summary["total_rentable_area"] > 0:
            overall_occupancy_rate = (
                summary["total_rented_area"] / summary["total_rentable_area"]
            ) * 100
            summary["overall_occupancy_rate"] = round(overall_occupancy_rate, 2)
        else:
            summary["overall_occupancy_rate"] = 0.0

        # 格式化数据
        for key in [
            "total_land_area",
            "total_rentable_area",
            "total_rented_area",
            "total_unrented_area",
            "total_non_commercial_area",
        ]:
            summary[key] = round(summary[key], 2)

        return summary

    except Exception as e:
        logger.error(f"面积汇总内存计算失败: {str(e)}")
        raise


@router.get(
    "/basic", response_model=BasicStatisticsResponse, summary="获取基础统计数据"
)
async def get_basic_statistics(
    ownership_status: str | None = Query(None, description="确权状态筛选"),
    property_nature: str | None = Query(None, description="物业性质筛选"),
    usage_status: str | None = Query(None, description="使用状态筛选"),
    ownership_entity: str | None = Query(None, description="权属方筛选"),
    db: Session = Depends(get_db),
):
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
    try:
        # 构建筛选条件
        filters = {}
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
        total_assets = asset_crud.count_with_search(db=db, filters=filters)

        if total_assets == 0:
            return {
                "success": False,
                "message": "没有找到符合条件的资产数据",
                "data": None,
            }

        # 按确权状态统计
        confirmed_count = asset_crud.count_with_search(
            db=db, filters={**filters, "ownership_status": "已确权"}
        )
        unconfirmed_count = asset_crud.count_with_search(
            db=db, filters={**filters, "ownership_status": "未确权"}
        )
        partial_count = asset_crud.count_with_search(
            db=db, filters={**filters, "ownership_status": "部分确权"}
        )

        # 按物业性质统计
        commercial_count = asset_crud.count_with_search(
            db=db, filters={**filters, "property_nature": "经营性"}
        )
        non_commercial_count = asset_crud.count_with_search(
            db=db, filters={**filters, "property_nature": "非经营性"}
        )

        # 按使用状态统计
        rented_count = asset_crud.count_with_search(
            db=db, filters={**filters, "usage_status": "出租"}
        )
        self_used_count = asset_crud.count_with_search(
            db=db, filters={**filters, "usage_status": "自用"}
        )
        vacant_count = asset_crud.count_with_search(
            db=db, filters={**filters, "usage_status": "空置"}
        )

        # 构建统计数据
        basic_stats = {
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
            ownership_status=basic_stats["ownership_status"],
            property_nature=basic_stats["property_nature"],
            usage_status=basic_stats["usage_status"],
            generated_at=basic_stats["generated_at"],
            filters_applied=basic_stats["filters_applied"],
        )

    except Exception as e:
        logger.error(f"获取基础统计数据异常: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取基础统计数据失败: {str(e)}")


# 仪表板端点已移除，请使用以下替代端点：
# - /api/v1/statistics/basic - 基础统计
# - /api/v1/statistics/summary - 统计摘要
# - /api/v1/statistics/area-summary - 面积汇总
# - /api/v1/statistics/financial-summary - 财务汇总


@router.get(
    "/basic", response_model=BasicStatisticsResponse, summary="获取基础统计数据"
)
async def get_basic_statistics(db: Session = Depends(get_db)):
    """
    获取基础统计数据
    """
    try:
        # 总资产数
        total_assets = asset_crud.count(db=db)

        # 按权属状态统计
        confirmed_count = asset_crud.count_with_search(
            db=db, search_criteria={"ownershipStatus": "已确权"}
        )
        pending_count = asset_crud.count_with_search(
            db=db, search_criteria={"ownershipStatus": "待确权"}
        )
        unowned_count = asset_crud.count_with_search(
            db=db, search_criteria={"ownershipStatus": "未确权"}
        )

        # 按使用状态统计
        rented_count = asset_crud.count_with_search(
            db=db, search_criteria={"usageStatus": "已出租"}
        )
        vacant_count = asset_crud.count_with_search(
            db=db, search_criteria={"usageStatus": "空置"}
        )
        under_maintenance_count = asset_crud.count_with_search(
            db=db, search_criteria={"usageStatus": "维护中"}
        )

        # 计算总面积
        total_land_area = db.execute(
            "SELECT COALESCE(SUM(CASE WHEN land_area IS NOT NULL THEN land_area ELSE 0 END), 0) "
            "FROM assets"
        ).scalar()
        total_property_area = db.execute(
            "SELECT COALESCE(SUM(CASE WHEN actual_property_area IS NOT NULL THEN actual_property_area ELSE 0 END), 0) "
            "FROM assets"
        ).scalar()

        # 计算出租率
        total_rentable_area = db.execute(
            "SELECT COALESCE(SUM(CASE WHEN rentable_area IS NOT NULL THEN rentable_area ELSE 0 END), 0) "
            "FROM assets"
        ).scalar()
        total_rented_area = db.execute(
            "SELECT COALESCE(SUM(CASE WHEN rented_area IS NOT NULL THEN rented_area ELSE 0 END), 0) "
            "FROM assets"
        ).scalar()

        occupancy_rate = (
            (total_rented_area / total_rentable_area * 100)
            if total_rentable_area > 0
            else 0
        )

        return {
            "success": True,
            "data": {
                "total_assets": total_assets,
                "ownership_status": {
                    "confirmed": confirmed_count,
                    "pending": pending_count,
                    "unowned": unowned_count,
                },
                "usage_status": {
                    "rented": rented_count,
                    "vacant": vacant_count,
                    "under_maintenance": under_maintenance_count,
                },
                "areas": {
                    "total_land_area": float(total_land_area),
                    "total_property_area": float(total_property_area),
                },
                "occupancy_rate": float(occupancy_rate),
                "last_updated": datetime.now().isoformat(),
            },
            "message": "基础统计数据获取成功",
        }

    except Exception as e:
        logger.error(f"获取基础统计数据失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取基础统计数据失败: {str(e)}")


# @cache_statistics(expire=1800)  # 30分钟缓存 - 临时禁用
@router.get("/summary", response_model=BasicStatisticsResponse, summary="获取统计摘要")
async def get_statistics_summary(db: Session = Depends(get_db)):
    """
    获取统计摘要信息
    """
    # DEBUG: 添加调试日志
    print("=== DEBUG: statistics.py中的get_statistics_summary被调用 ===")
    logger.info("=== statistics.py中的get_statistics摘要函数被调用 ===")

    try:
        # 总资产数
        total_assets = asset_crud.count(db=db)

        # 按确权状态统计
        confirmed_count = asset_crud.count_with_search(
            db=db, filters={"ownership_status": "已确权"}
        )
        unconfirmed_count = asset_crud.count_with_search(
            db=db, filters={"ownership_status": "未确权"}
        )
        partial_count = asset_crud.count_with_search(
            db=db, filters={"ownership_status": "部分确权"}
        )

        # 按物业性质统计
        commercial_count = asset_crud.count_with_search(
            db=db, filters={"property_nature": "经营性"}
        )
        non_commercial_count = asset_crud.count_with_search(
            db=db, filters={"property_nature": "非经营性"}
        )

        # 按使用状态统计
        rented_count = asset_crud.count_with_search(
            db=db, filters={"usage_status": "出租"}
        )
        self_used_count = asset_crud.count_with_search(
            db=db, filters={"usage_status": "自用"}
        )
        vacant_count = asset_crud.count_with_search(
            db=db, filters={"usage_status": "空置"}
        )

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

    except Exception as e:
        logger.error(f"获取统计摘要异常: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取统计摘要失败: {str(e)}")


@cache_statistics(expire=600)  # 10分钟缓存
@router.get("/occupancy-rate/overall", response_model=OccupancyRateStatsResponse)
def get_overall_occupancy_rate(
    include_deleted: bool = False,
    use_aggregation: bool = True,
    db: Session = Depends(get_db),
):
    """
    获取整体出租率统计

    Args:
        include_deleted: 是否包含已删除的资产
        use_aggregation: 是否使用数据库聚合查询（推荐，性能更好）
        db: 数据库会话

    Returns:
        整体出租率统计信息
    """
    try:
        logger.info(
            f"开始计算整体出租率，包含已删除: {include_deleted}, 使用聚合: {use_aggregation}"
        )

        # 构建筛选条件
        filters = {}
        if not include_deleted:
            filters["data_status"] = DataStatus.NORMAL.value

        if use_aggregation:
            # 使用数据库聚合查询 - 性能更好
            stats = _calculate_occupancy_with_aggregation(db, filters)
        else:
            # 使用内存计算 - 兼容性更好
            stats = _calculate_occupancy_in_memory(db, filters)

        logger.info(f"出租率计算完成: {stats}")

        return OccupancyRateStatsResponse(
            overall_occupancy_rate=stats["overall_rate"],
            total_rentable_area=stats["total_rentable_area"],
            total_rented_area=stats["total_rented_area"],
            calculated_at=datetime.now(),
        )

    except Exception as e:
        logger.error(f"获取出租率统计失败: {str(e)}")
        import traceback

        logger.error(f"详细错误: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取出租率统计失败: {str(e)}")


@cache_statistics(expire=600)  # 10分钟缓存
@router.get("/occupancy-rate/by-category", response_model=CategoryOccupancyRateResponse)
def get_occupancy_rate_by_category(
    category_field: str = "business_category",
    include_deleted: bool = False,
    use_aggregation: bool = True,
    db: Session = Depends(get_db),
):
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
    try:
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
        filters = {}
        if not include_deleted:
            filters["data_status"] = DataStatus.NORMAL.value

        if use_aggregation:
            # 使用数据库聚合查询
            stats = _calculate_category_occupancy_with_aggregation(
                db, category_field, filters
            )
        else:
            # 使用内存计算
            stats = _calculate_category_occupancy_in_memory(db, category_field, filters)

        logger.info(f"分类出租率计算完成: {category_field}, 共{len(stats)}个分类")

        return CategoryOccupancyRateResponse(
            category_field=category_field, categories=stats, generated_at=datetime.now()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取分类出租率统计失败: {str(e)}")
        import traceback

        logger.error(f"详细错误: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取分类出租率统计失败: {str(e)}")


@cache_statistics(expire=600)  # 10分钟缓存
@router.get("/area-summary", response_model=AreaSummaryResponse)
def get_area_summary(
    include_deleted: bool = False,
    use_aggregation: bool = True,
    db: Session = Depends(get_db),
):
    """
    获取面积汇总统计

    Args:
        include_deleted: 是否包含已删除的资产
        use_aggregation: 是否使用数据库聚合查询（推荐，性能更好）
        db: 数据库会话

    Returns:
        面积汇总统计信息
    """
    try:
        logger.info(f"开始计算面积汇总，聚合模式: {use_aggregation}")

        # 构建筛选条件
        filters = {}
        if not include_deleted:
            filters["data_status"] = DataStatus.NORMAL.value

        if use_aggregation:
            # 使用数据库聚合查询
            summary = _calculate_area_summary_with_aggregation(db, filters)
        else:
            # 使用内存计算
            summary = _calculate_area_summary_in_memory(db, filters)

        logger.info(f"面积汇总计算完成: {summary}")

        return AreaSummaryResponse(
            total_assets=summary["total_assets"],
            total_land_area=summary["total_land_area"],
            total_rentable_area=summary["total_rentable_area"],
            total_rented_area=summary["total_rented_area"],
            total_unrented_area=summary["total_unrented_area"],
            total_non_commercial_area=summary["total_non_commercial_area"],
            assets_with_area_data=summary["assets_with_area_data"],
            overall_occupancy_rate=summary["overall_occupancy_rate"],
            generated_at=datetime.now(),
        )

    except Exception as e:
        logger.error(f"获取面积汇总统计失败: {str(e)}")
        import traceback

        logger.error(f"详细错误: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取面积汇总统计失败: {str(e)}")


@cache_statistics(expire=1800)  # 30分钟缓存
@router.get("/financial-summary", response_model=FinancialSummaryResponse)
def get_financial_summary(include_deleted: bool = False, db: Session = Depends(get_db)):
    """
    获取财务汇总统计

    Args:
        include_deleted: 是否包含已删除的资产
        db: 数据库会话

    Returns:
        财务汇总统计信息
    """
    try:
        # 获取所有资产
        filters = {}
        if not include_deleted:
            filters["data_status"] = DataStatus.NORMAL.value

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
            "assets_with_income_data": 0,
            "assets_with_rent_data": 0,
        }

        for asset in assets:
            if getattr(asset, "annual_income", None):
                summary["total_annual_income"] += to_float(
                    getattr(asset, "annual_income")
                )
                summary["assets_with_income_data"] += 1

            if getattr(asset, "annual_expense", None):
                summary["total_annual_expense"] += to_float(
                    getattr(asset, "annual_expense")
                )

            if getattr(asset, "net_income", None):
                summary["total_net_income"] += to_float(getattr(asset, "net_income"))

            if getattr(asset, "monthly_rent", None):
                summary["total_monthly_rent"] += to_float(
                    getattr(asset, "monthly_rent")
                )
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
        ]:
            if summary[key] is not None:
                summary[key] = round(summary[key], 2)
            else:
                summary[key] = 0.0

        return FinancialSummaryResponse(
            total_assets=summary["total_assets"],
            total_annual_income=summary["total_annual_income"],
            total_annual_expense=summary["total_annual_expense"],
            total_net_income=summary["total_net_income"],
            total_monthly_rent=summary["total_monthly_rent"],
            total_deposit=summary["total_deposit"],
            assets_with_income_data=summary["assets_with_income_data"],
            assets_with_rent_data=summary["assets_with_rent_data"],
            generated_at=datetime.now(),
        )

    except Exception as e:
        logger.error(f"获取财务汇总统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取财务汇总统计失败: {str(e)}")


@router.post("/cache/clear", summary="清除统计数据缓存")
async def clear_statistics_cache():
    """
    清除统计数据缓存
    """
    try:
        cache_mgr = await get_cache_manager()
        cleared_count = await cache_mgr.clear_pattern("statistics:*")

        logger.info(f"用户请求清除统计数据缓存，清除了 {cleared_count} 个缓存条目")

        return {
            "success": True,
            "message": f"统计数据缓存已清除，共清除 {cleared_count} 个缓存条目",
            "data": {"cleared_count": cleared_count},
        }
    except Exception as e:
        logger.error(f"清除统计数据缓存失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"清除缓存失败: {str(e)}")


@router.get("/cache/info", summary="获取缓存信息")
async def get_cache_info():
    """
    获取缓存信息
    """
    try:
        cache_mgr = await get_cache_manager()

        # 简单的缓存状态检查
        cache_status = {
            "cache_type": "Redis" if cache_mgr.redis_client else "In-Memory",
            "cache_enabled": cache_mgr.redis_client is not None,
            "description": "统计数据使用Redis缓存，TTL为30分钟",
        }

        return {"success": True, "message": "获取缓存信息成功", "data": cache_status}
    except Exception as e:
        logger.error(f"获取缓存信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取缓存信息失败: {str(e)}")


@cache_statistics(expire=600)  # 10分钟缓存
@router.get(
    "/dashboard", response_model=DashboardDataResponse, summary="获取仪表板数据"
)
async def get_dashboard_data(db: Session = Depends(get_db)):
    """
    获取仪表板综合数据
    """
    try:
        # 获取基础统计
        total_assets = asset_crud.count(db=db)

        # 计算各类统计
        confirmed_count = asset_crud.count_with_search(
            db=db, filters={"ownership_status": "已确权"}
        )
        unconfirmed_count = asset_crud.count_with_search(
            db=db, filters={"ownership_status": "未确权"}
        )
        partial_count = asset_crud.count_with_search(
            db=db, filters={"ownership_status": "部分确权"}
        )

        commercial_count = asset_crud.count_with_search(
            db=db, filters={"property_nature": "经营性"}
        )
        non_commercial_count = asset_crud.count_with_search(
            db=db, filters={"property_nature": "非经营性"}
        )

        rented_count = asset_crud.count_with_search(
            db=db, filters={"usage_status": "出租"}
        )
        vacant_count = asset_crud.count_with_search(
            db=db, filters={"usage_status": "空置"}
        )
        self_used_count = asset_crud.count_with_search(
            db=db, filters={"usage_status": "自用"}
        )

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

        # 构建分布数据
        ownership_distribution = [
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
                percentage=(partial_count / total_assets * 100)
                if total_assets > 0
                else 0,
            ),
        ]

        property_nature_distribution = [
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

        usage_status_distribution = [
            ChartDataItem(
                name="出租",
                value=rented_count,
                percentage=(rented_count / total_assets * 100)
                if total_assets > 0
                else 0,
            ),
            ChartDataItem(
                name="空置",
                value=vacant_count,
                percentage=(vacant_count / total_assets * 100)
                if total_assets > 0
                else 0,
            ),
            ChartDataItem(
                name="自用",
                value=self_used_count,
                percentage=(self_used_count / total_assets * 100)
                if total_assets > 0
                else 0,
            ),
        ]

        return DashboardDataResponse(
            total_assets=total_assets,
            total_area=round(total_area, 2),
            total_income=round(total_income, 2),
            total_expense=round(total_expense, 2),
            net_income=round(net_income, 2),
            occupancy_rate=round(occupancy_rate, 2),
            ownership_distribution=ownership_distribution,
            property_nature_distribution=property_nature_distribution,
            usage_status_distribution=usage_status_distribution,
            generated_at=datetime.now(),
        )

    except Exception as e:
        logger.error(f"获取仪表板数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取仪表板数据失败: {str(e)}")


@router.get(
    "/ownership-distribution",
    response_model=DistributionResponse,
    summary="获取权属分布统计",
)
async def get_ownership_distribution(db: Session = Depends(get_db)):
    """
    获取按权属状态的资产分布统计
    """
    try:
        total_assets = asset_crud.count(db=db)

        confirmed_count = asset_crud.count_with_search(
            db=db, filters={"ownership_status": "已确权"}
        )
        unconfirmed_count = asset_crud.count_with_search(
            db=db, filters={"ownership_status": "未确权"}
        )
        partial_count = asset_crud.count_with_search(
            db=db, filters={"ownership_status": "部分确权"}
        )

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
                percentage=(partial_count / total_assets * 100)
                if total_assets > 0
                else 0,
            ),
        ]

        return DistributionResponse(
            category="权属状态",
            data=distribution,
            total=total_assets,
            generated_at=datetime.now(),
        )

    except Exception as e:
        logger.error(f"获取权属分布统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取权属分布统计失败: {str(e)}")


@router.get(
    "/property-nature-distribution",
    response_model=DistributionResponse,
    summary="获取物业性质分布统计",
)
async def get_property_nature_distribution(db: Session = Depends(get_db)):
    """
    获取按物业性质的资产分布统计
    """
    try:
        total_assets = asset_crud.count(db=db)

        commercial_count = asset_crud.count_with_search(
            db=db, filters={"property_nature": "经营性"}
        )
        non_commercial_count = asset_crud.count_with_search(
            db=db, filters={"property_nature": "非经营性"}
        )

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
            category="物业性质",
            data=distribution,
            total=total_assets,
            generated_at=datetime.now(),
        )

    except Exception as e:
        logger.error(f"获取物业性质分布统计失败: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"获取物业性质分布统计失败: {str(e)}"
        )


@router.get(
    "/usage-status-distribution",
    response_model=DistributionResponse,
    summary="获取使用状态分布统计",
)
async def get_usage_status_distribution(db: Session = Depends(get_db)):
    """
    获取按使用状态的资产分布统计
    """
    try:
        total_assets = asset_crud.count(db=db)

        rented_count = asset_crud.count_with_search(
            db=db, filters={"usage_status": "出租"}
        )
        vacant_count = asset_crud.count_with_search(
            db=db, filters={"usage_status": "空置"}
        )
        self_used_count = asset_crud.count_with_search(
            db=db, filters={"usage_status": "自用"}
        )

        distribution = [
            ChartDataItem(
                name="出租",
                value=rented_count,
                percentage=(rented_count / total_assets * 100)
                if total_assets > 0
                else 0,
            ),
            ChartDataItem(
                name="空置",
                value=vacant_count,
                percentage=(vacant_count / total_assets * 100)
                if total_assets > 0
                else 0,
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
            category="使用状态",
            data=distribution,
            total=total_assets,
            generated_at=datetime.now(),
        )

    except Exception as e:
        logger.error(f"获取使用状态分布统计失败: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"获取使用状态分布统计失败: {str(e)}"
        )


@router.get("/trend/{metric}", response_model=TrendDataResponse, summary="获取趋势数据")
async def get_trend_data(
    metric: str = Path(..., description="指标名称"),
    period: str = Query(
        "monthly", pattern="^(daily|weekly|monthly|yearly)$", description="时间周期"
    ),
    db: Session = Depends(get_db),
):
    """
    获取指标趋势数据

    Args:
        metric: 指标名称 (occupancy_rate, income, expense等)
        period: 时间周期 (daily, weekly, monthly, yearly)
    """
    try:
        # 这里简化实现，实际项目中可以根据时间周期和指标从历史数据中计算趋势
        # 目前返回模拟数据
        trend_data = []

        if metric == "occupancy_rate":
            # 模拟最近6个月的出租率趋势
            for i in range(6):
                month_value = 75 + (i * 2) + (hash(f"{metric}_{i}") % 10)
                trend_data.append(
                    {
                        "date": f"2024-{i + 1:02d}",
                        "value": round(min(month_value, 95), 1),
                    }
                )
        elif metric == "income":
            # 模拟最近6个月的收入趋势
            base_income = 1000000
            for i in range(6):
                month_income = (
                    base_income + (i * 50000) + (hash(f"{metric}_{i}") % 100000)
                )
                trend_data.append(
                    {"date": f"2024-{i + 1:02d}", "value": round(month_income, 2)}
                )
        else:
            # 默认返回简单的趋势数据
            for i in range(6):
                trend_data.append({"date": f"2024-{i + 1:02d}", "value": 100 + i * 10})

        return TrendDataResponse(
            metric=metric, period=period, data=trend_data, generated_at=datetime.now()
        )

    except Exception as e:
        logger.error(f"获取趋势数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取趋势数据失败: {str(e)}")


@router.get("/occupancy-rate", summary="获取出租率统计")
async def get_occupancy_rate_statistics(
    ownership_status: str | None = Query(None, description="确权状态筛选"),
    property_nature: str | None = Query(None, description="物业性质筛选"),
    usage_status: str | None = Query(None, description="使用状态筛选"),
    business_category: str | None = Query(None, description="业务分类筛选"),
    db: Session = Depends(get_db),
):
    """
    获取出租率统计数据
    """
    try:
        # 构建筛选条件
        filters = {}
        if ownership_status:
            filters["ownership_status"] = ownership_status
        if property_nature:
            filters["property_nature"] = property_nature
        if usage_status:
            filters["usage_status"] = usage_status
        if business_category:
            filters["business_category"] = business_category

        # 计算出租率
        stats = _calculate_occupancy_with_aggregation(db, filters)

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

    except Exception as e:
        logger.error(f"获取出租率统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取出租率统计失败: {str(e)}")


@router.get("/asset-distribution", summary="获取资产分布统计")
async def get_asset_distribution(
    group_by: str = Query("ownership_status", description="分组字段"),
    include_deleted: bool = Query(False, description="是否包含已删除资产"),
    db: Session = Depends(get_db),
):
    """
    获取资产分布统计数据
    """
    try:
        # 验证分组字段
        valid_fields = [
            "ownership_status",
            "property_nature",
            "usage_status",
            "business_category",
            "manager_name",
            "project_name",
        ]

        if group_by not in valid_fields:
            raise HTTPException(
                status_code=400,
                detail=f"无效的分组字段。支持的字段: {', '.join(valid_fields)}",
            )

        # 构建筛选条件
        filters = {}
        if not include_deleted:
            filters["data_status"] = DataStatus.NORMAL.value

        # 获取资产数据
        assets, _ = asset_crud.get_multi_with_search(
            db=db, skip=0, limit=10000, filters=filters
        )

        # 按字段分组统计
        distribution = {}
        total_assets = len(assets)

        for asset in assets:
            group_value = getattr(asset, group_by, None) or "未知"
            if group_value not in distribution:
                distribution[group_value] = 0
            distribution[group_value] += 1

        # 构建响应数据
        distribution_data = [
            {
                "name": key,
                "value": count,
                "percentage": round((count / total_assets * 100), 2)
                if total_assets > 0
                else 0,
            }
            for key, count in distribution.items()
        ]

        return {
            "success": True,
            "data": {
                "group_by": group_by,
                "distribution": distribution_data,
                "total_assets": total_assets,
                "generated_at": datetime.now().isoformat(),
                "filters_applied": filters,
            },
            "message": "资产分布统计数据获取成功",
        }

    except Exception as e:
        logger.error(f"获取资产分布统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取资产分布统计失败: {str(e)}")


@router.get("/area-statistics", summary="获取面积统计")
async def get_area_statistics(
    ownership_status: str | None = Query(None, description="确权状态筛选"),
    property_nature: str | None = Query(None, description="物业性质筛选"),
    usage_status: str | None = Query(None, description="使用状态筛选"),
    include_deleted: bool = Query(False, description="是否包含已删除资产"),
    db: Session = Depends(get_db),
):
    """
    获取面积统计数据
    """
    try:
        # 构建筛选条件
        filters = {}
        if ownership_status:
            filters["ownership_status"] = ownership_status
        if property_nature:
            filters["property_nature"] = property_nature
        if usage_status:
            filters["usage_status"] = usage_status
        if not include_deleted:
            filters["data_status"] = DataStatus.NORMAL.value

        # 计算面积汇总
        summary = _calculate_area_summary_with_aggregation(db, filters)

        return {
            "success": True,
            "data": {
                "total_assets": summary["total_assets"],
                "total_land_area": summary["total_land_area"],
                "total_property_area": summary[
                    "total_land_area"
                ],  # 土地面积作为物业面积
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

    except Exception as e:
        logger.error(f"获取面积统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取面积统计失败: {str(e)}")


@router.get("/comprehensive", summary="获取综合统计")
async def get_comprehensive_statistics(
    ownership_status: str | None = Query(None, description="确权状态筛选"),
    property_nature: str | None = Query(None, description="物业性质筛选"),
    usage_status: str | None = Query(None, description="使用状态筛选"),
    include_deleted: bool = Query(False, description="是否包含已删除资产"),
    db: Session = Depends(get_db),
):
    """
    获取综合统计数据
    """
    try:
        # 构建筛选条件
        filters = {}
        if ownership_status:
            filters["ownership_status"] = ownership_status
        if property_nature:
            filters["property_nature"] = property_nature
        if usage_status:
            filters["usage_status"] = usage_status
        if not include_deleted:
            filters["data_status"] = DataStatus.NORMAL.value

        # 基础统计
        total_assets = asset_crud.count_with_search(db=db, filters=filters)

        if total_assets == 0:
            return {
                "success": False,
                "message": "没有找到符合条件的资产数据",
                "data": None,
            }

        # 获取面积统计
        area_stats = _calculate_area_summary_with_aggregation(db, filters)

        # 获取出租率统计
        occupancy_stats = _calculate_occupancy_with_aggregation(db, filters)

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
        ownership_distribution = {}
        property_nature_distribution = {}
        usage_status_distribution = {}

        for asset in assets:
            # 权属状态分布
            ownership = getattr(asset, "ownership_status", None) or "未知"
            ownership_distribution[ownership] = (
                ownership_distribution.get(ownership, 0) + 1
            )

            # 物业性质分布
            nature = getattr(asset, "property_nature", None) or "未知"
            property_nature_distribution[nature] = (
                property_nature_distribution.get(nature, 0) + 1
            )

            # 使用状态分布
            usage = getattr(asset, "usage_status", None) or "未知"
            usage_status_distribution[usage] = (
                usage_status_distribution.get(usage, 0) + 1
            )

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
                "total_annual_expense": round(
                    financial_stats["total_annual_expense"], 2
                ),
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

    except Exception as e:
        logger.error(f"获取综合统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取综合统计失败: {str(e)}")
