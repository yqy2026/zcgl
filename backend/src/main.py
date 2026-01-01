"""
土地物业资产管理系统 - 主应用入口
使用环境感知的依赖管理
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 核心依赖 - 严格导入（开发/生产环境必须存在）
from .core.config import get_config, initialize_config, settings
from .core.encoding_utils import (
    safe_error_message,
    safe_print,
    setup_utf8_encoding,
)
from .core.environment import (
    get_dependency_policy,
    get_environment,
    is_production,
    is_testing,
)
from .core.exception_handler import setup_exception_handlers
from .core.import_utils import (
    create_lambda_none,
    create_mock_registry,
    safe_import,
    safe_import_from,
)
from .core.logging_security import setup_logging_security
from .core.response_handler import success_response
from .database import (
    create_tables,
    get_database_status,
    init_db,
)

# 立即设置 UTF-8 编码
setup_utf8_encoding()

# 设置日志
logger = logging.getLogger(__name__)

# 记录启动环境
env = get_environment()
logger.info(f"当前环境: {env.value}")
logger.info(f"依赖策略: {get_dependency_policy().value}")

# ===== 关键依赖（生产环境必须存在）=====
# 路由注册器 - 关键依赖
router_registry_module = safe_import(
    ".core.router_registry",
    critical=True,
    mock_factory=create_mock_registry,
)
if hasattr(router_registry_module, 'route_registry'):
    route_registry = router_registry_module.route_registry
else:
    route_registry = create_mock_registry()

if hasattr(router_registry_module, 'register_api_routes'):
    register_api_routes = router_registry_module.register_api_routes
else:
    register_api_routes = create_lambda_none

# 安全中间件 - 关键依赖
setup_security_middleware = safe_import_from(
    ".middleware.security_middleware",
    "setup_security_middleware",
    critical=True,
    fallback=lambda app: None,
)

# ===== 重要功能（推荐存在，允许降级）=====
ErrorRecoveryMiddleware = safe_import(
    ".middleware.error_recovery_middleware:ErrorRecoveryMiddleware",
    fallback=None,
)

RequestLoggingMiddleware = safe_import(
    ".middleware.request_logging:RequestLoggingMiddleware",
    fallback=None,
)

# ===== 可选功能（允许降级）=====
# OCR 服务 - 完全禁用以避免编码问题
OCR_SERVICE_AVAILABLE = False
OptimizedOCRService = None
safe_print("Info: OCR service disabled - avoiding encoding issues")

# OCR Provider
get_ocr_service = safe_import_from(
    ".services.providers.ocr_provider",
    "get_ocr_service",
    fallback=lambda: None,
)
set_ocr_service = safe_import_from(
    ".services.providers.ocr_provider",
    "set_ocr_service",
    fallback=lambda x: None,
)

# PaddleOCR 引擎
PaddleOCREngineAdapter = safe_import(
    ".services.adapters.paddle_ocr_engine_adapter:PaddleOCREngineAdapter",
    fallback=None,
)

# V1 兼容中间件（可选，迁移完成后可移除）
V1CompatibilityMiddleware = safe_import(
    ".middleware.v1_compatibility:V1CompatibilityMiddleware",
    fallback=None,
)
add_v1_compatibility = safe_import_from(
    ".middleware.v1_compatibility",
    "add_v1_compatibility",
    fallback=lambda app, preserve_endpoints=None: None,
)

logger.info("依赖导入完成")


# ===== 应用生命周期管理 =====
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理器"""
    # 启动时执行
    # 安全配置检查
    logger.info("开始安全配置检查...")
    settings.log_security_status()

    # JWT安全专项检查 - 重新启用安全验证
    logger.info("执行JWT安全配置检查...")
    try:
        from .core.jwt_security import validate_current_jwt_config

        jwt_config_result = validate_current_jwt_config()

        if not jwt_config_result["config_valid"]:
            for issue in jwt_config_result["issues"]:
                logger.error(f"JWT安全问题: {issue}")
            # 非测试模式下拒绝启动
            if not is_testing():
                raise RuntimeError(
                    "JWT配置存在严重安全问题，拒绝启动。请检查SECRET_KEY配置。"
                )
        else:
            logger.info("JWT配置安全检查通过")

        for rec in jwt_config_result.get("recommendations", []):
            logger.warning(f"JWT安全建议: {rec}")
    except ImportError as e:
        logger.warning(f"JWT安全模块导入失败: {e}")
        # 模块缺失时记录警告但仍允许启动
    except RuntimeError:
        # 安全检查失败，重新抛出以阻止启动
        raise
    except Exception as e:
        logger.warning(f"JWT配置检查出现异常: {e}")
        if not is_testing():
            logger.error("安全检查失败，拒绝在非测试模式下继续启动")
            raise RuntimeError(f"JWT安全检查失败: {e}")

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

    # 初始化枚举字段数据
    if not is_testing():
        try:
            from .database import SessionLocal
            from .services.enum_data_init import add_legacy_enum_values, init_enum_data

            db = SessionLocal()
            try:
                logger.info("开始初始化枚举字段数据...")
                init_result = init_enum_data(db, created_by="system")
                logger.info(
                    f"枚举类型初始化: 创建 {init_result['types_created']}, 更新 {init_result['types_updated']}"
                )
                logger.info(
                    f"枚举值初始化: 创建 {init_result['values_created']}, 更新 {init_result['values_updated']}"
                )

                # 添加遗留枚举值支持
                legacy_result = add_legacy_enum_values(db, created_by="system")
                logger.info(f"遗留枚举值添加: {legacy_result['values_added']}")
            except Exception as e:
                logger.warning(f"枚举数据初始化失败: {e}")
            finally:
                db.close()
        except ImportError as e:
            logger.warning(f"枚举初始化模块导入失败: {e}")
        except Exception as e:
            logger.warning(f"枚举数据初始化异常: {e}")

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
    allow_methods=[
        "GET",
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
        "OPTIONS",
    ],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "Accept",
        "Origin",
        "Access-Control-Request-Method",
        "Access-Control-Request-Headers",
    ],
)

# 设置安全中间件
if setup_security_middleware:
    setup_security_middleware(app)
else:
    safe_print("Warning: Skipping security middleware setup")

# 设置请求日志中间件
if RequestLoggingMiddleware:
    app.add_middleware(RequestLoggingMiddleware)
else:
    safe_print("Warning: Skipping request logging middleware")

# 设置错误恢复中间件
if ErrorRecoveryMiddleware:
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
    safe_print(
        f"Warning: File upload security middleware not available - {safe_error_message(e)}"
    )

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
if route_registry and register_api_routes:
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

# 初始化数据库（跳过测试模式）
if not is_testing():
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
else:
    logger.info("测试模式：跳过数据库自动初始化，使用测试fixture提供的数据库")

logger.info("FastAPI应用启动完成")
# Trigger reload
