"""
统计分析API路由
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ...database import get_db
from ...crud.asset import asset_crud
from ...services.asset_calculator import OccupancyRateCalculator
from ...schemas.asset import DataStatus
from ...schemas.statistics import (
    BasicStatisticsResponse,
    OccupancyRateStatsResponse,
    CategoryOccupancyRateResponse,
    AreaSummaryResponse,
    FinancialSummaryResponse,
    DashboardDataResponse,
    DistributionResponse,
    TrendDataResponse,
    ChartDataItem
)
from ...utils.cache_manager import cache_statistics, get_cache_manager

# 配置日志
logger = logging.getLogger(__name__)

# 创建统计路由器
router = APIRouter()


# 将可能为 None/Decimal/str 的值安全转换为 float
def to_float(value: Any) -> float:
    try:
        if value is None:
            return 0.0
        # 避免 Decimal 与 float 混算
        return float(value)
    except Exception:
        return 0.0


@router.get("/basic", response_model=BasicStatisticsResponse, summary="获取基础统计数据")
async def get_basic_statistics(
    ownership_status: Optional[str] = Query(None, description="确权状态筛选"),
    property_nature: Optional[str] = Query(None, description="物业性质筛选"),
    usage_status: Optional[str] = Query(None, description="使用状态筛选"),
    ownership_entity: Optional[str] = Query(None, description="权属方筛选"),
    db: Session = Depends(get_db)
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
                "data": None
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
                "partial": partial_count
            },
            "property_nature": {
                "commercial": commercial_count,
                "non_commercial": non_commercial_count
            },
            "usage_status": {
                "rented": rented_count,
                "self_used": self_used_count,
                "vacant": vacant_count
            },
            "generated_at": datetime.now().isoformat(),
            "filters_applied": filters
        }
        
        logger.info(f"基础统计数据获取完成，包含 {total_assets} 条资产")
        
        return BasicStatisticsResponse(
            total_assets=total_assets,
            ownership_status=basic_stats["ownership_status"],
            property_nature=basic_stats["property_nature"],
            usage_status=basic_stats["usage_status"],
            generated_at=basic_stats["generated_at"],
            filters_applied=basic_stats["filters_applied"]
        )
        
    except Exception as e:
        logger.error(f"获取基础统计数据异常: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取基础统计数据失败: {str(e)}"
        )


# 仪表板端点已移除，请使用以下替代端点：
# - /api/v1/statistics/basic - 基础统计
# - /api/v1/statistics/summary - 统计摘要  
# - /api/v1/statistics/area-summary - 面积汇总
# - /api/v1/statistics/financial-summary - 财务汇总


@cache_statistics(expire=1800)  # 30分钟缓存
@router.get("/summary", response_model=BasicStatisticsResponse, summary="获取统计摘要")
async def get_statistics_summary(
    db: Session = Depends(get_db)
):
    """
    获取统计摘要信息
    """
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
                "partial": partial_count
            },
            property_nature={
                "commercial": commercial_count,
                "non_commercial": non_commercial_count
            },
            usage_status={
                "rented": rented_count,
                "self_used": self_used_count,
                "vacant": vacant_count
            },
            generated_at=datetime.now(),
            filters_applied={}
        )

    except Exception as e:
        logger.error(f"获取统计摘要异常: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取统计摘要失败: {str(e)}")


@cache_statistics(expire=1800)  # 30分钟缓存
@router.get("/occupancy-rate/overall", response_model=OccupancyRateStatsResponse)
def get_overall_occupancy_rate(
    include_deleted: bool = False,
    db: Session = Depends(get_db)
):
    """
    获取整体出租率统计

    Args:
        include_deleted: 是否包含已删除的资产
        db: 数据库会话

    Returns:
        整体出租率统计信息
    """
    try:
        # 获取所有资产
        filters = {}
        if not include_deleted:
            filters['data_status'] = DataStatus.NORMAL.value

        assets, _ = asset_crud.get_multi_with_search(
            db=db,
            skip=0,
            limit=10000,  # 获取所有资产
            filters=filters
        )

        # 计算整体出租率
        stats = OccupancyRateCalculator.calculate_overall_occupancy_rate(assets)

        return OccupancyRateStatsResponse(
            total_assets=len(assets),
            total_rentable_area=stats["total_rentable_area"],
            total_rented_area=stats["total_rented_area"],
            overall_occupancy_rate=stats["overall_occupancy_rate"],
            unrented_area=stats["unrented_area"],
            assets_with_area_data=stats["assets_with_area_data"],
            generated_at=datetime.now()
        )

    except Exception as e:
        logger.error(f"获取出租率统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取出租率统计失败: {str(e)}")


@router.get("/occupancy-rate/by-category", response_model=CategoryOccupancyRateResponse)
def get_occupancy_rate_by_category(
    category_field: str = "business_category",
    include_deleted: bool = False,
    db: Session = Depends(get_db)
):
    """
    按类别获取出租率统计
    
    Args:
        category_field: 分类字段名
        include_deleted: 是否包含已删除的资产
        db: 数据库会话
        
    Returns:
        按类别的出租率统计信息
    """
    try:
        # 验证分类字段
        valid_fields = [
            'business_category', 'property_nature', 'usage_status', 
            'ownership_status', 'manager_name', 'business_model',
            'operation_status', 'project_name'
        ]
        
        if category_field not in valid_fields:
            raise HTTPException(
                status_code=400, 
                detail=f"无效的分类字段。支持的字段: {', '.join(valid_fields)}"
            )
        
        # 获取所有资产
        filters = {}
        if not include_deleted:
            filters['data_status'] = DataStatus.NORMAL.value
            
        assets, _ = asset_crud.get_multi_with_search(
            db=db,
            skip=0,
            limit=10000,  # 获取所有资产
            filters=filters
        )
        
        # 按类别计算出租率
        stats = OccupancyRateCalculator.calculate_occupancy_by_category(assets, category_field)
        
        return CategoryOccupancyRateResponse(
            category_field=category_field,
            categories=stats,
            generated_at=datetime.now()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取分类出租率统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取分类出租率统计失败: {str(e)}")


@cache_statistics(expire=1800)  # 30分钟缓存
@router.get("/area-summary", response_model=AreaSummaryResponse)
def get_area_summary(
    include_deleted: bool = False,
    db: Session = Depends(get_db)
):
    """
    获取面积汇总统计

    Args:
        include_deleted: 是否包含已删除的资产
        db: 数据库会话

    Returns:
        面积汇总统计信息
    """
    try:
        # 获取所有资产
        filters = {}
        if not include_deleted:
            filters['data_status'] = DataStatus.NORMAL.value

        assets, _ = asset_crud.get_multi_with_search(
            db=db,
            skip=0,
            limit=10000,  # 获取所有资产
            filters=filters
        )

        # 计算面积汇总
        summary = {
            'total_assets': len(assets),
            'total_land_area': 0.0,
            'total_rentable_area': 0.0,
            'total_rented_area': 0.0,
            'total_unrented_area': 0.0,
            'total_non_commercial_area': 0.0,
            'assets_with_area_data': 0
        }

        for asset in assets:
            if getattr(asset, 'land_area', None):
                summary['total_land_area'] += to_float(getattr(asset, 'land_area'))
                summary['assets_with_area_data'] += 1

            if getattr(asset, 'rentable_area', None):
                summary['total_rentable_area'] += to_float(getattr(asset, 'rentable_area'))

            if getattr(asset, 'rented_area', None):
                summary['total_rented_area'] += to_float(getattr(asset, 'rented_area'))

            if getattr(asset, 'unrented_area', None):
                summary['total_unrented_area'] += to_float(getattr(asset, 'unrented_area'))

            if getattr(asset, 'non_commercial_area', None):
                summary['total_non_commercial_area'] += to_float(getattr(asset, 'non_commercial_area'))

        # 格式化数据，保留2位小数
        for key in ['total_land_area', 'total_rentable_area', 'total_rented_area', 'total_unrented_area', 'total_non_commercial_area']:
            if summary[key] is not None:
                summary[key] = round(summary[key], 2)
            else:
                summary[key] = 0.0

        # 计算整体出租率
        if summary['total_rentable_area'] > 0:
            overall_occupancy_rate = (summary['total_rented_area'] / summary['total_rentable_area']) * 100
            summary['overall_occupancy_rate'] = round(overall_occupancy_rate, 2)
        else:
            summary['overall_occupancy_rate'] = 0.0

        return AreaSummaryResponse(
            total_assets=summary['total_assets'],
            total_land_area=summary['total_land_area'],
            total_rentable_area=summary['total_rentable_area'],
            total_rented_area=summary['total_rented_area'],
            total_unrented_area=summary['total_unrented_area'],
            total_non_commercial_area=summary['total_non_commercial_area'],
            assets_with_area_data=summary['assets_with_area_data'],
            overall_occupancy_rate=summary['overall_occupancy_rate'],
            generated_at=datetime.now()
        )

    except Exception as e:
        logger.error(f"获取面积汇总统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取面积汇总统计失败: {str(e)}")


@cache_statistics(expire=1800)  # 30分钟缓存
@router.get("/financial-summary", response_model=FinancialSummaryResponse)
def get_financial_summary(
    include_deleted: bool = False,
    db: Session = Depends(get_db)
):
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
            filters['data_status'] = DataStatus.NORMAL.value

        assets, _ = asset_crud.get_multi_with_search(
            db=db,
            skip=0,
            limit=10000,  # 获取所有资产
            filters=filters
        )

        # 计算财务汇总
        summary = {
            'total_assets': len(assets),
            'total_annual_income': 0.0,
            'total_annual_expense': 0.0,
            'total_net_income': 0.0,
            'total_monthly_rent': 0.0,
            'total_deposit': 0.0,
            'assets_with_income_data': 0,
            'assets_with_rent_data': 0
        }

        for asset in assets:
            if getattr(asset, 'annual_income', None):
                summary['total_annual_income'] += to_float(getattr(asset, 'annual_income'))
                summary['assets_with_income_data'] += 1

            if getattr(asset, 'annual_expense', None):
                summary['total_annual_expense'] += to_float(getattr(asset, 'annual_expense'))

            if getattr(asset, 'net_income', None):
                summary['total_net_income'] += to_float(getattr(asset, 'net_income'))

            if getattr(asset, 'monthly_rent', None):
                summary['total_monthly_rent'] += to_float(getattr(asset, 'monthly_rent'))
                summary['assets_with_rent_data'] += 1

            if getattr(asset, 'deposit', None):
                summary['total_deposit'] += to_float(getattr(asset, 'deposit'))

        # 格式化数据，保留2位小数
        for key in ['total_annual_income', 'total_annual_expense', 'total_net_income', 'total_monthly_rent', 'total_deposit']:
            if summary[key] is not None:
                summary[key] = round(summary[key], 2)
            else:
                summary[key] = 0.0

        return FinancialSummaryResponse(
            total_assets=summary['total_assets'],
            total_annual_income=summary['total_annual_income'],
            total_annual_expense=summary['total_annual_expense'],
            total_net_income=summary['total_net_income'],
            total_monthly_rent=summary['total_monthly_rent'],
            total_deposit=summary['total_deposit'],
            assets_with_income_data=summary['assets_with_income_data'],
            assets_with_rent_data=summary['assets_with_rent_data'],
            generated_at=datetime.now()
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
            "data": {
                "cleared_count": cleared_count
            }
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
            "description": "统计数据使用Redis缓存，TTL为30分钟"
        }

        return {
            "success": True,
            "message": "获取缓存信息成功",
            "data": cache_status
        }
    except Exception as e:
        logger.error(f"获取缓存信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取缓存信息失败: {str(e)}")


@cache_statistics(expire=600)  # 10分钟缓存
@router.get("/dashboard", response_model=DashboardDataResponse, summary="获取仪表板数据")
async def get_dashboard_data(db: Session = Depends(get_db)):
    """
    获取仪表板综合数据
    """
    try:
        # 获取基础统计
        total_assets = asset_crud.count(db=db)

        # 计算各类统计
        confirmed_count = asset_crud.count_with_search(db=db, filters={"ownership_status": "已确权"})
        unconfirmed_count = asset_crud.count_with_search(db=db, filters={"ownership_status": "未确权"})
        partial_count = asset_crud.count_with_search(db=db, filters={"ownership_status": "部分确权"})

        commercial_count = asset_crud.count_with_search(db=db, filters={"property_nature": "经营性"})
        non_commercial_count = asset_crud.count_with_search(db=db, filters={"property_nature": "非经营性"})

        rented_count = asset_crud.count_with_search(db=db, filters={"usage_status": "出租"})
        vacant_count = asset_crud.count_with_search(db=db, filters={"usage_status": "空置"})
        self_used_count = asset_crud.count_with_search(db=db, filters={"usage_status": "自用"})

        # 获取面积和财务数据
        assets, _ = asset_crud.get_multi_with_search(db=db, skip=0, limit=10000)

        total_area = 0.0
        total_income = 0.0
        total_expense = 0.0
        total_rentable_area = 0.0
        total_rented_area = 0.0

        for asset in assets:
            if getattr(asset, 'land_area', None):
                total_area += to_float(getattr(asset, 'land_area'))
            if getattr(asset, 'annual_income', None):
                total_income += to_float(getattr(asset, 'annual_income'))
            if getattr(asset, 'annual_expense', None):
                total_expense += to_float(getattr(asset, 'annual_expense'))
            if getattr(asset, 'rentable_area', None):
                total_rentable_area += to_float(getattr(asset, 'rentable_area'))
            if getattr(asset, 'rented_area', None):
                total_rented_area += to_float(getattr(asset, 'rented_area'))

        net_income = total_income - total_expense
        occupancy_rate = (total_rented_area / total_rentable_area * 100) if total_rentable_area > 0 else 0.0

        # 构建分布数据
        ownership_distribution = [
            ChartDataItem(name="已确权", value=confirmed_count, percentage=(confirmed_count/total_assets*100) if total_assets > 0 else 0),
            ChartDataItem(name="未确权", value=unconfirmed_count, percentage=(unconfirmed_count/total_assets*100) if total_assets > 0 else 0),
            ChartDataItem(name="部分确权", value=partial_count, percentage=(partial_count/total_assets*100) if total_assets > 0 else 0)
        ]

        property_nature_distribution = [
            ChartDataItem(name="经营性", value=commercial_count, percentage=(commercial_count/total_assets*100) if total_assets > 0 else 0),
            ChartDataItem(name="非经营性", value=non_commercial_count, percentage=(non_commercial_count/total_assets*100) if total_assets > 0 else 0)
        ]

        usage_status_distribution = [
            ChartDataItem(name="出租", value=rented_count, percentage=(rented_count/total_assets*100) if total_assets > 0 else 0),
            ChartDataItem(name="空置", value=vacant_count, percentage=(vacant_count/total_assets*100) if total_assets > 0 else 0),
            ChartDataItem(name="自用", value=self_used_count, percentage=(self_used_count/total_assets*100) if total_assets > 0 else 0)
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
            generated_at=datetime.now()
        )

    except Exception as e:
        logger.error(f"获取仪表板数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取仪表板数据失败: {str(e)}")


@router.get("/ownership-distribution", response_model=DistributionResponse, summary="获取权属分布统计")
async def get_ownership_distribution(db: Session = Depends(get_db)):
    """
    获取按权属状态的资产分布统计
    """
    try:
        total_assets = asset_crud.count(db=db)

        confirmed_count = asset_crud.count_with_search(db=db, filters={"ownership_status": "已确权"})
        unconfirmed_count = asset_crud.count_with_search(db=db, filters={"ownership_status": "未确权"})
        partial_count = asset_crud.count_with_search(db=db, filters={"ownership_status": "部分确权"})

        distribution = [
            ChartDataItem(name="已确权", value=confirmed_count, percentage=(confirmed_count/total_assets*100) if total_assets > 0 else 0),
            ChartDataItem(name="未确权", value=unconfirmed_count, percentage=(unconfirmed_count/total_assets*100) if total_assets > 0 else 0),
            ChartDataItem(name="部分确权", value=partial_count, percentage=(partial_count/total_assets*100) if total_assets > 0 else 0)
        ]

        return DistributionResponse(
            category="权属状态",
            data=distribution,
            total=total_assets,
            generated_at=datetime.now()
        )

    except Exception as e:
        logger.error(f"获取权属分布统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取权属分布统计失败: {str(e)}")


@router.get("/property-nature-distribution", response_model=DistributionResponse, summary="获取物业性质分布统计")
async def get_property_nature_distribution(db: Session = Depends(get_db)):
    """
    获取按物业性质的资产分布统计
    """
    try:
        total_assets = asset_crud.count(db=db)

        commercial_count = asset_crud.count_with_search(db=db, filters={"property_nature": "经营性"})
        non_commercial_count = asset_crud.count_with_search(db=db, filters={"property_nature": "非经营性"})

        distribution = [
            ChartDataItem(name="经营性", value=commercial_count, percentage=(commercial_count/total_assets*100) if total_assets > 0 else 0),
            ChartDataItem(name="非经营性", value=non_commercial_count, percentage=(non_commercial_count/total_assets*100) if total_assets > 0 else 0)
        ]

        return DistributionResponse(
            category="物业性质",
            data=distribution,
            total=total_assets,
            generated_at=datetime.now()
        )

    except Exception as e:
        logger.error(f"获取物业性质分布统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取物业性质分布统计失败: {str(e)}")


@router.get("/usage-status-distribution", response_model=DistributionResponse, summary="获取使用状态分布统计")
async def get_usage_status_distribution(db: Session = Depends(get_db)):
    """
    获取按使用状态的资产分布统计
    """
    try:
        total_assets = asset_crud.count(db=db)

        rented_count = asset_crud.count_with_search(db=db, filters={"usage_status": "出租"})
        vacant_count = asset_crud.count_with_search(db=db, filters={"usage_status": "空置"})
        self_used_count = asset_crud.count_with_search(db=db, filters={"usage_status": "自用"})

        distribution = [
            ChartDataItem(name="出租", value=rented_count, percentage=(rented_count/total_assets*100) if total_assets > 0 else 0),
            ChartDataItem(name="空置", value=vacant_count, percentage=(vacant_count/total_assets*100) if total_assets > 0 else 0),
            ChartDataItem(name="自用", value=self_used_count, percentage=(self_used_count/total_assets*100) if total_assets > 0 else 0)
        ]

        return DistributionResponse(
            category="使用状态",
            data=distribution,
            total=total_assets,
            generated_at=datetime.now()
        )

    except Exception as e:
        logger.error(f"获取使用状态分布统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取使用状态分布统计失败: {str(e)}")


@router.get("/trend/{metric}", response_model=TrendDataResponse, summary="获取趋势数据")
async def get_trend_data(
    metric: str = Query(..., description="指标名称"),
    period: str = Query("monthly", regex="^(daily|weekly|monthly|yearly)$", description="时间周期"),
    db: Session = Depends(get_db)
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
                trend_data.append({
                    "date": f"2024-{i+1:02d}",
                    "value": round(min(month_value, 95), 1)
                })
        elif metric == "income":
            # 模拟最近6个月的收入趋势
            base_income = 1000000
            for i in range(6):
                month_income = base_income + (i * 50000) + (hash(f"{metric}_{i}") % 100000)
                trend_data.append({
                    "date": f"2024-{i+1:02d}",
                    "value": round(month_income, 2)
                })
        else:
            # 默认返回简单的趋势数据
            for i in range(6):
                trend_data.append({
                    "date": f"2024-{i+1:02d}",
                    "value": 100 + i * 10
                })

        return TrendDataResponse(
            metric=metric,
            period=period,
            data=trend_data,
            generated_at=datetime.now()
        )

    except Exception as e:
        logger.error(f"获取趋势数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取趋势数据失败: {str(e)}")