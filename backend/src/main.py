"""
土地物业资产管理系统 - 主应用入口
使用环境感知的依赖管理
"""

import logging
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# 核心依赖 - 严格导入（开发/生产环境必须存在）
from .core.config import settings, validate_config
from .core.encoding_utils import safe_print, setup_utf8_encoding
from .core.environment import (
    get_dependency_policy,
    get_environment,
    is_production,
    is_testing,
)
from .core.exception_handler import (
    ConfigurationError,
    InternalServerError,
    setup_exception_handlers,
)
from .core.import_utils import (
    create_lambda_none,
    create_mock_registry,
    safe_import,
    safe_import_from,
)
from .core.observability import init_sentry
from .core.response_handler import success_response
from .database import get_database_status, init_db, reset_database_manager
from .security.logging_security import setup_logging_security

if TYPE_CHECKING:
    from .utils.cache_manager import CacheManager as AsyncCacheManager

# 立即设置 UTF-8 编码
setup_utf8_encoding()

# 设置日志
logger = logging.getLogger(__name__)

# 初始化 Sentry (可选)
init_sentry()

# 记录启动环境
env = get_environment()
logger.info(f"当前环境: {env.value}")
logger.info(f"依赖策略: {get_dependency_policy().value}")
allow_mock_registry = settings.ALLOW_MOCK_REGISTRY or is_testing()
if is_production() and settings.ALLOW_MOCK_REGISTRY:
    raise ConfigurationError(
        "生产环境禁止启用 ALLOW_MOCK_REGISTRY",
        config_key="ALLOW_MOCK_REGISTRY",
    )
if is_production():
    allow_mock_registry = False

# ===== 关键依赖（生产环境必须存在）=====
# 路由注册器 - 关键依赖
router_registry_module = safe_import(
    "src.core.router_registry",
    critical=True,
    mock_factory=create_mock_registry if allow_mock_registry else None,
)
if hasattr(router_registry_module, "route_registry"):
    route_registry = router_registry_module.route_registry
elif allow_mock_registry:
    route_registry = create_mock_registry()
else:
    if is_production():
        raise ConfigurationError(
            "缺少 route_registry（生产环境禁止降级）",
            config_key="route_registry",
        )
    raise ConfigurationError(
        "缺少 route_registry 且未启用 ALLOW_MOCK_REGISTRY",
        config_key="ALLOW_MOCK_REGISTRY",
    )

if hasattr(router_registry_module, "register_api_routes"):
    register_api_routes = router_registry_module.register_api_routes
elif allow_mock_registry:
    register_api_routes = create_lambda_none
else:
    if is_production():
        raise ConfigurationError(
            "缺少 register_api_routes（生产环境禁止降级）",
            config_key="register_api_routes",
        )
    raise ConfigurationError(
        "缺少 register_api_routes 且未启用 ALLOW_MOCK_REGISTRY",
        config_key="ALLOW_MOCK_REGISTRY",
    )

# 安全中间件 - 关键依赖
setup_security_middleware = safe_import_from(
    "src.middleware.security_middleware",
    "setup_security_middleware",
    critical=True,
    fallback=lambda app: None,
)

# ===== 重要功能（推荐存在，允许降级）=====
ErrorRecoveryMiddleware = safe_import_from(
    "src.middleware.error_recovery_middleware",
    "ErrorRecoveryMiddleware",
    fallback=None,
)

RequestLoggingMiddleware = safe_import_from(
    "src.middleware.request_logging",
    "RequestLoggingMiddleware",
    fallback=None,
)

logger.info("依赖导入完成")


