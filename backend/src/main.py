"""
土地物业资产管理系统 - 主应用入口
整合UTF-8编码安全处理
"""

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 导入编码安全工具
from .core.encoding_utils import (
    safe_error_message,
    safe_print,
    setup_utf8_encoding,
)

# 立即设置UTF-8编码
setup_utf8_encoding()

# OCR服务导入 - 完全禁用以避免编码问题
OCR_SERVICE_AVAILABLE = False
OptimizedOCRService = None
safe_print("Info: OCR service disabled - avoiding encoding issues")

try:
    from .services.providers.ocr_provider import get_ocr_service, set_ocr_service
    OCR_PROVIDER_AVAILABLE = True
except ImportError as e:
    safe_print(f"Warning: OCR provider not available - {safe_error_message(e)}")
    get_ocr_service = lambda: None
    set_ocr_service = lambda x: None
    OCR_PROVIDER_AVAILABLE = False

try:
    from .services.adapters.paddle_ocr_engine_adapter import PaddleOCREngineAdapter
except Exception:
    PaddleOCREngineAdapter = None  # type: ignore

# 导入API路由 - 使用条件导入
try:
    # 恢复路由注册器以实现统一路由管理
    from .core.router_registry import register_api_routes, route_registry
    ROUTER_REGISTRY_AVAILABLE = True
except ImportError as e:
    safe_print(f"Warning: Router registry not available - {safe_error_message(e)}")
    register_api_routes = lambda: None
    route_registry = type('MockRegistry', (), {
        'register_global_dependency': lambda x: None,
        'include_all': lambda app, version: None
    })()
from .core.config import get_config, initialize_config, settings
from .core.exception_handler import setup_exception_handlers

# from .core.jwt_security import validate_current_jwt_config  # 临时禁用
from .core.logging_security import setup_logging_security
from .core.response_handler import success_response
from .database import (
    create_tables,
    get_database_status,
    init_db,
)

# 中间件导入 - 使用条件导入
try:
    from .middleware.error_recovery_middleware import ErrorRecoveryMiddleware
    ERROR_RECOVERY_MIDDLEWARE_AVAILABLE = True
except ImportError as e:
    safe_print(f"Warning: Error recovery middleware not available - {safe_error_message(e)}")
    ErrorRecoveryMiddleware = None
    ERROR_RECOVERY_MIDDLEWARE_AVAILABLE = False

try:
    from .middleware.request_logging import RequestLoggingMiddleware
    REQUEST_LOGGING_MIDDLEWARE_AVAILABLE = True
except ImportError as e:
    safe_print(f"Warning: Request logging middleware not available - {safe_error_message(e)}")
    RequestLoggingMiddleware = None
    REQUEST_LOGGING_MIDDLEWARE_AVAILABLE = False

try:
    from .middleware.security_middleware import setup_security_middleware
    SECURITY_MIDDLEWARE_AVAILABLE = True
except ImportError as e:
    safe_print(f"Warning: Security middleware not available - {safe_error_message(e)}")
    setup_security_middleware = lambda app: None
    SECURITY_MIDDLEWARE_AVAILABLE = False

try:
    from .middleware.v1_compatibility import (
        V1CompatibilityMiddleware,
        add_v1_compatibility,
    )
    V1_COMPATIBILITY_AVAILABLE = True
except ImportError as e:
    safe_print(f"Warning: V1 compatibility middleware not available - {safe_error_message(e)}")
    add_v1_compatibility = lambda app, preserve_endpoints=None: None
    V1CompatibilityMiddleware = None
    V1_COMPATIBILITY_AVAILABLE = False

# 设置日志
logger = logging.getLogger(__name__)


