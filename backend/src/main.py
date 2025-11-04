"""
土地物业资产管理系统 - 主应用入口
"""

import logging
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 导入API路由
from .api.v1 import api_router
from .api.v1.pdf_import_unified import router as pdf_import_router
from .core.config_manager import get_config, initialize_config
from .core.error_handler import create_error_handlers
from .core.exception_handler import setup_exception_handlers
from .core.logging_security import setup_logging_security
from .database import (
    create_tables,
    get_database_status,
    initialize_enhanced_database_if_available,
)
from .middleware.error_recovery_middleware import ErrorRecoveryMiddleware
from .middleware.request_logging import create_request_logging_middleware
from .middleware.security_middleware import setup_security_middleware

# 设置日志
logger = logging.getLogger(__name__)

# 创建FastAPI应用实例
app = FastAPI(
    title="土地物业资产管理系统",
    description="专为资产管理经理设计的智能化工作平台",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# 初始化配置
initialize_config()

# 设置CORS中间件
cors_origins = get_config("cors_origins", ["http://localhost:5173"])
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 设置安全中间件
setup_security_middleware(app)

# 设置请求日志中间件
app.add_middleware(create_request_logging_middleware())

# 设置错误恢复中间件
app.add_middleware(ErrorRecoveryMiddleware)

# 设置统一异常处理器
setup_exception_handlers(app)

# 设置新的统一错误处理框架
create_error_handlers(app)


# 健康检查端点（必须在路由注册之前定义）
@app.get("/api/v1/health", tags=["健康检查"])
async def health_check():
    """健康检查端点 - 包含数据库状态"""
    try:
        # 获取数据库状态
        db_status = get_database_status()

        health_response = {
            "status": "healthy",
            "timestamp": datetime.now(UTC).isoformat(),
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

                health_response["database"].update(
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
                logger.warning(f"Failed to get detailed database metrics: {db_e}")
                health_response["database"]["metrics_error"] = str(db_e)

        return health_response

    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now(UTC).isoformat(),
            "error": str(e),
            "database": {"status": "unknown"},
        }


# 根路由端点
@app.get("/", tags=["根路由"])
async def root_endpoint():
    """根路由端点"""
    return {
        "message": "土地物业资产管理系统 API",
        "version": "2.0.0",
        "docs_url": "/docs",
        "health_check": "/api/v1/health",
    }


# API v1根路径
@app.get("/api/v1/", tags=["根路径"])
async def api_v1_root():
    """API v1根路径"""
    return {
        "message": "API v1 根路径",
        "version": "2.0.0",
        "endpoints": {
            "health": "/api/v1/health",
            "assets": "/api/v1/assets",
            "auth": "/api/v1/auth",
            "docs": "/docs",
        },
    }


# 应用信息端点
@app.get("/api/v1/info", tags=["应用信息"])
async def app_info():
    """应用信息端点"""
    return {
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
    }


# 注册API路由
app.include_router(api_router)
app.include_router(pdf_import_router, prefix="/api/v1/pdf-import", tags=["PDF智能导入"])

# 设置日志安全
setup_logging_security()

# 初始化增强数据库管理器（如果可用）
initialize_enhanced_database_if_available()

# 创建数据库表
create_tables()

# 记录数据库状态
db_status = get_database_status()
logger.info(f"数据库状态: {db_status}")

if db_status.get("enhanced_active"):
    logger.info("增强数据库管理器已激活 - 性能监控和连接池优化已启用")
else:
    logger.info("使用基础数据库配置")

logger.info("FastAPI应用启动完成")