# ===== 应用生命周期管理 =====
@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:
    """应用生命周期管理器"""
    # 启动时执行

    # Secret validation - NEW: Validate SECRET_KEY and DATA_ENCRYPTION_KEY on startup
    logger.info("Validating application secrets...")
    try:
        # Correct import path: src.security.secret_validator
        from .security.secret_validator import SecretValidationError, secret_validator

        try:
            logger.info("🔐 Validating application secrets...")

            if not secret_validator.validate_env_secrets():
                logger.warning("⚠️  WARNING: Weak secrets detected!")
                logger.warning("In production, the application will refuse to start.")
                if is_production():
                    logger.error("❌ Production mode requires strong secrets. Exiting.")
                    raise SystemExit(1)
        except SecretValidationError as e:
            logger.error(f"❌ Secret validation failed: {e}")
            if is_production():
                raise SystemExit(1)

    except ImportError:
        logger.warning("Secret validator module not available, skipping validation")

    # 安全配置检查 (已在配置加载时自动完成)
    logger.info("安全配置检查已完成")

    # 初始化异步缓存（Redis）
    async_cache_manager: AsyncCacheManager | None = None
    try:
        from .utils.cache_manager import cache_manager as utils_cache_manager

        async_cache_manager = utils_cache_manager
        if async_cache_manager is not None:
            try:
                await async_cache_manager.initialize()
            except RuntimeError as e:
                logger.warning(
                    "缓存初始化失败，将继续使用内存缓存",
                    extra={
                        "bootstrap_component": "cache",
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "fallback": "memory_cache",
                    },
                )
                async_cache_manager = None
            except Exception as e:
                logger.exception(
                    "缓存初始化异常，将继续使用内存缓存",
                    extra={
                        "bootstrap_component": "cache",
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "fallback": "memory_cache",
                    },
                )
                async_cache_manager = None
    except ImportError as e:
        logger.warning(
            "缓存模块加载失败，将继续使用内存缓存",
            extra={
                "bootstrap_component": "cache",
                "error_type": type(e).__name__,
                "error_message": str(e),
                "fallback": "memory_cache",
            },
        )

    # JWT安全专项检查 - 重新启用安全验证
    logger.info("执行JWT安全配置检查...")
    try:
        from .security.jwt_security import validate_current_jwt_config

        jwt_config_result = validate_current_jwt_config()

        if not jwt_config_result["config_valid"]:
            for issue in jwt_config_result["issues"]:
                logger.error(f"JWT安全问题: {issue}")
            # 非测试模式下拒绝启动
            if not is_testing():
                raise ConfigurationError(
                    "JWT配置存在严重安全问题，拒绝启动。请检查SECRET_KEY配置。",
                    config_key="SECRET_KEY",
                )
        else:
            logger.info("JWT配置安全检查通过")

        for rec in jwt_config_result.get("recommendations", []):
            logger.warning(f"JWT安全建议: {rec}")
    except ImportError as e:
        logger.warning(f"JWT安全模块导入失败: {e}")
        # 模块缺失时记录警告但仍允许启动
    except ConfigurationError:
        # 安全检查失败，重新抛出以阻止启动
        raise
    except Exception as e:
        logger.warning(f"JWT配置检查出现异常: {e}")
        if not is_testing():
            logger.error("安全检查失败，拒绝在非测试模式下继续启动")
            raise InternalServerError(
                message=f"JWT安全检查失败: {e}",
                original_error=e,
            )

    # 初始化枚举字段数据
    if not is_testing():
        try:
            from .database import async_session_scope
            from .services.enum_data_init import init_enum_data

            try:
                logger.info("开始初始化枚举字段数据...")
                async with async_session_scope() as db:
                    init_result = await init_enum_data(db, created_by="system")
                    logger.info(
                        f"枚举类型初始化: 创建 {init_result['types_created']}, 更新 {init_result['types_updated']}"
                    )
                    logger.info(
                        f"枚举值初始化: 创建 {init_result['values_created']}, 更新 {init_result['values_updated']}"
                    )

            except Exception as e:
                logger.warning(f"枚举数据初始化失败: {e}")
        except ImportError as e:
            logger.warning(f"枚举初始化模块导入失败: {e}")
        except Exception as e:
            logger.warning(f"枚举数据初始化异常: {e}")

    # 初始化数据库（跳过测试模式）
    if not is_testing():
        await init_db()

        # 记录数据库状态
        db_status = await get_database_status()
        logger.info(f"数据库状态: {db_status}")

        health_check = db_status.get("health_check", {})
        if isinstance(health_check, dict) and health_check.get("healthy"):
            logger.info("数据库健康检查通过")
        else:
            logger.info("数据库健康检查未通过或未返回状态")

        # 启动缓存预热（best effort）
        try:
            from .database import async_session_scope
            from .services.cache_warmup_service import cache_warmup_service

            async with async_session_scope() as db:
                warmup_result = await cache_warmup_service.warmup_low_churn_data(db)
                logger.info(
                    "启动缓存预热完成: success=%s failure=%s duration_ms=%s",
                    warmup_result["success_count"],
                    warmup_result["failure_count"],
                    warmup_result["duration_ms"],
                )
        except ImportError as e:
            logger.warning("缓存预热模块导入失败: %s", e)
        except Exception as e:
            logger.warning("缓存预热执行失败: %s", e, exc_info=True)
    else:
        logger.info("测试模式：跳过数据库自动初始化，使用测试fixture提供的数据库")

    yield

    # 关闭异步缓存连接
    if async_cache_manager is not None:
        try:
            await async_cache_manager.close()
        except Exception as e:
            logger.warning(f"缓存关闭失败: {e}")

    # 关闭鉴权失效事件总线传输层（Redis pub/sub 监听线程）
    try:
        from .services.authz import authz_event_bus

        authz_event_bus.close()
    except Exception as e:
        logger.warning(f"鉴权事件总线关闭失败: {e}")

    # 释放全局数据库管理器，避免测试多轮生命周期复用旧事件循环连接池
    try:
        await reset_database_manager()
    except Exception as e:
        logger.warning(f"数据库管理器关闭失败: {e}")


