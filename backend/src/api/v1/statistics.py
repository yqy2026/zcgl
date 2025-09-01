"""
统计分析API路由
"""

import logging
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from crud.asset import asset_crud

# 配置日志
logger = logging.getLogger(__name__)

# 创建统计路由器
router = APIRouter()


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
        if ownership_status:
            filters["ownership_status"] = ownership_status
        if property_nature:
            filters["property_nature"] = property_nature
        if usage_status:
            filters["usage_status"] = usage_status
        if ownership_entity:
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


@router.get("/dashboard", summary="获取仪表板数据")
async def get_dashboard_data(
    db: Session = Depends(get_db)
):
    """
    获取仪表板数据
    
    Returns:
        仪表板统计数据
    """
    try:
        logger.info("开始获取仪表板数据")
        
        # 获取基础统计
        basic_stats = await get_basic_statistics(db=db)
        
        if not basic_stats["success"]:
            raise HTTPException(
                status_code=400,
                detail=basic_stats["message"]
            )
        
        logger.info("仪表板数据生成完成")
        
        return {
            "success": True,
            "message": "仪表板数据获取成功",
            "data": {
                "overview": basic_stats["data"],
                "charts": {
                    "ownership_pie": [
                        {"name": "已确权", "value": basic_stats["data"]["ownership_status"]["confirmed"]},
                        {"name": "未确权", "value": basic_stats["data"]["ownership_status"]["unconfirmed"]},
                        {"name": "部分确权", "value": basic_stats["data"]["ownership_status"]["partial"]}
                    ],
                    "nature_pie": [
                        {"name": "经营性", "value": basic_stats["data"]["property_nature"]["commercial"]},
                        {"name": "非经营性", "value": basic_stats["data"]["property_nature"]["non_commercial"]}
                    ],
                    "usage_pie": [
                        {"name": "出租", "value": basic_stats["data"]["usage_status"]["rented"]},
                        {"name": "自用", "value": basic_stats["data"]["usage_status"]["self_used"]},
                        {"name": "空置", "value": basic_stats["data"]["usage_status"]["vacant"]}
                    ]
                }
            }
        }
        
    except Exception as e:
        logger.error(f"获取仪表板数据异常: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取仪表板数据失败: {str(e)}"
        )


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