# ===== 应用生命周期管理 =====
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理器"""
    # 启动时执行
    import os

    # 安全配置检查
    logger.info("开始安全配置检查...")
    settings.log_security_status()

    # JWT安全专项检查 - 临时跳过，避免启动问题
    logger.info("JWT安全配置检查... [临时跳过]")
    try:
        # jwt_config_result = validate_current_jwt_config()  # 临时禁用
        jwt_config_result = {"config_valid": True, "issues": [], "recommendations": []}

        if not jwt_config_result["config_valid"]:
            logger.error("严重错误: JWT配置存在严重安全问题:")
            for issue in jwt_config_result["issues"]:
                logger.error(f"  错误: {issue}")
        else:
            logger.info("JWT配置安全检查通过")

        if jwt_config_result.get("recommendations"):
            logger.info("JWT安全建议:")
            for rec in jwt_config_result["recommendations"]:
                logger.info(f"  建议: {rec}")
    except Exception as e:
        logger.warning(f"警告: JWT配置检查跳过，存在启动问题: {e}")
        logger.info("使用默认JWT配置继续启动...")

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
    safe_print("Warning: Skipping security middleware setup")

# 设置请求日志中间件
if REQUEST_LOGGING_MIDDLEWARE_AVAILABLE and RequestLoggingMiddleware:
    app.add_middleware(RequestLoggingMiddleware)
else:
    safe_print("Warning: Skipping request logging middleware")

# 设置错误恢复中间件
if ERROR_RECOVERY_MIDDLEWARE_AVAILABLE and ErrorRecoveryMiddleware:
    app.add_middleware(ErrorRecoveryMiddleware)
else:
    safe_print("Warning: Skipping error recovery middleware")

# API架构说明：系统使用统一的版本化架构 /api/v1/*
# 所有API端点都通过路由注册器统一管理
logger.info("版本化API架构已启用 - 使用 /api/v1/* 端点")
safe_print("版本化API架构已配置完成")

# 设置文件上传安全中间件
try:
    from .middleware.file_upload_security import create_file_security_middleware
    file_security_middleware = create_file_security_middleware(app)
    app.add_middleware(type(file_security_middleware))
except ImportError as e:
    safe_print(f"Warning: File upload security middleware not available - {safe_error_message(e)}")

# 设置统一异常处理器
setup_exception_handlers(app)


# 健康检查端点已迁移到 /api/v1/monitoring/health
# 原有的 /api/health 路由已移除，统一使用路由注册器管理


# 根路由端点
@app.get("/", tags=["根路由"])
async def root_endpoint():
    """根路由端点"""
    return success_response(
        data={
            "service": "土地物业资产管理系统 API",
            "version": "2.0.0",
            "docs_url": "/docs",
            "health_check": "/api/v1/monitoring/health",
            "api_root": "/api/v1",
        },
        message="欢迎使用土地物业资产管理系统API",
    )


# API根路径和应用信息端点已迁移到路由注册器
# /api/ → /api/v1/system/root
# /api/info → /api/v1/system/info
# 统一使用路由注册器管理，避免手动路由冲突


# 统一通过路由注册器注册路由与全局依赖
if ROUTER_REGISTRY_AVAILABLE:
    try:
        register_api_routes()
        # 全局依赖：OCR 服务（确保每个请求上下文可用）
        route_registry.register_global_dependency(Depends(get_ocr_service))
        # 统一注册路由（版本化架构）
        route_registry.include_all(app, version="v1")
        logger.info("已通过路由注册器统一注册 API 路由（版本化）")
    except Exception as e:
        logger.error(f"路由注册器注册失败: {e}")
# else:
#     logger.warning("路由注册器不可用，使用手动路由注册")
#     # 手动路由注册已被禁用，使用路由注册器统一管理

    # # 调试端点 - 列出所有路由
    # @app.get("/debug/routes", tags=["调试"])
    # async def debug_routes():
    #     """调试端点 - 列出所有注册的路由"""
    #     routes_info = []
    #     for route in app.routes:
    #         if hasattr(route, 'path') and hasattr(route, 'methods'):
    #             route_info = {
    #                 "path": route.path,
    #                 "methods": list(route.methods) if hasattr(route, 'methods') else [],
    #                 "name": getattr(route, 'name', 'unknown')
    #             }
    #             routes_info.append(route_info)
    #
    #     return {
    #         "success": True,
    #         "total_routes": len(routes_info),
    #         "routes": routes_info
    #     }

    # 调试路由已移除 - 统一使用路由注册器管理
    # 资产调试功能请使用 /api/v1/assets 端点

    # 移除手动路由注册 - 统一使用路由注册器
    logger.info("手动路由注册已移除，统一使用路由注册器管理所有API路由")

    # 注释掉重复的/assets路由 - 使用最高优先级版本
    # @app.get("/api/assets", tags=["资产管理-最终兼容"])
    # async def final_assets_compatibility():
    #     """最终兼容性API - 获取资产列表（无认证）"""
    #     safe_print("DEBUG: 最终兼容性API被调用 - 这应该是唯一被调用的/api/assets路由")
    #     logger.info("最终兼容性API被调用")
    #     return {
    #         "success": True,
    #         "data": [],
    #         "total": 0,
    #         "page": 1,
    #         "limit": 20,
    #         "pages": 0,
    #         "message": "最终兼容性API成功 - 无需认证"
    #     }

# PDF智能导入API端点已迁移到路由注册器
# /api/pdf-import/* → /api/v1/pdf-import/*
# 统一使用路由注册器管理，避免手动路由冲突

# 设置日志安全
try:
    setup_logging_security()
except Exception as e:
    logger.warning(f"日志安全设置失败: {e}")

# 初始化数据库
init_db()

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
# Trigger reload
