"""
系统监控端点模块
"""

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, Query

from ....constants.message_constants import ErrorIDs
from ....core.exception_handler import ConfigurationError, internal_error, not_found
from .collectors import (
    check_performance_alerts,
    collect_application_metrics,
    collect_system_metrics,
    get_active_alerts,
    get_application_metrics_history,
    get_metrics_history,
)
from .health import calculate_overall_health_score, check_component_health
from .models import ApplicationMetrics, HealthStatus, PerformanceAlert, SystemMetrics

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ....models.auth import User

# 关键依赖导入 - 使用快速失败策略
try:
    from ....middleware.auth import require_permission
    from ....models.auth import User
except ImportError as e:
    logger.critical(
        "无法导入系统监控关键依赖",
        extra={
            "error_id": ErrorIDs.System.RESOURCE_EXHAUSTED,
            "import_error": str(e),
            "module": "system_monitoring",
        },
    )
    raise ConfigurationError(
        "系统监控模块缺少必要依赖，无法启动。\n"
        "这表明应用程序安装不完整。请运行: poetry install 或 pip install -e .\n"
        f"导入错误详情: {e}",
        config_key="system_monitoring",
    )


router = APIRouter()


@router.get("/system-metrics", response_model=SystemMetrics, summary="获取系统性能指标")
def get_system_metrics(
    current_user: User = Depends(require_permission("system_monitoring", "read")),
) -> SystemMetrics:
    """获取当前系统性能指标"""
    return collect_system_metrics()


@router.get(
    "/application-metrics",
    response_model=ApplicationMetrics,
    summary="获取应用性能指标",
)
def get_application_metrics(
    current_user: User = Depends(require_permission("system_monitoring", "read")),
) -> ApplicationMetrics:
    """获取应用性能指标"""
    return collect_application_metrics()


@router.get("/health", response_model=HealthStatus, summary="获取系统健康状态")
async def get_health_status(
    current_user: User = Depends(require_permission("system_monitoring", "read")),
) -> HealthStatus:
    """获取系统整体健康状态"""
    components = await check_component_health()
    overall_score = calculate_overall_health_score(components)

    if overall_score >= 90:
        status = "healthy"
    elif overall_score >= 70:
        status = "degraded"
    else:
        status = "unhealthy"

    return HealthStatus(
        status=status,
        timestamp=datetime.now(),
        components=components,
        overall_score=overall_score,
    )


@router.get(
    "/metrics/history", response_model=list[SystemMetrics], summary="获取系统指标历史"
)
def get_history(
    hours: int = Query(default=24, ge=1, le=168, description="查询历史时间范围(小时)"),
    current_user: User = Depends(require_permission("system_monitoring", "read")),
) -> list[SystemMetrics]:
    """获取系统性能指标历史数据"""
    cutoff_time = datetime.now() - timedelta(hours=hours)
    return [m for m in get_metrics_history() if m.timestamp > cutoff_time]


@router.get("/alerts", response_model=list[PerformanceAlert], summary="获取性能告警")
def get_performance_alerts(
    level: str | None = Query(
        default=None, regex="^(info|warning|critical)$", description="告警级别过滤"
    ),
    resolved: bool | None = Query(default=None, description="是否已解决过滤"),
    current_user: User = Depends(require_permission("system_monitoring", "read")),
) -> list[PerformanceAlert]:
    """获取性能告警列表"""
    alerts = get_active_alerts()

    if level:
        alerts = [a for a in alerts if a.level == level]

    if resolved is not None:
        alerts = [a for a in alerts if a.resolved == resolved]

    return sorted(alerts, key=lambda x: x.timestamp, reverse=True)


@router.post("/alerts/{alert_id}/resolve", summary="解决告警")
def resolve_alert(
    alert_id: str,
    current_user: User = Depends(require_permission("system_monitoring", "write")),
) -> dict[str, Any]:
    """标记告警为已解决"""
    for alert in get_active_alerts():
        if alert.id == alert_id:
            alert.resolved = True
            return {"message": f"告警 {alert_id} 已标记为解决", "success": True}

    raise not_found(
        f"告警 {alert_id} 未找到", resource_type="alert", resource_id=alert_id
    )


@router.get("/dashboard", summary="获取监控仪表板数据")
async def get_monitoring_dashboard(
    current_user: User = Depends(require_permission("system_monitoring", "read")),
) -> dict[str, Any]:
    """获取监控仪表板综合数据"""
    system_metrics = collect_system_metrics()
    app_metrics = collect_application_metrics()
    health_status = await get_health_status(current_user)

    recent_alerts = sorted(
        get_active_alerts(), key=lambda x: x.timestamp, reverse=True
    )[:10]
    recent_system_metrics = get_metrics_history()[-12:]
    recent_app_metrics = get_application_metrics_history()[-12:]

    return {
        "current_system": system_metrics,
        "current_application": app_metrics,
        "health_status": health_status,
        "active_alerts": recent_alerts,
        "trends": {
            "system_metrics": recent_system_metrics,
            "application_metrics": recent_app_metrics,
        },
        "summary": {
            "total_alerts": len(get_active_alerts()),
            "critical_alerts": len(
                [a for a in get_active_alerts() if a.level == "critical"]
            ),
            "warning_alerts": len(
                [a for a in get_active_alerts() if a.level == "warning"]
            ),
            "health_score": health_status.overall_score,
            "last_updated": datetime.now().isoformat(),
        },
    }


@router.post("/metrics/collect", summary="手动触发指标收集")
def trigger_metrics_collection(
    current_user: User = Depends(require_permission("system_monitoring", "write")),
) -> dict[str, Any]:
    """手动触发一次指标收集"""
    system_metrics = collect_system_metrics()
    app_metrics = collect_application_metrics()
    new_alerts = check_performance_alerts(system_metrics, app_metrics)

    return {
        "message": "指标收集完成",
        "system_metrics": system_metrics,
        "application_metrics": app_metrics,
        "new_alerts_count": len(new_alerts),
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/encryption-status", summary="获取加密状态")
def get_encryption_status(
    current_user: User = Depends(require_permission("system_monitoring", "read")),
) -> dict[str, Any]:
    """获取数据加密系统状态"""
    try:
        from ....core.encryption import EncryptionKeyManager

        key_manager = EncryptionKeyManager()
        encryption_enabled = key_manager.is_available()

        protected_fields = {
            "RentContract": ["owner_phone", "tenant_phone"],
            "Contact": ["phone", "office_phone"],
            "Asset": ["project_phone"],
        }

        total_protected_fields = sum(
            len(fields) for fields in protected_fields.values()
        )

        response = {
            "encryption_enabled": encryption_enabled,
            "encryption_algorithm": "AES-256-CBC (deterministic) / AES-256-GCM (standard)",
            "key_version": key_manager.get_version() if encryption_enabled else None,
            "protected_fields": protected_fields,
            "total_protected_fields": total_protected_fields,
            "status": "active" if encryption_enabled else "disabled",
            "timestamp": datetime.now().isoformat(),
        }

        if not encryption_enabled:
            response["warning"] = (
                "数据加密未启用。敏感数据（PII）将以明文存储。"
                "强烈建议设置 DATA_ENCRYPTION_KEY 环境变量以保护敏感信息。"
            )

        return response

    except Exception as e:
        raise internal_error(f"获取加密状态失败: {str(e)}")
