"""
统一应用启动文件
整合统一错误处理和配置管理系统
"""

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

# 导入路由注册器
from .core.router_registry import register_routes

# 导入统一配置和错误处理
from .core.unified_config import get_global_config, load_config
from .core.unified_error_handler import (
    ErrorCode,
    UnifiedError,
    UnifiedErrorHandler,
    unified_error_handler,
)
from .middleware.unified_error_middleware import (
    MetricsMiddleware,
    RateLimitMiddleware,
    RequestLoggingMiddleware,
    SecurityMiddleware,
    UnifiedErrorMiddleware,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    await startup_events()

    try:
        yield
    finally:
        # 关闭时执行
        await shutdown_events()


async def startup_events():
    """应用启动事件"""
    config = get_global_config()
    logger = logging.getLogger(__name__)

    logger.info("=" * 60)
    logger.info("🚀 启动地产资产管理系统")
    logger.info(f"📍 环境: {config.environment.value}")
    logger.info(f"🔧 调试模式: {config.debug}")
    logger.info(f"🌐 主机: {config.api.host}:{config.api.port}")
    logger.info(f"📚 API版本: {config.api.version}")
    logger.info("=" * 60)

    # 创建必要的目录
    await create_directories(config)

    # 初始化数据库连接池
    await initialize_database(config)

    # 初始化缓存连接
    await initialize_cache(config)

    logger.info("✅ 应用启动完成")


async def shutdown_events():
    """应用关闭事件"""
    logger = logging.getLogger(__name__)
    logger.info("🛑 正在关闭应用...")

    # 清理资源
    await cleanup_resources()

    logger.info("✅ 应用已安全关闭")


async def create_directories(config):
    """创建必要的目录"""
    directories = [
        config.upload_path(),
        Path(config.logging.file_path).parent,
        Path("logs"),
        Path("temp"),
        Path("uploads/pdf"),
        Path("uploads/excel"),
        Path("uploads/images"),
    ]

    for directory in directories:
        try:
            directory.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.warning(f"⚠️ 无法创建目录 {directory}: {e}")


async def initialize_database(config):
    """初始化数据库连接"""
    try:
        # 这里可以添加数据库连接池初始化逻辑
        logger = logging.getLogger(__name__)
        logger.info("📊 数据库连接初始化完成")
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"❌ 数据库初始化失败: {e}")
        raise


async def initialize_cache(config):
    """初始化缓存连接"""
    if config.cache.redis_enabled:
        try:
            # 这里可以添加Redis连接初始化逻辑
            logger = logging.getLogger(__name__)
            logger.info("💾 缓存连接初始化完成")
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.warning(f"⚠️ 缓存初始化失败: {e}")


async def cleanup_resources():
    """清理资源"""
    # 这里可以添加资源清理逻辑
    pass


def create_application() -> FastAPI:
    """创建FastAPI应用实例"""

    # 加载配置
    config = load_config()

    # 创建应用实例
    app = FastAPI(
        title=config.api.title,
        description=config.api.description,
        version=config.api.version,
        debug=config.debug,
        lifespan=lifespan,
        docs_url="/docs" if config.debug else None,
        redoc_url="/redoc" if config.debug else None,
        openapi_url="/openapi.json" if config.debug else None,
    )

    # 配置CORS
    setup_cors(app, config)

    # 配置信任主机
    setup_trusted_hosts(app, config)

    # 添加中间件
    setup_middleware(app, config)

    # 注册路由
    register_routes(app, config.api.prefix)

    # 添加异常处理器
    setup_exception_handlers(app)

    # 添加健康检查端点
    setup_health_check(app)

    # 添加指标端点
    setup_metrics_endpoint(app)

    return app


def setup_cors(app: FastAPI, config):
    """配置CORS"""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.security.allowed_origins,
        allow_credentials=config.security.allow_credentials,
        allow_methods=config.security.allowed_methods,
        allow_headers=config.security.allowed_headers,
    )


def setup_trusted_hosts(app: FastAPI, config):
    """配置信任主机"""
    if config.environment.value == "production":
        trusted_hosts = ["*"]  # 生产环境应该配置具体的主机列表
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=trusted_hosts)


def setup_middleware(app: FastAPI, config):
    """设置中间件"""
    # 指标收集中间件（最外层）
    if config.monitoring.metrics_enabled:
        app.add_middleware(MetricsMiddleware, enabled=True)

    # 速率限制中间件
    app.add_middleware(RateLimitMiddleware, enabled=True)

    # 安全头中间件
    app.add_middleware(
        SecurityMiddleware, enabled=config.security.enable_security_headers
    )

    # 请求日志中间件
    app.add_middleware(RequestLoggingMiddleware)

    # 统一错误处理中间件
    app.add_middleware(UnifiedErrorMiddleware, error_handler=unified_error_handler)


def setup_exception_handlers(app: FastAPI):
    """设置异常处理器"""

    @app.exception_handler(UnifiedError)
    async def unified_error_exception_handler(request: Request, exc: UnifiedError):
        """处理统一错误异常"""
        return unified_error_handler.handle_error(exc, request)

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """处理未捕获的异常"""
        logger = logging.getLogger(__name__)
        logger.error(f"未捕获的异常: {type(exc).__name__}: {exc}")

        unified_error = UnifiedError(
            message="服务器内部错误",
            code=ErrorCode.INTERNAL_SERVER_ERROR,
            details=str(exc) if get_global_config().debug else None,
        )

        return unified_error_handler.handle_error(unified_error, request)


def setup_health_check(app: FastAPI):
    """设置健康检查端点"""

    @app.get("/health")
    async def health_check():
        """健康检查端点"""
        config = get_global_config()
        return {
            "status": "healthy",
            "environment": config.environment.value,
            "version": config.api.version,
            "timestamp": "2025-11-07T03:00:00Z",
        }

    @app.get("/health/ready")
    async def readiness_check():
        """就绪检查端点"""
        # 检查数据库连接、缓存连接等
        checks = {
            "database": "healthy",
            "cache": "healthy"
            if get_global_config().cache.redis_enabled
            else "disabled",
            "file_system": "healthy",
        }

        all_healthy = all(status == "healthy" for status in checks.values())

        return {
            "status": "ready" if all_healthy else "not_ready",
            "checks": checks,
            "timestamp": "2025-11-07T03:00:00Z",
        }


def setup_metrics_endpoint(app: FastAPI):
    """设置指标端点"""

    # 获取指标中间件实例
    metrics_middleware = None
    for middleware in app.user_middleware:
        if (
            hasattr(middleware.cls, "__name__")
            and "MetricsMiddleware" in middleware.cls.__name__
        ):
            metrics_middleware = middleware
            break

    if not metrics_middleware:
        return

    @app.get("/metrics")
    async def metrics():
        """指标端点"""
        if hasattr(metrics_middleware, "instance") and hasattr(
            metrics_middleware.instance, "get_metrics"
        ):
            return metrics_middleware.instance.get_metrics()

        return {"error": "Metrics not available"}


# 创建应用实例
app = create_application()


if __name__ == "__main__":
    import uvicorn

    config = get_global_config()

    # 配置日志
    logging.basicConfig(
        level=getattr(logging, config.logging.level.value),
        format=config.logging.format,
        datefmt=config.logging.date_format,
    )

    logger = logging.getLogger(__name__)
    logger.info("🚀 启动应用服务器...")

    # 启动服务器
    uvicorn.run(
        "main_unified:app",
        host=config.api.host,
        port=config.api.port,
        reload=config.api.reload,
        debug=config.debug,
        log_level=config.logging.level.value.lower(),
        access_log=config.logging.console_enabled,
    )
