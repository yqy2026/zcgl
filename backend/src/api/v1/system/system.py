"""
系统核心路由模块
包含健康检查、应用信息、API根路径等系统级端点
"""

from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ....core.response_handler import success_response
from ....database import get_database_status

router = APIRouter(tags=["系统管理"])


@router.get("/monitoring/health")
def health_check() -> JSONResponse:
    """
    健康检查端点 - 包含数据库状态
    迁移自 main.py 的健康检查功能
    """
    try:
        db_status = get_database_status()

        health_check = db_status.get("health_check", {})
        metrics = db_status.get("metrics", {})
        pool_status = (
            health_check.get("checks", {}).get("connection_pool", {})
            if isinstance(health_check, dict)
            else {}
        )

        health_data = {
            "status": "healthy",
            "version": "2.0.0",
            "service": "土地物业资产管理系统",
            "database": {
                "healthy": bool(health_check.get("healthy", False)),
                "engine_type": db_status.get("engine_type", "Unknown"),
            },
        }

        try:
            database_data: dict[str, Any] = health_data["database"]  # type: ignore[assignment]
            database_data.update(
                {
                    "connection_pool_utilization": pool_status.get("utilization", 0),
                    "active_connections": metrics.get("active_connections", 0),
                    "total_queries": metrics.get("total_queries", 0),
                    "slow_queries": metrics.get("slow_queries", 0),
                    "avg_response_time_ms": round(
                        metrics.get("avg_response_time", 0), 2
                    ),
                    "pool_hit_rate": pool_status.get("pool_hit_rate", 0),
                }
            )
        except Exception as db_e:
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to get detailed database metrics: {db_e}")
            database_data["metrics_error"] = str(db_e)

        return success_response(data=health_data, message="系统运行正常")

    except Exception as e:
        import logging

        from sqlalchemy.exc import OperationalError

        from ....core.exception_handler import service_unavailable

        logger = logging.getLogger(__name__)
        logger.error(f"健康检查失败: {e}")

        if isinstance(e, OperationalError):
            raise service_unavailable("数据库不可用，请稍后重试")
        raise service_unavailable("系统健康检查失败")


@router.get("/system/info")
def app_info() -> JSONResponse:
    """
    应用信息端点
    迁移自 main.py 的应用信息功能
    """
    return success_response(
        data={
            "name": "土地物业资产管理系统",
            "version": "2.0.0",
            "description": "专为资产管理经理设计的智能化工作平台",
            "docs_url": "/docs",
            "features": [
                "PDF智能导入",
                "58字段资产管理",
                "RBAC权限控制",
                "实时数据分析",
                "Excel导入导出",
            ],
        },
        message="应用信息获取成功",
    )


@router.get("/system/root")
def api_root() -> JSONResponse:
    """
    API根路径端点
    迁移自 main.py 的API根路径功能
    """
    return success_response(
        data={
            "version": "2.0.0",
            "endpoints": {
                "health": "/api/v1/monitoring/health",
                "assets": "/api/v1/assets",
                "auth": "/api/v1/auth",
                "docs": "/docs",
                "system": "/api/v1/system",
            },
        },
        message="API 根路径",
    )
