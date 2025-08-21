"""
出租率自动计算API端点
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime

from src.database import get_db
from src.services.occupancy_calculator import OccupancyService
from src.schemas.statistics import StatisticsRequest, StatisticsResponse

router = APIRouter(prefix="/occupancy", tags=["occupancy"])
logger = logging.getLogger(__name__)


@router.get("/calculate", response_model=StatisticsResponse)
async def calculate_comprehensive_occupancy(
    property_nature: Optional[str] = Query(None, description="物业性质筛选"),
    ownership_entity: Optional[str] = Query(None, description="权属方筛选"),
    usage_status: Optional[str] = Query(None, description="使用状态筛选"),
    ownership_status: Optional[str] = Query(None, description="确权状态筛选"),
    db: Session = Depends(get_db)
) -> StatisticsResponse:
    """
    计算综合出租率分析
    
    Args:
        property_nature: 物业性质筛选
        ownership_entity: 权属方筛选
        usage_status: 使用状态筛选
        ownership_status: 确权状态筛选
        db: 数据库会话
    
    Returns:
        综合出租率分析结果
    """
    try:
        # 构建筛选条件
        filters = {}
        if property_nature:
            filters["property_nature"] = property_nature
        if ownership_entity:
            filters["ownership_entity"] = ownership_entity
        if usage_status:
            filters["usage_status"] = usage_status
        if ownership_status:
            filters["ownership_status"] = ownership_status
        
        logger.info(f"开始计算综合出租率分析，筛选条件: {filters}")
        
        occupancy_service = OccupancyService()
        result = await occupancy_service.calculate_comprehensive_occupancy(
            filters=filters,
            db=db
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=400,
                detail=result["message"]
            )
        
        logger.info("综合出租率分析计算完成")
        
        return StatisticsResponse(
            success=True,
            message=result["message"],
            data=result["data"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"计算综合出租率分析异常: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"计算综合出租率分析失败: {str(e)}"
        )


@router.get("/rate", response_model=StatisticsResponse)
async def get_occupancy_rate(
    property_nature: Optional[str] = Query(None, description="物业性质筛选"),
    ownership_entity: Optional[str] = Query(None, description="权属方筛选"),
    db: Session = Depends(get_db)
) -> StatisticsResponse:
    """
    获取出租率统计
    
    Args:
        property_nature: 物业性质筛选
        ownership_entity: 权属方筛选
        db: 数据库会话
    
    Returns:
        出租率统计数据
    """
    try:
        # 构建筛选条件
        filters = {}
        if property_nature:
            filters["property_nature"] = property_nature
        if ownership_entity:
            filters["ownership_entity"] = ownership_entity
        
        logger.info(f"开始获取出租率统计，筛选条件: {filters}")
        
        occupancy_service = OccupancyService()
        
        # 获取资产数据
        assets = await occupancy_service._get_filtered_assets(filters, db)
        
        if not assets:
            return StatisticsResponse(
                success=False,
                message="没有找到符合条件的资产数据",
                data=None
            )
        
        # 计算出租率统计
        overall_stats = occupancy_service.calculator.calculate_overall_occupancy_rate(assets)
        by_nature = occupancy_service.calculator.calculate_occupancy_by_category(assets, "property_nature")
        by_entity = occupancy_service.calculator.calculate_occupancy_by_category(assets, "ownership_entity")
        distribution = occupancy_service.calculator.analyze_occupancy_distribution(assets)
        
        # 组装结果
        result_data = {
            "overall_statistics": overall_stats,
            "by_property_nature": by_nature,
            "by_ownership_entity": by_entity,
            "distribution_analysis": distribution,
            "generated_at": datetime.now().isoformat(),
            "filters_applied": filters,
            "data_count": len(assets)
        }
        
        logger.info(f"出租率统计获取完成，包含 {len(assets)} 条资产")
        
        return StatisticsResponse(
            success=True,
            message=f"成功获取 {len(assets)} 条资产的出租率统计",
            data=result_data
        )
        
    except Exception as e:
        logger.error(f"获取出租率统计异常: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取出租率统计失败: {str(e)}"
        )


@router.get("/trend", response_model=StatisticsResponse)
async def get_occupancy_trend(
    months: int = Query(12, description="分析月数", ge=1, le=24),
    property_nature: Optional[str] = Query(None, description="物业性质筛选"),
    ownership_entity: Optional[str] = Query(None, description="权属方筛选"),
    db: Session = Depends(get_db)
) -> StatisticsResponse:
    """
    获取出租率趋势分析
    
    Args:
        months: 分析月数
        property_nature: 物业性质筛选
        ownership_entity: 权属方筛选
        db: 数据库会话
    
    Returns:
        出租率趋势分析数据
    """
    try:
        # 构建筛选条件
        filters = {}
        if property_nature:
            filters["property_nature"] = property_nature
        if ownership_entity:
            filters["ownership_entity"] = ownership_entity
        
        logger.info(f"开始获取出租率趋势分析，筛选条件: {filters}, 分析月数: {months}")
        
        occupancy_service = OccupancyService()
        
        # 获取资产数据
        assets = await occupancy_service._get_filtered_assets(filters, db)
        
        if not assets:
            return StatisticsResponse(
                success=False,
                message="没有找到符合条件的资产数据",
                data=None
            )
        
        # 分析月度趋势
        monthly_trend = occupancy_service.trend_analyzer.analyze_monthly_trend(assets, months)
        
        # 生成未来预测
        predictions = occupancy_service.trend_analyzer.predict_future_occupancy(
            monthly_trend["monthly_data"], 3
        )
        
        # 组装结果
        result_data = {
            "monthly_trend": monthly_trend,
            "future_predictions": predictions,
            "analysis_period": f"{months}个月",
            "generated_at": datetime.now().isoformat(),
            "filters_applied": filters,
            "data_count": len(assets)
        }
        
        logger.info(f"出租率趋势分析完成，包含 {len(assets)} 条资产")
        
        return StatisticsResponse(
            success=True,
            message=f"成功获取 {len(assets)} 条资产的出租率趋势分析",
            data=result_data
        )
        
    except Exception as e:
        logger.error(f"获取出租率趋势分析异常: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取出租率趋势分析失败: {str(e)}"
        )


@router.post("/update", response_model=StatisticsResponse)
async def update_occupancy_rates(
    background_tasks: BackgroundTasks,
    asset_ids: Optional[List[str]] = Query(None, description="要更新的资产ID列表"),
    db: Session = Depends(get_db)
) -> StatisticsResponse:
    """
    更新资产出租率字段
    
    Args:
        background_tasks: 后台任务
        asset_ids: 要更新的资产ID列表，None表示更新所有
        db: 数据库会话
    
    Returns:
        更新结果
    """
    try:
        logger.info(f"开始更新资产出租率，资产ID: {asset_ids}")
        
        occupancy_service = OccupancyService()
        result = await occupancy_service.update_asset_occupancy_rates(
            asset_ids=asset_ids,
            db=db
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=400,
                detail=result["message"]
            )
        
        logger.info(f"资产出租率更新完成，更新了 {result['updated_count']} 个资产")
        
        return StatisticsResponse(
            success=True,
            message=result["message"],
            data={
                "updated_count": result["updated_count"],
                "total_assets": result["total_assets"],
                "updated_at": datetime.now().isoformat()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新资产出租率异常: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"更新资产出租率失败: {str(e)}"
        )


@router.get("/insights", response_model=StatisticsResponse)
async def get_occupancy_insights(
    property_nature: Optional[str] = Query(None, description="物业性质筛选"),
    ownership_entity: Optional[str] = Query(None, description="权属方筛选"),
    db: Session = Depends(get_db)
) -> StatisticsResponse:
    """
    获取出租率洞察分析
    
    Args:
        property_nature: 物业性质筛选
        ownership_entity: 权属方筛选
        db: 数据库会话
    
    Returns:
        出租率洞察分析
    """
    try:
        # 构建筛选条件
        filters = {}
        if property_nature:
            filters["property_nature"] = property_nature
        if ownership_entity:
            filters["ownership_entity"] = ownership_entity
        
        logger.info(f"开始获取出租率洞察分析，筛选条件: {filters}")
        
        occupancy_service = OccupancyService()
        result = await occupancy_service.get_occupancy_insights(
            filters=filters,
            db=db
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=400,
                detail=result["message"]
            )
        
        logger.info("出租率洞察分析获取完成")
        
        return StatisticsResponse(
            success=True,
            message=result["message"],
            data=result["data"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取出租率洞察分析异常: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取出租率洞察分析失败: {str(e)}"
        )


@router.get("/individual/{asset_id}")
async def calculate_individual_occupancy(
    asset_id: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    计算单个资产的出租率
    
    Args:
        asset_id: 资产ID
        db: 数据库会话
    
    Returns:
        单个资产出租率信息
    """
    try:
        logger.info(f"开始计算单个资产出租率，资产ID: {asset_id}")
        
        occupancy_service = OccupancyService()
        
        # 获取资产
        asset = occupancy_service.asset_crud.get(db, id=asset_id)
        if not asset:
            raise HTTPException(
                status_code=404,
                detail="资产不存在"
            )
        
        # 计算出租率
        if asset.rentable_area and asset.rentable_area > 0:
            occupancy_rate = occupancy_service.calculator.calculate_individual_occupancy_rate(
                asset.rentable_area, asset.rented_area or 0.0
            )
            
            result_data = {
                "asset_id": asset_id,
                "property_name": asset.property_name,
                "rentable_area": asset.rentable_area,
                "rented_area": asset.rented_area or 0.0,
                "unrented_area": (asset.rentable_area or 0.0) - (asset.rented_area or 0.0),
                "occupancy_rate": occupancy_rate,
                "occupancy_status": (
                    "满租" if occupancy_rate >= 100 else
                    "高出租率" if occupancy_rate >= 80 else
                    "中等出租率" if occupancy_rate >= 50 else
                    "低出租率" if occupancy_rate >= 20 else
                    "极低出租率"
                ),
                "calculated_at": datetime.now().isoformat()
            }
        else:
            result_data = {
                "asset_id": asset_id,
                "property_name": asset.property_name,
                "rentable_area": 0.0,
                "rented_area": 0.0,
                "unrented_area": 0.0,
                "occupancy_rate": 0.0,
                "occupancy_status": "无可出租面积",
                "calculated_at": datetime.now().isoformat()
            }
        
        logger.info(f"单个资产出租率计算完成，出租率: {result_data['occupancy_rate']}%")
        
        return {
            "success": True,
            "message": "成功计算单个资产出租率",
            "data": result_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"计算单个资产出租率异常: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"计算单个资产出租率失败: {str(e)}"
        )


