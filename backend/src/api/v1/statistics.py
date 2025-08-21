"""
数据统计和报表API端点
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
import logging
from datetime import datetime

from src.database import get_db
from src.services.statistics import ReportService
from src.schemas.statistics import (
    StatisticsRequest,
    StatisticsResponse,
    DashboardResponse,
    ReportResponse
)

router = APIRouter(prefix="/statistics", tags=["statistics"])
logger = logging.getLogger(__name__)


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard_data(
    db: Session = Depends(get_db)
) -> DashboardResponse:
    """
    获取仪表板数据
    
    Returns:
        仪表板关键指标和图表数据
    """
    try:
        logger.info("开始生成仪表板数据")
        
        report_service = ReportService()
        result = report_service.generate_dashboard_data(db=db)
        
        if not result["success"]:
            raise HTTPException(
                status_code=400,
                detail=result["message"]
            )
        
        logger.info("仪表板数据生成完成")
        
        return DashboardResponse(
            success=True,
            message=result["message"],
            data=result["data"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取仪表板数据异常: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取仪表板数据失败: {str(e)}"
        )


@router.post("/report", response_model=ReportResponse)
def generate_comprehensive_report(
    request: StatisticsRequest,
    db: Session = Depends(get_db)
) -> ReportResponse:
    """
    生成综合统计报表
    
    Args:
        request: 统计请求参数
        db: 数据库会话
    
    Returns:
        综合统计报表数据
    """
    try:
        logger.info(f"开始生成综合报表，筛选条件: {request.filters}")
        
        report_service = ReportService()
        result = report_service.generate_comprehensive_report(
            filters=request.filters,
            db=db
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=400,
                detail=result["message"]
            )
        
        logger.info("综合报表生成完成")
        
        return ReportResponse(
            success=True,
            message=result["message"],
            data=result["data"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成综合报表异常: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"生成综合报表失败: {str(e)}"
        )


@router.get("/basic", response_model=StatisticsResponse)
def get_basic_statistics(
    ownership_status: Optional[str] = Query(None, description="确权状态筛选"),
    property_nature: Optional[str] = Query(None, description="物业性质筛选"),
    usage_status: Optional[str] = Query(None, description="使用状态筛选"),
    ownership_entity: Optional[str] = Query(None, description="权属方筛选"),
    db: Session = Depends(get_db)
) -> StatisticsResponse:
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
        
        report_service = ReportService()
        
        # 获取资产数据
        assets = report_service._get_filtered_assets(filters, db)
        
        if not assets:
            return StatisticsResponse(
                success=False,
                message="没有找到符合条件的资产数据",
                data=None
            )
        
        # 计算基础统计
        basic_stats = report_service.analyzer.calculate_basic_statistics(assets)
        
        # 添加生成时间和筛选条件
        basic_stats["generated_at"] = datetime.now().isoformat()
        basic_stats["filters_applied"] = filters
        basic_stats["data_count"] = len(assets)
        
        logger.info(f"基础统计数据获取完成，包含 {len(assets)} 条资产")
        
        return StatisticsResponse(
            success=True,
            message=f"成功获取 {len(assets)} 条资产的基础统计数据",
            data=basic_stats
        )
        
    except Exception as e:
        logger.error(f"获取基础统计数据异常: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取基础统计数据失败: {str(e)}"
        )


@router.get("/distribution/ownership", response_model=StatisticsResponse)
def get_ownership_distribution(
    ownership_entity: Optional[str] = Query(None, description="权属方筛选"),
    property_nature: Optional[str] = Query(None, description="物业性质筛选"),
    db: Session = Depends(get_db)
) -> StatisticsResponse:
    """
    获取确权状态分布统计
    
    Args:
        ownership_entity: 权属方筛选
        property_nature: 物业性质筛选
        db: 数据库会话
    
    Returns:
        确权状态分布数据
    """
    try:
        # 构建筛选条件
        filters = {}
        if ownership_entity:
            filters["ownership_entity"] = ownership_entity
        if property_nature:
            filters["property_nature"] = property_nature
        
        logger.info(f"开始获取确权状态分布，筛选条件: {filters}")
        
        report_service = ReportService()
        assets = report_service._get_filtered_assets(filters, db)
        
        if not assets:
            return StatisticsResponse(
                success=False,
                message="没有找到符合条件的资产数据",
                data=None
            )
        
        # 分析确权状态分布
        distribution = report_service.analyzer.analyze_ownership_distribution(assets)
        
        # 添加元数据
        distribution["generated_at"] = datetime.now().isoformat()
        distribution["filters_applied"] = filters
        distribution["data_count"] = len(assets)
        
        logger.info(f"确权状态分布获取完成，包含 {len(assets)} 条资产")
        
        return StatisticsResponse(
            success=True,
            message=f"成功获取 {len(assets)} 条资产的确权状态分布",
            data=distribution
        )
        
    except Exception as e:
        logger.error(f"获取确权状态分布异常: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取确权状态分布失败: {str(e)}"
        )


@router.get("/distribution/nature", response_model=StatisticsResponse)
def get_property_nature_distribution(
    ownership_status: Optional[str] = Query(None, description="确权状态筛选"),
    ownership_entity: Optional[str] = Query(None, description="权属方筛选"),
    db: Session = Depends(get_db)
) -> StatisticsResponse:
    """
    获取物业性质分布统计
    
    Args:
        ownership_status: 确权状态筛选
        ownership_entity: 权属方筛选
        db: 数据库会话
    
    Returns:
        物业性质分布数据
    """
    try:
        # 构建筛选条件
        filters = {}
        if ownership_status:
            filters["ownership_status"] = ownership_status
        if ownership_entity:
            filters["ownership_entity"] = ownership_entity
        
        logger.info(f"开始获取物业性质分布，筛选条件: {filters}")
        
        report_service = ReportService()
        assets = report_service._get_filtered_assets(filters, db)
        
        if not assets:
            return StatisticsResponse(
                success=False,
                message="没有找到符合条件的资产数据",
                data=None
            )
        
        # 分析物业性质分布
        distribution = report_service.analyzer.analyze_property_nature_distribution(assets)
        
        # 添加元数据
        distribution["generated_at"] = datetime.now().isoformat()
        distribution["filters_applied"] = filters
        distribution["data_count"] = len(assets)
        
        logger.info(f"物业性质分布获取完成，包含 {len(assets)} 条资产")
        
        return StatisticsResponse(
            success=True,
            message=f"成功获取 {len(assets)} 条资产的物业性质分布",
            data=distribution
        )
        
    except Exception as e:
        logger.error(f"获取物业性质分布异常: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取物业性质分布失败: {str(e)}"
        )


@router.get("/distribution/usage", response_model=StatisticsResponse)
def get_usage_status_distribution(
    property_nature: Optional[str] = Query(None, description="物业性质筛选"),
    ownership_entity: Optional[str] = Query(None, description="权属方筛选"),
    db: Session = Depends(get_db)
) -> StatisticsResponse:
    """
    获取使用状态分布统计
    
    Args:
        property_nature: 物业性质筛选
        ownership_entity: 权属方筛选
        db: 数据库会话
    
    Returns:
        使用状态分布数据
    """
    try:
        # 构建筛选条件
        filters = {}
        if property_nature:
            filters["property_nature"] = property_nature
        if ownership_entity:
            filters["ownership_entity"] = ownership_entity
        
        logger.info(f"开始获取使用状态分布，筛选条件: {filters}")
        
        report_service = ReportService()
        assets = report_service._get_filtered_assets(filters, db)
        
        if not assets:
            return StatisticsResponse(
                success=False,
                message="没有找到符合条件的资产数据",
                data=None
            )
        
        # 分析使用状态分布
        distribution = report_service.analyzer.analyze_usage_status_distribution(assets)
        
        # 添加元数据
        distribution["generated_at"] = datetime.now().isoformat()
        distribution["filters_applied"] = filters
        distribution["data_count"] = len(assets)
        
        logger.info(f"使用状态分布获取完成，包含 {len(assets)} 条资产")
        
        return StatisticsResponse(
            success=True,
            message=f"成功获取 {len(assets)} 条资产的使用状态分布",
            data=distribution
        )
        
    except Exception as e:
        logger.error(f"获取使用状态分布异常: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取使用状态分布失败: {str(e)}"
        )


@router.get("/occupancy", response_model=StatisticsResponse)
def get_occupancy_analysis(
    property_nature: Optional[str] = Query(None, description="物业性质筛选"),
    ownership_entity: Optional[str] = Query(None, description="权属方筛选"),
    db: Session = Depends(get_db)
) -> StatisticsResponse:
    """
    获取出租率分析
    
    Args:
        property_nature: 物业性质筛选
        ownership_entity: 权属方筛选
        db: 数据库会话
    
    Returns:
        出租率分析数据
    """
    try:
        # 构建筛选条件
        filters = {}
        if property_nature:
            filters["property_nature"] = property_nature
        if ownership_entity:
            filters["ownership_entity"] = ownership_entity
        
        logger.info(f"开始获取出租率分析，筛选条件: {filters}")
        
        report_service = ReportService()
        assets = report_service._get_filtered_assets(filters, db)
        
        if not assets:
            return StatisticsResponse(
                success=False,
                message="没有找到符合条件的资产数据",
                data=None
            )
        
        # 生成出租率分析
        occupancy_analysis = report_service.analyzer.generate_occupancy_analysis(assets)
        
        # 添加元数据
        occupancy_analysis["generated_at"] = datetime.now().isoformat()
        occupancy_analysis["filters_applied"] = filters
        occupancy_analysis["data_count"] = len(assets)
        
        logger.info(f"出租率分析获取完成，包含 {len(assets)} 条资产")
        
        return StatisticsResponse(
            success=True,
            message=f"成功获取 {len(assets)} 条资产的出租率分析",
            data=occupancy_analysis
        )
        
    except Exception as e:
        logger.error(f"获取出租率分析异常: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取出租率分析失败: {str(e)}"
        )


@router.get("/area-distribution", response_model=StatisticsResponse)
def get_area_distribution(
    property_nature: Optional[str] = Query(None, description="物业性质筛选"),
    ownership_entity: Optional[str] = Query(None, description="权属方筛选"),
    db: Session = Depends(get_db)
) -> StatisticsResponse:
    """
    获取面积分布分析
    
    Args:
        property_nature: 物业性质筛选
        ownership_entity: 权属方筛选
        db: 数据库会话
    
    Returns:
        面积分布分析数据
    """
    try:
        # 构建筛选条件
        filters = {}
        if property_nature:
            filters["property_nature"] = property_nature
        if ownership_entity:
            filters["ownership_entity"] = ownership_entity
        
        logger.info(f"开始获取面积分布分析，筛选条件: {filters}")
        
        report_service = ReportService()
        assets = report_service._get_filtered_assets(filters, db)
        
        if not assets:
            return StatisticsResponse(
                success=False,
                message="没有找到符合条件的资产数据",
                data=None
            )
        
        # 分析面积分布
        area_distribution = report_service.analyzer.analyze_area_distribution(assets)
        
        # 添加元数据
        area_distribution["generated_at"] = datetime.now().isoformat()
        area_distribution["filters_applied"] = filters
        area_distribution["data_count"] = len(assets)
        
        logger.info(f"面积分布分析获取完成，包含 {len(assets)} 条资产")
        
        return StatisticsResponse(
            success=True,
            message=f"成功获取 {len(assets)} 条资产的面积分布分析",
            data=area_distribution
        )
        
    except Exception as e:
        logger.error(f"获取面积分布分析异常: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取面积分布分析失败: {str(e)}"
        )