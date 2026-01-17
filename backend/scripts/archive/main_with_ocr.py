"""
土地物业资产管理系统 - 主应用入口
"""

import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

# OCR服务导入 - 使用条件导入避免依赖问题
try:
    from .services.document.optimized_ocr_service import OptimizedOCRService

    OCR_SERVICE_AVAILABLE = True
except ImportError as e:
    print(f"Warning: OCR服务不可用 - {e}")
    OptimizedOCRService = None
    OCR_SERVICE_AVAILABLE = False

try:
    from .services.providers.ocr_provider import get_ocr_service, set_ocr_service

    OCR_PROVIDER_AVAILABLE = True
except ImportError as e:
    print(f"Warning: OCR提供者不可用 - {e}")
    def get_ocr_service():
        return None
    def set_ocr_service(x):
        return None
    OCR_PROVIDER_AVAILABLE = False

try:
    from .services.adapters.paddle_ocr_engine_adapter import PaddleOCREngineAdapter
except Exception:
    PaddleOCREngineAdapter = None  # type: ignore

# 导入API路由 - 使用条件导入
try:
    from .core.router_registry import register_api_routes, route_registry

    ROUTER_REGISTRY_AVAILABLE = True
except ImportError as e:
    print(f"Warning: 路由注册器不可用 - {e}")
    def register_api_routes():
        return None
    route_registry = type(
        "MockRegistry",
        (),
        {
            "register_global_dependency": lambda x: None,
            "include_all": lambda app, version: None,
        },
    )()
    ROUTER_REGISTRY_AVAILABLE = False
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

# 中间件导入 - 使用条件导入
try:
    from .middleware.error_recovery_middleware import ErrorRecoveryMiddleware

    ERROR_RECOVERY_MIDDLEWARE_AVAILABLE = True
except ImportError as e:
    print(f"Warning: 错误恢复中间件不可用 - {e}")
    ErrorRecoveryMiddleware = None
    ERROR_RECOVERY_MIDDLEWARE_AVAILABLE = False

try:
    from .middleware.request_logging import RequestLoggingMiddleware

    REQUEST_LOGGING_MIDDLEWARE_AVAILABLE = True
except ImportError as e:
    print(f"Warning: 请求日志中间件不可用 - {e}")
    RequestLoggingMiddleware = None
    REQUEST_LOGGING_MIDDLEWARE_AVAILABLE = False

try:
    from .middleware.security_middleware import setup_security_middleware

    SECURITY_MIDDLEWARE_AVAILABLE = True
except ImportError as e:
    print(f"Warning: 安全中间件不可用 - {e}")
    def setup_security_middleware(app):
        return None
    SECURITY_MIDDLEWARE_AVAILABLE = False

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

    # 🔐 JWT安全专项检查 - 临时跳过，避免启动问题
    logger.info("🔐 JWT安全配置检查... [临时跳过]")
    try:
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
    except Exception as e:
        logger.warning(f"⚠️ JWT配置检查跳过，存在启动问题: {e}")
        logger.info("🔧 使用默认JWT配置继续启动...")

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
if SECURITY_MIDDLEWARE_AVAILABLE:
    setup_security_middleware(app)
else:
    print("Warning: 跳过安全中间件设置")

# 设置请求日志中间件
if REQUEST_LOGGING_MIDDLEWARE_AVAILABLE and RequestLoggingMiddleware:
    app.add_middleware(RequestLoggingMiddleware)
else:
    print("Warning: 跳过请求日志中间件")

# 设置错误恢复中间件
if ERROR_RECOVERY_MIDDLEWARE_AVAILABLE and ErrorRecoveryMiddleware:
    app.add_middleware(ErrorRecoveryMiddleware)
else:
    print("Warning: 跳过错误恢复中间件")

# 设置文件上传安全中间件
try:
    from .middleware.file_upload_security import create_file_security_middleware

    file_security_middleware = create_file_security_middleware(app)
    app.add_middleware(type(file_security_middleware))
except ImportError as e:
    print(f"Warning: 文件上传安全中间件不可用 - {e}")

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
if ROUTER_REGISTRY_AVAILABLE:
    try:
        register_api_routes()
        # 全局依赖：OCR 服务（确保每个请求上下文可用）
        route_registry.register_global_dependency(Depends(get_ocr_service))
        # 统一注册 v1 路由
        route_registry.include_all(app, version="v1")
        logger.info("已通过路由注册器统一注册 API 路由")
    except Exception as e:
        logger.error(f"路由注册器注册失败: {e}")
else:
    logger.warning("路由注册器不可用，使用手动路由注册")

    # 手动添加关键API路由
    routes_added = []

    # 1. 认证路由
    try:
        from .api.v1.auth import router as auth_router

        app.include_router(auth_router, prefix="/api/v1/auth", tags=["认证"])
        routes_added.append("认证")
        logger.info("已手动添加认证路由")
    except ImportError as e:
        logger.warning(f"无法添加认证路由: {e}")

        # 添加最基础的登录端点
        @app.post("/api/v1/auth/login")
        async def login(credentials: dict):
            """基础登录接口"""
            username = credentials.get("username", "")
            password = credentials.get("password", "")
            if username == "admin" and password == "admin123":
                return {
                    "success": True,
                    "message": "登录成功",
                    "user": {
                        "id": 1,
                        "username": "admin",
                        "full_name": "系统管理员",
                        "roles": ["admin"],
                    },
                    "token": "mock_token_admin",
                }
            else:
                return {"success": False, "message": "用户名或密码错误"}

    # 2. 资产管理路由
    try:
        from .api.v1.assets import asset_router

        app.include_router(asset_router, prefix="/api/v1/assets", tags=["资产管理"])
        routes_added.append("资产管理")
        logger.info("已手动添加资产管理路由")
    except ImportError as e:
        logger.warning(f"无法添加资产管理路由: {e}")

    # 3. 租赁合同路由
    try:
        from .api.v1.rent_contract import rent_contract_router

        app.include_router(
            rent_contract_router, prefix="/api/v1/rental-contracts", tags=["租赁合同"]
        )
        routes_added.append("租赁合同")
        logger.info("已手动添加租赁合同路由")
    except ImportError as e:
        logger.warning(f"无法添加租赁合同路由: {e}")

    # 4. 统计分析路由
    try:
        from .api.v1.statistics import statistics_router

        app.include_router(
            statistics_router, prefix="/api/v1/analytics", tags=["数据分析"]
        )
        routes_added.append("数据分析")
        logger.info("已手动添加统计分析路由")
    except ImportError as e:
        logger.warning(f"无法添加统计分析路由: {e}")

    # 5. 系统管理路由
    try:
        from .api.v1.system import system_router

        app.include_router(system_router, prefix="/api/v1/system", tags=["系统管理"])
        routes_added.append("系统管理")
        logger.info("已手动添加系统管理路由")
    except ImportError as e:
        logger.warning(f"无法添加系统管理路由: {e}")

    # 6. Excel处理路由
    try:
        from .api.v1.excel import excel_router

        app.include_router(excel_router, prefix="/api/v1/excel", tags=["Excel处理"])
        routes_added.append("Excel处理")
        logger.info("已手动添加Excel处理路由")
    except ImportError as e:
        logger.warning(f"无法添加Excel处理路由: {e}")

    logger.info(
        f"手动路由注册完成，共添加 {len(routes_added)} 个模块: {', '.join(routes_added)}"
    )

# 设置日志安全
try:
    setup_logging_security()
except Exception as e:
    logger.warning(f"日志安全设置失败: {e}")

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
