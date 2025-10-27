"""
土地物业资产管理系统 - 主应用入口
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from jose import JWTError
import logging
import traceback
from datetime import datetime

from .database import create_tables
from .exceptions import AssetNotFoundError, DuplicateAssetError, BusinessLogicError
from .utils.cache_manager import cache_manager
from .core.config_manager import initialize_config, get_config
from .core.exception_handler import setup_exception_handlers
from .core.logging_security import setup_logging_security
from .middleware.api_security import api_security_middleware
from .middleware.request_logging import create_request_logging_middleware
from .middleware.security_middleware import setup_security_middleware
from .middleware.error_recovery_middleware import ErrorRecoveryMiddleware

# 初始化配置管理器
initialize_config()

# 设置日志安全
setup_logging_security()
logger = logging.getLogger(__name__)

# 创建FastAPI应用实例
app = FastAPI(
    title=get_config("api_title", "土地物业资产管理系统"),
    description="专为资产管理经理设计的个人工作助手工具",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# 设置安全中间件（在CORS之前设置）
setup_security_middleware(app)

# 配置CORS中间件
cors_origins = get_config("cors_origins", ["*"])
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# 添加错误恢复中间件（在其他中间件之前）
app.add_middleware(ErrorRecoveryMiddleware)

# 添加请求日志中间件
app.add_middleware(create_request_logging_middleware)

# 设置统一异常处理器
setup_exception_handlers(app)

# 健康检查端点（必须在路由注册之前定义）
@app.get("/api/v1/health", tags=["健康检查"])
async def health_check():
    """健康检查端点"""
    try:
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "2.0.0"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
            "version": "2.0.0"
        }

@app.get("/", tags=["根路由"])
async def root_endpoint():
    """根路由端点"""
    return {
        "message": "土地物业资产管理系统 API",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/v1/", tags=["根路径"])
async def api_v1_root():
    """API v1根路径"""
    return {
        "message": "土地物业资产管理系统 API v1",
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/v1/info", tags=["应用信息"])
async def app_info():
    """应用信息端点"""
    return {
        "name": "土地物业资产管理系统",
        "version": "2.0.0",
        "docs_url": "/docs"
    }

# 导入API路由
from .api.v1 import api_router
from .api.v1.pdf_import_unified import router as pdf_import_router
# from .api.v1.pdf_import_enhanced import router as pdf_import_enhanced_router  # 暂时注释
# from .api.v1.error_recovery import router as error_recovery_router  # 暂时注释

# 注册API路由
app.include_router(api_router)

# 注册PDF导入API路由 - 使用统一的连字符命名
app.include_router(pdf_import_router, prefix="/api/v1/pdf-import")

# 注册增强版PDF导入API路由
# app.include_router(pdf_import_enhanced_router, prefix="/api/v1/pdf-import")  # 暂时注释

# 注册错误恢复管理API路由
# app.include_router(error_recovery_router, prefix="/api/v1")  # 暂时注释

# 创建数据库表
create_tables()

logger.info("FastAPI应用启动完成")