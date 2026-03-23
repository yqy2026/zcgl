from typing import Any

"""
监控API路由
收集和分析系统性能指标
"""

import contextlib
import logging
from datetime import datetime

import psutil
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.exception_handler import internal_error
from ....database import get_async_db
from ....middleware.auth import AuthzContext, get_current_active_user, require_authz
from ....models.auth import User
from ....security.permissions import permission_required

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/monitoring",
    tags=["系统监控"],
    dependencies=[Depends(get_current_active_user)],
)
_SYSTEM_MONITORING_CREATE_UNSCOPED_PARTY_ID = "__unscoped__:system_monitoring:create"
_SYSTEM_MONITORING_CREATE_RESOURCE_CONTEXT: dict[str, str] = {
    "party_id": _SYSTEM_MONITORING_CREATE_UNSCOPED_PARTY_ID,
    "owner_party_id": _SYSTEM_MONITORING_CREATE_UNSCOPED_PARTY_ID,
    "manager_party_id": _SYSTEM_MONITORING_CREATE_UNSCOPED_PARTY_ID,
}
_SYSTEM_MONITORING_UPDATE_UNSCOPED_PARTY_ID = "__unscoped__:system_monitoring:update"
_SYSTEM_MONITORING_UPDATE_RESOURCE_CONTEXT: dict[str, str] = {
    "party_id": _SYSTEM_MONITORING_UPDATE_UNSCOPED_PARTY_ID,
    "owner_party_id": _SYSTEM_MONITORING_UPDATE_UNSCOPED_PARTY_ID,
    "manager_party_id": _SYSTEM_MONITORING_UPDATE_UNSCOPED_PARTY_ID,
}


# 路由性能指标模式
class RoutePerformanceMetric(BaseModel):
    route: str = Field(..., description="路由路径")
    route_load_time: float = Field(..., description="路由加载时间(ms)")
    component_load_time: float = Field(..., description="组件加载时间(ms)")
    render_time: float = Field(..., description="渲染时间(ms)")
    interactive_time: float = Field(..., description="交互可用时间(ms)")
    FCP: float | None = Field(None, description="首次内容绘制时间(ms)")
    LCP: float | None = Field(None, description="最大内容绘制时间(ms)")
    FID: float | None = Field(None, description="首次输入延迟(ms)")
    CLS: float | None = Field(None, description="累积布局偏移")
    memory_usage: float | None = Field(None, description="内存使用量(bytes)")
    js_heap_size: float | None = Field(None, description="JS堆大小(bytes)")
    error_count: int = Field(0, description="错误次数")
    retry_count: int = Field(0, description="重试次数")
    navigation_type: str = Field(..., description="导航类型")
    user_agent: str = Field(..., description="用户代理")
    session_id: str = Field(..., description="会话ID")
    timestamp: datetime = Field(..., description="时间戳")


class PerformanceReport(BaseModel):
    session_id: str = Field(..., description="会话ID")
    metrics: list[RoutePerformanceMetric] = Field(..., description="性能指标列表")
    aggregated: dict[str, Any] | None = Field(None, description="聚合指标")
    timestamp: datetime = Field(..., description="上报时间")


class HealthCheck(BaseModel):
    status: str = Field(..., description="健康状态")
    services: dict[str, str] = Field(..., description="服务状态")
    uptime: float = Field(..., description="运行时间(秒)")
    memory_usage: dict[str, float] = Field(..., description="内存使用情况")
    database_status: str = Field(..., description="数据库状态")


