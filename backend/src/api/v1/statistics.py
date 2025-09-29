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


@router.get("/basic", summary="获取基础统计数据")
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
        
        return {
            "success": True,
            "message": f"成功获取 {total_assets} 条资产的基础统计数据",
            "data": basic_stats
        }
        
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


@router.get("/summary", summary="获取统计摘要")
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
        
        return {
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
            }
        }
        
    except Exception as e:
        logger.error(f"获取统计摘要异常: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取统计摘要失败: {str(e)}")


@router.get("/occupancy-rate/overall", response_model=Dict[str, Any])
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
        
        return {
            "success": True,
            "data": stats
        }
        
    except Exception as e:
        logger.error(f"获取出租率统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取出租率统计失败: {str(e)}")


@router.get("/occupancy-rate/by-category", response_model=Dict[str, Any])
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
        
        return {
            "success": True,
            "data": {
                "category_field": category_field,
                "categories": stats
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取分类出租率统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取分类出租率统计失败: {str(e)}")


@router.get("/area-summary", response_model=Dict[str, Any])
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
        
        return {
            "success": True,
            "data": summary
        }
        
    except Exception as e:
        logger.error(f"获取面积汇总统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取面积汇总统计失败: {str(e)}")


@router.get("/financial-summary", response_model=Dict[str, Any])
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
        
        return {
            "success": True,
            "data": summary
        }
        
    except Exception as e:
        logger.error(f"获取财务汇总统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取财务汇总统计失败: {str(e)}")