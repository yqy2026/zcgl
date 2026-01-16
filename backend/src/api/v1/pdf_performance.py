"""
PDF性能监控API路由模块

从 pdf_import_unified.py 提取的性能监控相关端点

职责：
- 实时性能数据查询
- 性能报告生成
- 系统健康状态监控

端点：
- GET /performance/realtime: 获取实时性能监控数据
- GET /performance/report: 获取性能报告
- GET /performance/health: 获取系统健康状态
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query

from ...core.performance import PerformanceMonitor
from .dependencies import get_performance_monitor

logger = logging.getLogger(__name__)

router = APIRouter(tags=["PDF性能监控"])


@router.get("/performance/realtime")
async def get_realtime_performance(
    perf_monitor: PerformanceMonitor = Depends(get_performance_monitor),
) -> dict[str, Any]:
    """
    获取实时性能监控数据

    返回：
    - 包含实时性能数据的字典：
        - enabled: 是否启用监控
        - threshold_ms: 慢查询阈值
        - stats: 统计数据
        - timestamp: 时间戳
    """
    try:
        performance_data = await perf_monitor.get_real_time_performance()
        return {
            "success": True,
            "data": performance_data,
            "message": "实时性能数据获取成功",
        }
    except Exception as e:
        logger.error(f"获取实时性能数据失败: {str(e)}")
        return {"success": False, "error": str(e), "data": None}


@router.get("/performance/report")
async def get_performance_report(
    hours: int = Query(default=24, ge=1, le=168, description="报告时间范围（小时）"),
    perf_monitor: PerformanceMonitor = Depends(get_performance_monitor),
) -> dict[str, Any]:
    """
    获取性能报告

    参数：
    - hours: 报告时间范围（1-168小时，默认24小时）

    返回：
    - 包含性能报告的字典：
        - hours: 报告时间范围
        - stats: 统计数据
        - report_generated_at: 报告生成时间
    """
    try:
        report = await perf_monitor.get_performance_report(hours)
        return {"success": True, "data": report, "message": "性能报告生成成功"}
    except Exception as e:
        logger.error(f"获取性能报告失败: {str(e)}")
        return {"success": False, "error": str(e), "data": None}


@router.get("/performance/health")
async def get_system_health(
    perf_monitor: PerformanceMonitor = Depends(get_performance_monitor),
) -> dict[str, Any]:
    """
    获取系统健康状态

    返回：
    - 包含系统健康状态的字典：
        - status: 健康状态 (healthy/degraded)
        - monitoring_enabled: 监控是否启用
        - total_queries: 总查询数
        - slow_queries: 慢查询数
    """
    try:
        # 获取性能监控器健康状态
        health_data = await perf_monitor.get_health_status()

        # 尝试获取增强的健康监控（如果可用）
        try:
            from ...services.core.enhanced_error_handler import monitor_processing_health

            enhanced_health = await monitor_processing_health()
            # 合并健康数据
            health_data.update({"enhanced_monitoring": enhanced_health})
        except ImportError:
            # 增强健康监控不可用，使用基础数据
            pass

        return {"success": True, "data": health_data, "message": "系统健康状态获取成功"}
    except Exception as e:
        logger.error(f"获取系统健康状态失败: {str(e)}")
        return {"success": False, "error": str(e), "data": None}