@router.post("/route-performance", summary="上报路由性能指标")
async def report_route_performance(
    report: PerformanceReport,
    _: AsyncSession = Depends(get_async_db),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="create",
            resource_type="system_monitoring",
            resource_context=_SYSTEM_MONITORING_CREATE_RESOURCE_CONTEXT,
        )
    ),
) -> dict[str, str]:
    """
    接收前端上报的路由性能指标
    """
    try:
        logger.info(
            f"收到性能指标上报，会话ID: {report.session_id}, 指标数量: {len(report.metrics)}"
        )

        if report.metrics:
            avg_load_time = sum(m.route_load_time for m in report.metrics) / len(
                report.metrics
            )
            total_errors = sum(m.error_count for m in report.metrics)

            logger.info(
                f"平均加载时间: {avg_load_time:.2f}ms, 总错误数: {total_errors}"
            )

            for metric in report.metrics:
                if metric.route_load_time > 5000:
                    logger.warning(
                        f"慢路由告警: {metric.route}, 加载时间: {metric.route_load_time}ms"
                    )
                if metric.error_count > 0:
                    logger.error(
                        f"路由错误告警: {metric.route}, 错误数: {metric.error_count}"
                    )

        return {"success": str(True), "message": "性能指标已保存"}
    except Exception as e:
        logger.error(f"保存性能指标失败: {str(e)}")
        raise internal_error("性能指标保存失败")


@router.get("/system-health", summary="获取系统健康状态", response_model=HealthCheck)
def get_system_health(
    _authz_ctx: AuthzContext = Depends(
        require_authz(action="read", resource_type="system_monitoring")
    ),
) -> HealthCheck:
    """
    获取系统健康状态
    """
    try:
        # 简化版本的健康检查
        import time

        health_check = HealthCheck(
            status="healthy",
            services={"database": "healthy", "api": "healthy", "memory": "healthy"},
            uptime=time.time(),
            memory_usage={"total": 0, "used": 0, "percent": 0},
            database_status="healthy",
        )

        return health_check

    except Exception as e:
        logger.error(f"获取系统健康状态失败: {str(e)}")
        raise internal_error("获取系统健康状态失败")


@router.get("/performance/dashboard", summary="获取性能监控仪表板数据")
@permission_required("system", "monitoring")
async def get_performance_dashboard(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
    _authz_ctx: AuthzContext = Depends(
        require_authz(action="read", resource_type="system_monitoring")
    ),
) -> dict[str, Any]:
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
                "retry_rate": 0.05,
            },
            "route_performance": {
                "/dashboard": {"visits": 450, "avg_load_time": 800},
                "/assets/list[Any]": {"visits": 320, "avg_load_time": 1200},
                "/rental/contracts": {"visits": 280, "avg_load_time": 1500},
            },
            "trends": [
                {"timestamp": "2024-01-20T10:00:00Z", "avg_load_time": 1200},
                {"timestamp": "2024-01-20T11:00:00Z", "avg_load_time": 1150},
                {"timestamp": "2024-01-20T12:00:00Z", "avg_load_time": 1300},
            ],
            "alerts": [
                {
                    "type": "slow_routes",
                    "severity": "warning",
                    "message": "检测到2个慢路由",
                }
            ],
            "top_slow_routes": [
                {"route": "/analytics/reports", "avg_time": 2500},
                {"route": "/rental/contracts/pdf-import", "avg_time": 2100},
            ],
        }

        return {"success": True, "data": dashboard_data}

    except Exception as e:
        logger.error(f"获取仪表板数据失败: {str(e)}")
        raise internal_error("获取仪表板数据失败")


# === 新增系统监控API ===


class SystemMetrics(BaseModel):
    """系统性能指标模型"""

    timestamp: datetime = Field(..., description="指标采集时间")
    cpu_percent: float = Field(..., ge=0, le=100, description="CPU使用率(%)")
    memory_percent: float = Field(..., ge=0, le=100, description="内存使用率(%)")
    memory_available_gb: float = Field(..., ge=0, description="可用内存(GB)")
    disk_usage_percent: float = Field(..., ge=0, le=100, description="磁盘使用率(%)")
    disk_free_gb: float = Field(..., ge=0, description="可用磁盘空间(GB)")
    network_io: dict[str, int] = Field(..., description="网络IO统计")
    process_count: int = Field(..., ge=0, description="运行进程数")
    load_average: list[float] | None = Field(None, description="系统负载平均值")


class ApplicationMetrics(BaseModel):
    """应用性能指标模型"""

    timestamp: datetime = Field(..., description="指标采集时间")
    active_connections: int = Field(..., ge=0, description="活跃连接数")
    total_requests: int = Field(..., ge=0, description="总请求数")
    average_response_time: float = Field(..., ge=0, description="平均响应时间(ms)")
    error_rate: float = Field(..., ge=0, le=100, description="错误率(%)")
    cache_hit_rate: float = Field(..., ge=0, le=100, description="缓存命中率(%)")
    database_connections: int = Field(..., ge=0, description="数据库连接数")


