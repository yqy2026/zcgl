"""
系统监控API路由
提供系统状态、性能指标和健康检查接口
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ...database import get_db
from ...middleware.auth import get_current_user
from ...models.auth import User
from ...services.monitoring import system_monitor

router = APIRouter()

@router.get("/status")
async def get_system_status():
    """
    获取系统状态概览
    """
    return system_monitor.get_system_status()

@router.get("/performance")
async def get_performance_summary(
    hours: int = Query(1, ge=1, le=24, description="时间范围（小时）"),
    current_user: User = Depends(get_current_user)
):
    """
    获取性能摘要

    Args:
        hours: 统计时间范围（1-24小时）
    """
    return system_monitor.get_performance_summary(hours)

@router.get("/health")
async def health_check(
    db: Session = Depends(get_db),
    detailed: bool = Query(False, description="是否返回详细检查信息")
):
    """
    系统健康检查

    Args:
        detailed: 是否返回详细的检查信息
    """
    health_data = system_monitor.get_health_check(db)

    if detailed:
        return health_data
    else:
        # 只返回基本状态
        return {
            "status": health_data["overall"],
            "timestamp": health_data["timestamp"]
        }

@router.get("/database/stats")
async def get_database_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取数据库统计信息
    """
    return system_monitor.get_database_stats(db)

@router.get("/metrics/system")
async def get_system_metrics(
    limit: int = Query(100, ge=1, le=1000, description="返回记录数量限制"),
    current_user: User = Depends(get_current_user)
):
    """
    获取系统指标历史数据

    Args:
        limit: 返回的记录数量
    """
    if not system_monitor.system_metrics_history:
        return {"message": "No system metrics available"}

    # 返回最近的记录
    recent_metrics = list(system_monitor.system_metrics_history)[-limit:]

    return {
        "metrics": [
            {
                "timestamp": m.timestamp.isoformat(),
                "cpu_percent": m.cpu_percent,
                "memory_percent": m.memory_percent,
                "memory_used_mb": m.memory_used // (1024 * 1024),
                "memory_available_mb": m.memory_available // (1024 * 1024),
                "disk_usage_percent": m.disk_usage_percent,
                "active_connections": m.active_connections,
                "database_size_mb": m.database_size // (1024 * 1024),
                "response_time_ms": m.response_time * 1000
            }
            for m in recent_metrics
        ],
        "total_records": len(recent_metrics)
    }

@router.get("/metrics/api")
async def get_api_metrics(
    limit: int = Query(100, ge=1, le=1000, description="返回记录数量限制"),
    endpoint: Optional[str] = Query(None, description="筛选特定端点"),
    current_user: User = Depends(get_current_user)
):
    """
    获取API指标历史数据

    Args:
        limit: 返回的记录数量
        endpoint: 筛选特定端点
    """
    if not system_monitor.api_metrics_history:
        return {"message": "No API metrics available"}

    # 筛选数据
    metrics = system_monitor.api_metrics_history
    if endpoint:
        metrics = [m for m in metrics if endpoint in m.endpoint]

    # 返回最近的记录
    recent_metrics = list(metrics)[-limit:]

    return {
        "metrics": [
            {
                "timestamp": m.timestamp.isoformat(),
                "endpoint": m.endpoint,
                "method": m.method,
                "status_code": m.status_code,
                "response_time_ms": m.response_time * 1000,
                "user_id": m.user_id
            }
            for m in recent_metrics
        ],
        "total_records": len(recent_metrics),
        "endpoint_filter": endpoint
    }

@router.get("/errors")
async def get_error_summary(
    limit: int = Query(10, ge=1, le=50, description="返回错误数量限制"),
    current_user: User = Depends(get_current_user)
):
    """
    获取错误摘要

    Args:
        limit: 返回的错误数量限制
    """
    if not system_monitor.error_counts:
        return {"message": "No errors recorded"}

    # 按错误次数排序
    sorted_errors = sorted(system_monitor.error_counts.items(), key=lambda x: x[1], reverse=True)

    return {
        "top_errors": [
            {
                "endpoint": endpoint,
                "error_count": count
            }
            for endpoint, count in sorted_errors[:limit]
        ],
        "total_error_types": len(sorted_errors)
    }

@router.post("/monitoring/start")
async def start_monitoring(
    interval: int = Query(30, ge=10, le=300, description="监控间隔（秒）"),
    current_user: User = Depends(get_current_user)
):
    """
    启动系统监控

    Args:
        interval: 监控间隔（秒）
    """
    if system_monitor._is_monitoring:
        return {"message": "Monitoring is already running"}

    # 在后台启动监控
    import asyncio
    asyncio.create_task(system_monitor.start_monitoring(interval))

    return {"message": f"Monitoring started with {interval}s interval"}

@router.post("/monitoring/stop")
async def stop_monitoring(
    current_user: User = Depends(get_current_user)
):
    """
    停止系统监控
    """
    if not system_monitor._is_monitoring:
        return {"message": "Monitoring is not running"}

    system_monitor.stop_monitoring()
    return {"message": "Monitoring stopped"}