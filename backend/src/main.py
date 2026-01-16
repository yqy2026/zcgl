"""
土地物业资产管理系统 - 主应用入口
使用环境感知的依赖管理
"""

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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

# OCR服务已完全禁用 - 功能已移除
# OCR functionality has been completely removed due to encoding issues
# The system will run without PDF OCR text extraction capabilities
OCR_SERVICE_AVAILABLE = False
OCR_PROVIDER_AVAILABLE = False
PaddleOCREngineAdapter: Any = None
OptimizedOCRService: Any = None


def get_ocr_service() -> Any:
    """OCR服务占位函数 - 返回None"""
    return None


def set_ocr_service(service: Any) -> None:
    """OCR服务占位函数 - 不执行任何操作"""
    pass


safe_print("Info: OCR service disabled - PDF intelligent import unavailable")

# ===== 关键依赖（生产环境必须存在）=====
# 路由注册器 - 关键依赖
router_registry_module = safe_import(
    "src.core.router_registry",
    critical=True,
    mock_factory=create_mock_registry,
)
if hasattr(router_registry_module, "route_registry"):
    route_registry = router_registry_module.route_registry
else:
    route_registry = create_mock_registry()

if hasattr(router_registry_module, "register_api_routes"):
    register_api_routes = router_registry_module.register_api_routes
else:
    register_api_routes = create_lambda_none

# 安全中间件 - 关键依赖
setup_security_middleware = safe_import_from(
    "src.middleware.security_middleware",
    "setup_security_middleware",
    critical=True,
    fallback=lambda app: None,
)

# ===== 重要功能（推荐存在，允许降级）=====
ErrorRecoveryMiddleware = safe_import(
    "src.middleware.error_recovery_middleware:ErrorRecoveryMiddleware",
    fallback=None,
)

RequestLoggingMiddleware = safe_import(
    "src.middleware.request_logging:RequestLoggingMiddleware",
    fallback=None,
)

# V1 兼容中间件（可选，迁移完成后可移除）
V1CompatibilityMiddleware = safe_import(
    "src.middleware.v1_compatibility:V1CompatibilityMiddleware",
    fallback=None,
)
add_v1_compatibility = safe_import_from(
    "src.middleware.v1_compatibility",
    "add_v1_compatibility",
    fallback=lambda app, preserve_endpoints=None: None,
)

logger.info("依赖导入完成")


# ===== 应用生命周期管理 =====
@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:
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

    # 初始化枚举字段数据
    if not is_testing():
        try:
            from .database import SessionLocal
            from .services.enum_data_init import add_legacy_enum_values, init_enum_data

            if SessionLocal is None:
                logger.warning("无法获取数据库会话工厂，跳过枚举初始化")
            else:
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


# 创建FastAPI应用实例
app = FastAPI(
    title="土地物业资产管理系统",
    description="专为资产管理经理设计的智能化工作平台",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# PDF智能导入API - 直接注册到应用
try:
    from .api.v1.pdf_import import router as pdf_import_router
    app.include_router(pdf_import_router, prefix="/api/pdf-import", tags=["PDF智能导入"])
    safe_print("✓ PDF导入路由已注册")
except Exception as e:
    safe_print(f"✗ PDF导入路由注册失败: {e}")

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
    # The middleware factory is already correctly configured by create_file_security_middleware
    # No need to add it again
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
logger.info(f"检查路由注册器: route_registry={route_registry is not None}, register_api_routes={register_api_routes is not None}")
if route_registry and register_api_routes:
    logger.info("开始通过路由注册器注册路由...")
    try:
        register_api_routes()
        logger.info("register_api_routes() 调用成功")
        # 全局依赖：OCR 服务（确保每个请求上下文可用）
        route_registry.register_global_dependency(Depends(get_ocr_service))
        # 统一注册路由（版本化架构）
        route_registry.include_all(app, version="v1")
        logger.info("已通过路由注册器统一注册 API 路由（版本化）")
        # 单独注册非版本化路由（如 PDF 导入）
        route_registry.include_all(app, version=None)
        logger.info("已通过路由注册器注册非版本化路由")
        logger.info(f"总路由数: {len(app.routes)}")
    except Exception as e:
        logger.error(f"路由注册器注册失败: {e}")
        import traceback
        traceback.print_exc()

    # 手动路由注册已移除，统一使用路由注册器管理所有API路由
    logger.info("手动路由注册已移除，统一使用路由注册器管理所有API路由")
else:
    logger.warning("路由注册器或register_api_routes不可用，跳过路由注册")

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