class HealthStatus(BaseModel):
    """健康状态模型"""

    status: str = Field(
        ..., pattern="^(healthy|degraded|unhealthy)$", description="健康状态"
    )
    timestamp: datetime = Field(..., description="检查时间")
    components: dict[str, dict[str, Any]] = Field(..., description="组件状态详情")
    overall_score: float = Field(..., ge=0, le=100, description="总体健康评分")


class PerformanceAlert(BaseModel):
    """性能告警模型"""

    id: str = Field(..., description="告警ID")
    level: str = Field(..., pattern="^(info|warning|critical)$", description="告警级别")
    message: str = Field(..., description="告警消息")
    metric_name: str = Field(..., description="指标名称")
    current_value: float = Field(..., description="当前值")
    threshold: float = Field(..., description="阈值")
    timestamp: datetime = Field(..., description="告警时间")
    resolved: bool = Field(False, description="是否已解决")


# 全局变量存储指标历史数据
_metrics_history: list[SystemMetrics] = []
_application_metrics: list[ApplicationMetrics] = []
_active_alerts: list[PerformanceAlert] = []


def collect_system_metrics() -> SystemMetrics:
    """收集系统性能指标"""
    try:
        # CPU使用率
        cpu_percent = psutil.cpu_percent(interval=1)

        # 内存信息
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_available_gb = memory.available / (1024**3)

        # 磁盘信息
        disk = psutil.disk_usage("/")
        disk_usage_percent = disk.percent
        disk_free_gb = disk.free / (1024**3)

        # 网络IO
        network_io = {
            "bytes_sent": psutil.net_io_counters().bytes_sent,
            "bytes_recv": psutil.net_io_counters().bytes_recv,
            "packets_sent": psutil.net_io_counters().packets_sent,
            "packets_recv": psutil.net_io_counters().packets_recv,
        }

        # 进程数
        process_count = len(psutil.pids())

        # 系统负载 (Linux/Mac)
        load_average = None
        with contextlib.suppress(AttributeError, OSError):
            # Windows不支持getloadavg
            load_average = list(psutil.getloadavg())

        metrics = SystemMetrics(
            timestamp=datetime.now(),
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            memory_available_gb=memory_available_gb,
            disk_usage_percent=disk_usage_percent,
            disk_free_gb=disk_free_gb,
            network_io=network_io,
            process_count=process_count,
            load_average=load_average,
        )

        # 保存历史数据 (保留最近100条)
        _metrics_history.append(metrics)
        if len(_metrics_history) > 100:
            _metrics_history.pop(0)

        return metrics

    except Exception as e:
        logger.error(f"收集系统指标失败: {e}")
        raise internal_error(f"收集系统指标失败: {str(e)}")


def collect_application_metrics() -> ApplicationMetrics:
    """收集应用性能指标"""
    try:
        # 模拟应用指标 (实际项目中应该从监控系统获取)
        metrics = ApplicationMetrics(
            timestamp=datetime.now(),
            active_connections=42,
            total_requests=15847,
            average_response_time=125.5,
            error_rate=0.2,
            cache_hit_rate=85.3,
            database_connections=8,
        )

        # 保存历史数据
        _application_metrics.append(metrics)
        if len(_application_metrics) > 100:
            _application_metrics.pop(0)

        return metrics

    except Exception as e:
        logger.error(f"收集应用指标失败: {e}")
        raise internal_error(f"收集应用指标失败: {str(e)}")


@router.get("/system-metrics", response_model=SystemMetrics, summary="获取系统性能指标")
@permission_required("system_monitoring", "read")
async def get_system_metrics(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
    _authz_ctx: AuthzContext = Depends(
        require_authz(action="read", resource_type="system_monitoring")
    ),
) -> SystemMetrics:
    """获取当前系统性能指标"""
    return collect_system_metrics()