@router.get("/comparison")
async def compare_occupancy_rates(
    compare_by: str = Query("property_nature", description="对比维度"),
    property_nature: Optional[str] = Query(None, description="物业性质筛选"),
    ownership_entity: Optional[str] = Query(None, description="权属方筛选"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    对比不同维度的出租率
    
    Args:
        compare_by: 对比维度（property_nature, ownership_entity, usage_status）
        property_nature: 物业性质筛选
        ownership_entity: 权属方筛选
        db: 数据库会话
    
    Returns:
        出租率对比分析
    """
    try:
        # 验证对比维度
        valid_dimensions = ["property_nature", "ownership_entity", "usage_status"]
        if compare_by not in valid_dimensions:
            raise HTTPException(
                status_code=400,
                detail=f"无效的对比维度，支持的维度: {valid_dimensions}"
            )
        
        # 构建筛选条件
        filters = {}
        if property_nature:
            filters["property_nature"] = property_nature
        if ownership_entity:
            filters["ownership_entity"] = ownership_entity
        
        logger.info(f"开始对比出租率，对比维度: {compare_by}, 筛选条件: {filters}")
        
        occupancy_service = OccupancyService()
        
        # 获取资产数据
        assets = await occupancy_service._get_filtered_assets(filters, db)
        
        if not assets:
            raise HTTPException(
                status_code=400,
                detail="没有找到符合条件的资产数据"
            )
        
        # 按维度计算出租率
        comparison_data = occupancy_service.calculator.calculate_occupancy_by_category(
            assets, compare_by
        )
        
        # 生成对比分析
        categories = list(comparison_data.keys())
        if len(categories) < 2:
            return {
                "success": False,
                "message": f"按 {compare_by} 分类的数据不足，无法进行对比分析",
                "data": None
            }
        
        # 找出最高和最低出租率
        best_category = max(comparison_data.items(), key=lambda x: x[1]["overall_rate"])
        worst_category = min(comparison_data.items(), key=lambda x: x[1]["overall_rate"])
        
        # 计算平均出租率
        avg_rate = sum([data["overall_rate"] for data in comparison_data.values()]) / len(comparison_data)
        
        # 生成对比图表数据
        chart_data = []
        for category, data in comparison_data.items():
            chart_data.append({
                "category": category,
                "occupancy_rate": data["overall_rate"],
                "total_rentable_area": data["total_rentable_area"],
                "total_rented_area": data["total_rented_area"],
                "asset_count": data["asset_count"]
            })
        
        # 按出租率排序
        chart_data.sort(key=lambda x: x["occupancy_rate"], reverse=True)
        
        result_data = {
            "comparison_dimension": compare_by,
            "comparison_data": comparison_data,
            "chart_data": chart_data,
            "summary": {
                "categories_count": len(categories),
                "best_performer": {
                    "category": best_category[0],
                    "rate": best_category[1]["overall_rate"]
                },
                "worst_performer": {
                    "category": worst_category[0],
                    "rate": worst_category[1]["overall_rate"]
                },
                "average_rate": round(avg_rate, 2),
                "rate_difference": round(best_category[1]["overall_rate"] - worst_category[1]["overall_rate"], 2)
            },
            "generated_at": datetime.now().isoformat(),
            "filters_applied": filters,
            "data_count": len(assets)
        }
        
        logger.info(f"出租率对比分析完成，对比了 {len(categories)} 个分类")
        
        return {
            "success": True,
            "message": f"成功完成按 {compare_by} 的出租率对比分析",
            "data": result_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"出租率对比分析异常: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"出租率对比分析失败: {str(e)}"
        )