"""
系统核心路由模块
包含健康检查、应用信息、API根路径等系统级端点
"""

from datetime import UTC, datetime
from fastapi import APIRouter
from ...core.response_handler import success_response
from ...database import get_database_status

router = APIRouter(tags=["系统管理"])


@router.get("/monitoring/health")
async def health_check():
    """
    健康检查端点 - 包含数据库状态
    迁移自 main.py 的健康检查功能
    """
    try:
        # 获取数据库状态
        db_status = get_database_status()

        health_data = {
            "status": "healthy",
            "version": "2.0.0",
            "service": "土地物业资产管理系统",
            "database": {
                "enhanced_active": db_status.get("enhanced_active", False),
                "enhanced_available": db_status.get("enhanced_available", False),
                "engine_type": db_status.get("engine_type", "Unknown"),
            },
        }

        # 如果增强数据库激活，添加更多指标
        if db_status.get("enhanced_active"):
            try:
                pool_status = db_status.get("pool_status", {})
                metrics = db_status.get("enhanced_metrics", {})

                health_data["database"].update(
                    {
                        "connection_pool_utilization": pool_status.get(
                            "utilization", 0
                        ),
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
                health_data["database"]["metrics_error"] = str(db_e)

        return success_response(data=health_data, message="系统运行正常")

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"健康检查失败: {e}")
        return {
            "success": False,
            "status": "unhealthy",
            "timestamp": datetime.now(UTC).isoformat(),
            "error": str(e),
            "database": {"status": "unknown"},
        }


@router.get("/system/info")
async def app_info():
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
async def api_root():
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