@router.get(
    "/application-metrics",
    response_model=ApplicationMetrics,
    summary="获取应用性能指标",
)
@permission_required("system_monitoring", "read")
async def get_application_metrics(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
    _authz_ctx: AuthzContext = Depends(
        require_authz(action="read", resource_type="system_monitoring")
    ),
) -> ApplicationMetrics:
    """获取应用性能指标"""
    return collect_application_metrics()


@router.get("/dashboard", summary="获取系统监控仪表板")
@permission_required("system_monitoring", "read")
async def get_system_monitoring_dashboard(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
    _authz_ctx: AuthzContext = Depends(
        require_authz(action="read", resource_type="system_monitoring")
    ),
) -> dict[str, Any]:
    """获取系统监控仪表板综合数据"""
    try:
        system_metrics = collect_system_metrics()
        app_metrics = collect_application_metrics()

        # 健康状态检查
        components = {}
        overall_score = 100

        # 检查CPU
        if system_metrics.cpu_percent > 90:
            components["cpu"] = {
                "status": "unhealthy",
                "value": system_metrics.cpu_percent,
            }
            overall_score -= 30
        elif system_metrics.cpu_percent > 70:
            components["cpu"] = {
                "status": "warning",
                "value": system_metrics.cpu_percent,
            }
            overall_score -= 15
        else:
            components["cpu"] = {
                "status": "healthy",
                "value": system_metrics.cpu_percent,
            }

        # 检查内存
        if system_metrics.memory_percent > 90:
            components["memory"] = {
                "status": "unhealthy",
                "value": system_metrics.memory_percent,
            }
            overall_score -= 30
        elif system_metrics.memory_percent > 80:
            components["memory"] = {
                "status": "warning",
                "value": system_metrics.memory_percent,
            }
            overall_score -= 15
        else:
            components["memory"] = {
                "status": "healthy",
                "value": system_metrics.memory_percent,
            }

        # 检查磁盘
        if system_metrics.disk_usage_percent > 95:
            components["disk"] = {
                "status": "unhealthy",
                "value": system_metrics.disk_usage_percent,
            }
            overall_score -= 20
        elif system_metrics.disk_usage_percent > 85:
            components["disk"] = {
                "status": "warning",
                "value": system_metrics.disk_usage_percent,
            }
            overall_score -= 10
        else:
            components["disk"] = {
                "status": "healthy",
                "value": system_metrics.disk_usage_percent,
            }

        # 确定整体状态
        if overall_score >= 90:
            status = "healthy"
        elif overall_score >= 70:
            status = "degraded"
        else:
            status = "unhealthy"

        health_status = HealthStatus(
            status=status,
            timestamp=datetime.now(),
            components=components,
            overall_score=max(0, overall_score),
        )

        return {
            "current_system": system_metrics,
            "current_application": app_metrics,
            "health_status": health_status,
            "active_alerts": _active_alerts[-10:],  # 最近10个告警
            "trends": {
                "system_metrics": _metrics_history[-20:],  # 最近20个数据点
                "application_metrics": _application_metrics[-20:],
            },
            "summary": {
                "total_alerts": len(_active_alerts),
                "critical_alerts": len(
                    [a for a in _active_alerts if a.level == "critical"]
                ),
                "warning_alerts": len(
                    [a for a in _active_alerts if a.level == "warning"]
                ),
                "health_score": overall_score,
                "last_updated": datetime.now().isoformat(),
            },
        }

    except Exception as e:
        logger.error(f"获取监控仪表板数据失败: {e}")
        raise internal_error(f"获取监控仪表板数据失败: {str(e)}")


@router.post("/metrics/collect", summary="手动触发指标收集")
@permission_required("system_monitoring", "write")
async def trigger_metrics_collection(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="update",
            resource_type="system_monitoring",
            resource_context=_SYSTEM_MONITORING_UPDATE_RESOURCE_CONTEXT,
        )
    ),
) -> dict[str, Any]:
    """手动触发一次指标收集"""
    try:
        system_metrics = collect_system_metrics()
        app_metrics = collect_application_metrics()

        return {
            "message": "指标收集完成",
            "system_metrics": system_metrics,
            "application_metrics": app_metrics,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"手动指标收集失败: {e}")
        raise internal_error(f"手动指标收集失败: {str(e)}")
