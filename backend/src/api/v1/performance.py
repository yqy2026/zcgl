"""
性能优化API端点
"""

from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from services.performance_service import PerformanceService

router = APIRouter()


@router.get("/analyze", response_model=Dict[str, Any])
def analyze_database_performance(db: Session = Depends(get_db)):
    """分析数据库性能"""
    try:
        service = PerformanceService(db)
        return service.analyze_query_performance("SELECT * FROM assets LIMIT 10")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"性能分析失败: {str(e)}")


@router.post("/optimize", response_model=Dict[str, Any])
def optimize_database(db: Session = Depends(get_db)):
    """优化数据库性能"""
    try:
        service = PerformanceService(db)
        return service.optimize_database()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据库优化失�? {str(e)}")


@router.get("/statistics", response_model=Dict[str, Any])
def get_performance_statistics(db: Session = Depends(get_db)):
    """获取性能统计信息"""
    try:
        service = PerformanceService(db)
        return service.get_asset_statistics_optimized()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


@router.post("/indexes", response_model=Dict[str, Any])
def create_performance_indexes(db: Session = Depends(get_db)):
    """创建性能优化索引"""
    try:
        service = PerformanceService(db)
        return service.create_performance_indexes()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建索引失败: {str(e)}")
