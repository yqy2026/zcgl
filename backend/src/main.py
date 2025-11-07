"""
土地物业资产管理系统 - 主应用入口
"""

import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 导入API路由
from .core.router_registry import register_api_routes, route_registry
from .services.optimized_ocr_service import OptimizedOCRService
from .services.providers.ocr_provider import get_ocr_service, set_ocr_service

try:
    from .services.adapters.paddle_ocr_engine_adapter import PaddleOCREngineAdapter
except Exception:
    PaddleOCREngineAdapter = None  # type: ignore
from .core.config import settings
from .core.config_manager import get_config, initialize_config
from .core.exception_handler import setup_exception_handlers
from .core.jwt_security import validate_current_jwt_config
from .core.logging_security import setup_logging_security
from .core.response_handler import success_response
from .database import (
    create_tables,
    get_database_status,
    initialize_enhanced_database_if_available,
)
from .middleware.error_recovery_middleware import ErrorRecoveryMiddleware
from .middleware.request_logging import RequestLoggingMiddleware
from .middleware.security_middleware import setup_security_middleware

# 设置日志
logger = logging.getLogger(__name__)


# ===== 应用生命周期管理 =====
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理器"""
    # 启动时执行
    import os

    # 🔐 安全配置检查
    logger.info("🔐 开始安全配置检查...")
    settings.log_security_status()

    # 🔐 JWT安全专项检查
    logger.info("🔐 JWT安全配置检查...")
    jwt_config_result = validate_current_jwt_config()

    if not jwt_config_result["config_valid"]:
        logger.error("🚨 JWT配置存在严重安全问题:")
        for issue in jwt_config_result["issues"]:
            logger.error(f"  ❌ {issue}")
    else:
        logger.info("✅ JWT配置安全检查通过")

    if jwt_config_result.get("recommendations"):
        logger.info("💡 JWT安全建议:")
        for rec in jwt_config_result["recommendations"]:
            logger.info(f"  💡 {rec}")

    provider = os.getenv("OCR_ENGINE_PROVIDER", "optimized").lower()
    try:
        if provider == "paddle" and PaddleOCREngineAdapter is not None:
            ocr = PaddleOCREngineAdapter()
            set_ocr_service(ocr)
            logger.info("OCR 引擎: PaddleOCREngineAdapter 已初始化")
        else:
            ocr = OptimizedOCRService()
            set_ocr_service(ocr)
            logger.info("OCR 引擎: OptimizedOCRService 已初始化")
    except Exception as e:
        logger.error(f"OCR 服务初始化失败: {e}")

    yield

    # 关闭时执行
    try:
        # 重置 Provider，以避免悬挂实例
        set_ocr_service(None)
        logger.info("OCR 服务已释放并清理 Provider")
    except Exception as e:
        logger.warning(f"OCR 服务释放失败: {e}")


# 创建FastAPI应用实例
app = FastAPI(
    title="土地物业资产管理系统",
    description="专为资产管理经理设计的智能化工作平台",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# 初始化配置
initialize_config()

# 设置CORS中间件
cors_origins = get_config(
    "cors_origins", ["http://localhost:5173", "http://localhost:5174"]
)
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
app.add_middleware(RequestLoggingMiddleware)

# 设置错误恢复中间件
app.add_middleware(ErrorRecoveryMiddleware)

# 设置文件上传安全中间件
from .middleware.file_upload_security import create_file_security_middleware

file_security_middleware = create_file_security_middleware(app)
app.add_middleware(type(file_security_middleware))

# 设置统一异常处理器
setup_exception_handlers(app)


# 健康检查端点（必须在路由注册之前定义）
@app.get("/api/v1/health", tags=["健康检查"])
async def health_check():
    """健康检查端点 - 包含数据库状态"""
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
                logger.warning(f"Failed to get detailed database metrics: {db_e}")
                health_data["database"]["metrics_error"] = str(db_e)

        return success_response(data=health_data, message="系统运行正常")

    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return {
            "success": False,
            "status": "unhealthy",
            "timestamp": datetime.now(UTC).isoformat(),
            "error": str(e),
            "database": {"status": "unknown"},
        }


# 根路由端点
@app.get("/", tags=["根路由"])
async def root_endpoint():
    """根路由端点"""
    return success_response(
        data={
            "service": "土地物业资产管理系统 API",
            "version": "2.0.0",
            "docs_url": "/docs",
            "health_check": "/api/v1/health",
        },
        message="欢迎使用土地物业资产管理系统API",
    )


# API v1根路径
@app.get("/api/v1/", tags=["根路径"])
async def api_v1_root():
    """API v1根路径"""
    return success_response(
        data={
            "version": "2.0.0",
            "endpoints": {
                "health": "/api/v1/health",
                "assets": "/api/v1/assets",
                "auth": "/api/v1/auth",
                "docs": "/docs",
            },
        },
        message="API v1 根路径",
    )


# 应用信息端点
@app.get("/api/v1/info", tags=["应用信息"])
async def app_info():
    """应用信息端点"""
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


# 统一通过路由注册器注册路由与全局依赖
try:
    register_api_routes()
    # 全局依赖：OCR 服务（确保每个请求上下文可用）
    route_registry.register_global_dependency(Depends(get_ocr_service))
    # 统一注册 v1 路由
    route_registry.include_all(app, version="v1")
    logger.info("已通过路由注册器统一注册 API 路由")
except Exception as e:
    logger.error(f"路由注册器注册失败: {e}")

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