# 创建FastAPI应用实例
app = FastAPI(
    title="土地物业资产管理系统",
    description="专为资产管理经理设计的智能化工作平台",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    default_response_class=JSONResponse,
)

# 初始化配置
validate_config()

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

# 设置CORS中间件（保持最外层以覆盖错误响应）
cors_origins = settings.CORS_ORIGINS
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
        "Authorization",
        "Content-Type",
        "X-CSRF-Token",
        "X-Requested-With",
        "X-Request-ID",
        "Accept",
        "Origin",
        "Access-Control-Request-Method",
        "Access-Control-Request-Headers",
    ],
    expose_headers=[
        "X-Request-ID",
        "Request-ID",
    ],
)

# API架构说明：系统使用统一的版本化架构 /api/v1/*
# 所有API端点都通过路由注册器统一管理
logger.info("版本化API架构已启用 - 使用 /api/v1/* 端点")
safe_print("版本化API架构已配置完成")

# 设置统一异常处理器
setup_exception_handlers(app)


# 健康检查端点已迁移到 /api/v1/monitoring/health
# 原有的 /api/health 路由已移除，统一使用路由注册器管理


# 根路由端点
@app.get("/", tags=["根路由"])
async def root_endpoint() -> JSONResponse:
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
logger.info(
    f"检查路由注册器: route_registry={route_registry is not None}, register_api_routes={register_api_routes is not None}"
)
if route_registry and register_api_routes:
    logger.info("开始通过路由注册器注册路由...")
    try:
        register_api_routes()
        logger.info("register_api_routes() 调用成功")
        # 统一注册路由（版本化架构）
        route_registry.include_all(app, version="v1")
        logger.info("已通过路由注册器统一注册 API 路由（版本化）")
        logger.info(f"总路由数: {len(app.routes)}")
    except Exception as e:
        logger.error(f"路由注册器注册失败: {e}")
        import traceback

        traceback.print_exc()

    # 手动路由注册已移除，统一使用路由注册器管理所有API路由
    logger.info("手动路由注册已移除，统一使用路由注册器管理所有API路由")
else:
    logger.warning("路由注册器或register_api_routes不可用，跳过路由注册")

# 设置日志安全
try:
    setup_logging_security()
except Exception as e:
    logger.warning(f"日志安全设置失败: {e}")

logger.info("FastAPI应用启动完成")
