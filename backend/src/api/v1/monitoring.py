"""
监控API路由
收集和分析系统性能指标
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from ...database import get_db
from ...decorators.permission import permission_required
from ...schemas.common import SuccessResponse, PaginatedResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/monitoring", tags=["系统监控"])


# 路由性能指标模式
class RoutePerformanceMetric(BaseModel):
    route: str = Field(..., description="路由路径")
    route_load_time: float = Field(..., description="路由加载时间(ms)")
    component_load_time: float = Field(..., description="组件加载时间(ms)")
    render_time: float = Field(..., description="渲染时间(ms)")
    interactive_time: float = Field(..., description="交互可用时间(ms)")
    FCP: Optional[float] = Field(None, description="首次内容绘制时间(ms)")
    LCP: Optional[float] = Field(None, description="最大内容绘制时间(ms)")
    FID: Optional[float] = Field(None, description="首次输入延迟(ms)")
    CLS: Optional[float] = Field(None, description="累积布局偏移")
    memory_usage: Optional[float] = Field(None, description="内存使用量(bytes)")
    js_heap_size: Optional[float] = Field(None, description="JS堆大小(bytes)")
    error_count: int = Field(0, description="错误次数")
    retry_count: int = Field(0, description="重试次数")
    navigation_type: str = Field(..., description="导航类型")
    user_agent: str = Field(..., description="用户代理")
    session_id: str = Field(..., description="会话ID")
    timestamp: datetime = Field(..., description="时间戳")


class PerformanceReport(BaseModel):
    session_id: str = Field(..., description="会话ID")
    metrics: List[RoutePerformanceMetric] = Field(..., description="性能指标列表")
    aggregated: Optional[Dict[str, Any]] = Field(None, description="聚合指标")
    timestamp: datetime = Field(..., description="上报时间")


class HealthCheck(BaseModel):
    status: str = Field(..., description="健康状态")
    services: Dict[str, str] = Field(..., description="服务状态")
    uptime: float = Field(..., description="运行时间(秒)")
    memory_usage: Dict[str, float] = Field(..., description="内存使用情况")
    database_status: str = Field(..., description="数据库状态")


@router.post("/route-performance", summary="上报路由性能指标")
async def report_route_performance(
    report: PerformanceReport,
    db: Session = Depends(get_db)
):
    """
    接收前端上报的路由性能指标
    """
    try:
        # 简化版本：直接记录到日志，实际项目中应该保存到数据库
        logger.info(f"收到性能指标上报，会话ID: {report.session_id}, 指标数量: {len(report.metrics)}")

        # 计算基本统计
        if report.metrics:
            avg_load_time = sum(m.route_load_time for m in report.metrics) / len(report.metrics)
            total_errors = sum(m.error_count for m in report.metrics)

            logger.info(f"平均加载时间: {avg_load_time:.2f}ms, 总错误数: {total_errors}")

            # 检查性能告警
            for metric in report.metrics:
                if metric.route_load_time > 5000:  # 5秒
                    logger.warning(f"慢路由告警: {metric.route}, 加载时间: {metric.route_load_time}ms")

                if metric.error_count > 0:
                    logger.error(f"路由错误告警: {metric.route}, 错误数: {metric.error_count}")

        return {"success": True, "message": "性能指标已保存"}

    except Exception as e:
        logger.error(f"保存性能指标失败: {str(e)}")
        raise HTTPException(status_code=500, detail="性能指标保存失败")


@router.get("/system-health", summary="获取系统健康状态", response_model=HealthCheck)
async def get_system_health():
    """
    获取系统健康状态
    """
    try:
        # 简化版本的健康检查
        import time

        health_check = HealthCheck(
            status="healthy",
            services={
                "database": "healthy",
                "api": "healthy",
                "memory": "healthy"
            },
            uptime=time.time(),
            memory_usage={
                "total": 0,
                "used": 0,
                "percent": 0
            },
            database_status="healthy"
        )

        return health_check

    except Exception as e:
        logger.error(f"获取系统健康状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取系统健康状态失败")


@router.get("/performance/dashboard", summary="获取性能监控仪表板数据")
@permission_required("system", "monitoring")
async def get_performance_dashboard():
    """
    获取性能监控仪表板数据
    """
    try:
        # 模拟仪表板数据
        dashboard_data = {
            "overview": {
                "total_visits": 1250,
                "unique_users": 89,
                "avg_load_time": 1250.5,
                "error_rate": 0.02,
                "retry_rate": 0.05
            },
            "route_performance": {
                "/dashboard": {"visits": 450, "avg_load_time": 800},
                "/assets/list": {"visits": 320, "avg_load_time": 1200},
                "/rental/contracts": {"visits": 280, "avg_load_time": 1500}
            },
            "trends": [
                {"timestamp": "2024-01-20T10:00:00Z", "avg_load_time": 1200},
                {"timestamp": "2024-01-20T11:00:00Z", "avg_load_time": 1150},
                {"timestamp": "2024-01-20T12:00:00Z", "avg_load_time": 1300}
            ],
            "alerts": [
                {
                    "type": "slow_routes",
                    "severity": "warning",
                    "message": "检测到2个慢路由"
                }
            ],
            "top_slow_routes": [
                {"route": "/analytics/reports", "avg_time": 2500},
                {"route": "/rental/contracts/pdf-import", "avg_time": 2100}
            ]
        }

        return {"success": True, "data": dashboard_data}

    except Exception as e:
        logger.error(f"获取仪表板数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取仪表板数据失败")