"""
数据库监控端点模块
"""

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, Query

from .....constants.message_constants import ErrorIDs
from .....core.exception_handler import (
    BaseBusinessError,
    ConfigurationError,
    internal_error,
    service_unavailable,
)
from .....middleware.auth import AuthzContext, get_current_active_user, require_authz
from .health import get_database_manager
from .models import DatabaseHealthMetrics, DatabaseOptimizationReport

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .....models.auth import User

# 关键依赖导入 - 使用快速失败策略
try:
    from .....models.auth import User
except ImportError as e:
    logger.critical(
        "无法导入数据库监控关键依赖",
        extra={
            "error_id": ErrorIDs.System.RESOURCE_EXHAUSTED,
            "import_error": str(e),
            "module": "system_monitoring.database_endpoints",
        },
    )
    raise ConfigurationError(
        "数据库监控模块缺少必要依赖，无法启动。\n"
        "请运行: poetry install 或 pip install -e .\n"
        f"导入错误详情: {e}",
        config_key="system_monitoring.database_endpoints",
    )


router = APIRouter()


@router.get(
    "/database/health",
    response_model=DatabaseHealthMetrics,
    summary="获取数据库健康指标",
)
async def get_database_health_metrics(
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(action="read", resource_type="system_monitoring")
    ),
) -> DatabaseHealthMetrics:
    """获取数据库健康状态和性能指标"""
    try:
        db_manager: Any = get_database_manager()
        if not db_manager:
            raise service_unavailable("数据库管理器不可用")

        health_check = await db_manager.run_health_check()
        pool_status: dict[str, Any] = db_manager.get_connection_pool_status()
        metrics = db_manager.get_metrics()

        health_score = 100.0
        if not health_check["healthy"]:
            health_score -= 50.0

        utilization = pool_status.get("utilization", 0)
        if utilization > 90:
            health_score -= 30.0
        elif utilization > 80:
            health_score -= 15.0

        if metrics.total_queries > 0:
            slow_query_rate = (metrics.slow_queries / metrics.total_queries) * 100
            if slow_query_rate > 10:
                health_score -= 20.0
            elif slow_query_rate > 5:
                health_score -= 10.0

        if metrics.avg_response_time > 1000:
            health_score -= 15.0
        elif metrics.avg_response_time > 500:
            health_score -= 5.0

        health_score = max(0.0, health_score)

        return DatabaseHealthMetrics(
            timestamp=datetime.now(),
            connection_pool_status=pool_status,
            active_connections=metrics.active_connections,
            total_queries=metrics.total_queries,
            slow_queries=metrics.slow_queries,
            avg_response_time=metrics.avg_response_time,
            pool_hit_rate=pool_status.get("pool_hit_rate", 0),
            database_size_mb=health_check["checks"]
            .get("database_size", {})
            .get("size_mb", 0),
            health_score=health_score,
        )

    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"获取数据库健康指标失败: {str(e)}")


@router.get("/database/slow-queries", summary="获取慢查询列表")
def get_slow_queries(
    page_size: int = Query(default=20, ge=1, le=100, description="返回数量限制"),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(action="read", resource_type="system_monitoring")
    ),
) -> dict[str, Any]:
    """获取数据库慢查询列表"""
    try:
        db_manager: Any = get_database_manager()
        if not db_manager:
            raise service_unavailable("数据库管理器不可用")

        slow_queries = db_manager.get_slow_queries(limit=page_size)

        return {
            "slow_queries": slow_queries,
            "total_count": len(slow_queries),
            "threshold_ms": db_manager.slow_query_threshold,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"获取慢查询失败: {str(e)}")


@router.post(
    "/database/optimize",
    response_model=DatabaseOptimizationReport,
    summary="执行数据库优化",
)
def optimize_database(
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="update",
            resource_type="system_monitoring",
        )
    ),
) -> DatabaseOptimizationReport:
    """执行数据库优化操作"""
    try:
        db_manager: Any = get_database_manager()
        if not db_manager:
            raise service_unavailable("数据库管理器不可用")

        before_metrics = db_manager.get_metrics()
        before_pool_status: dict[str, Any] = db_manager.get_connection_pool_status()

        optimization_results: dict[str, Any] = db_manager.optimize_database()
        cleanup_count: int = db_manager.cleanup_old_sessions(days=7)

        after_metrics = db_manager.get_metrics()
        after_pool_status: dict[str, Any] = db_manager.get_connection_pool_status()

        performance_improvement: dict[str, float] = {}
        if before_metrics.avg_response_time > 0:
            improvement_percent = (
                (before_metrics.avg_response_time - after_metrics.avg_response_time)
                / before_metrics.avg_response_time
            ) * 100
            performance_improvement["avg_response_time_improvement_percent"] = round(
                improvement_percent, 2
            )

        if before_pool_status.get("utilization", 0) > 0:
            utilization_improvement = before_pool_status.get(
                "utilization", 0
            ) - after_pool_status.get("utilization", 0)
            performance_improvement["pool_utilization_improvement_percent"] = round(
                utilization_improvement, 2
            )

        return DatabaseOptimizationReport(
            timestamp=datetime.now(),
            actions_taken=optimization_results.get("actions_taken", []),
            recommendations=optimization_results.get("recommendations", []),
            performance_improvement=performance_improvement,
            cleanup_results={
                "cleaned_records": cleanup_count,
                "optimization_success": "error" not in optimization_results,
                "optimization_error": optimization_results.get("error"),
            },
        )

    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"数据库优化失败: {str(e)}")


@router.post("/database/cleanup", summary="清理数据库过期数据")
def cleanup_database(
    days: int = Query(default=7, ge=1, le=90, description="清理多少天前的数据"),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="delete",
            resource_type="system_monitoring",
        )
    ),
) -> dict[str, Any]:
    """清理数据库过期数据"""
    try:
        db_manager: Any = get_database_manager()
        if not db_manager:
            raise service_unavailable("数据库管理器不可用")

        cleaned_count: int = db_manager.cleanup_old_sessions(days=days)

        return {
            "message": f"成功清理了 {cleaned_count} 条过期数据",
            "cleaned_records": cleaned_count,
            "days_cleaned": days,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"数据库清理失败: {str(e)}")


@router.get("/database/connection-pool", summary="获取连接池状态")
def get_connection_pool_status(
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(action="read", resource_type="system_monitoring")
    ),
) -> dict[str, Any]:
    """获取数据库连接池详细状态"""
    try:
        db_manager: Any = get_database_manager()
        if not db_manager:
            raise service_unavailable("数据库管理器不可用")

        pool_status: dict[str, Any] = db_manager.get_connection_pool_status()

        return {
            "pool_status": pool_status,
            "configuration": {
                "pool_size": db_manager.config.pool_size,
                "max_overflow": db_manager.config.max_overflow,
                "pool_timeout": db_manager.config.pool_timeout,
                "pool_recycle": db_manager.config.pool_recycle,
                "pool_pre_ping": db_manager.config.pool_pre_ping,
            },
            "metrics": db_manager.get_metrics().__dict__,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"获取连接池状态失败: {str(e)}")
