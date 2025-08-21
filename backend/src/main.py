"""
土地物业资产管理系统 - 主应用入口
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
import logging
import traceback
from datetime import datetime

from .database import create_tables
from .exceptions import AssetNotFoundError, DuplicateAssetError, BusinessLogicError

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建FastAPI应用实例
app = FastAPI(
    title="土地物业资产管理系统",
    description="专为资产管理经理设计的个人工作助手工具",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# 配置CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React开发服务器
        "http://127.0.0.1:3000",
        "http://localhost:5173",  # Vite开发服务器
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)



# 全局异常处理器
@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    """处理Pydantic验证错误"""
    logger.error(f"Validation error: {exc}")
    return JSONResponse(
        status_code=400,
        content={
            "error": "Validation Error",
            "message": "请求数据格式不正确",
            "details": exc.errors(),
            "timestamp": datetime.now().isoformat(),
        }
    )


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    """处理FastAPI请求验证错误"""
    logger.error(f"Request validation error: {exc}")
    return JSONResponse(
        status_code=422,
        content={
            "error": "Request Validation Error",
            "message": "请求参数验证失败",
            "details": exc.errors(),
            "timestamp": datetime.now().isoformat(),
        }
    )


@app.exception_handler(AssetNotFoundError)
async def asset_not_found_handler(request: Request, exc: AssetNotFoundError):
    """处理资产未找到异常"""
    logger.warning(f"Asset not found: {exc.asset_id}")
    return JSONResponse(
        status_code=404,
        content={
            "error": "Asset Not Found",
            "message": f"未找到ID为 {exc.asset_id} 的资产",
            "timestamp": datetime.now().isoformat(),
        }
    )


@app.exception_handler(DuplicateAssetError)
async def duplicate_asset_handler(request: Request, exc: DuplicateAssetError):
    """处理重复资产异常"""
    logger.warning(f"Duplicate asset: {exc.property_name}")
    return JSONResponse(
        status_code=409,
        content={
            "error": "Duplicate Asset",
            "message": f"物业名称 '{exc.property_name}' 已存在",
            "timestamp": datetime.now().isoformat(),
        }
    )


@app.exception_handler(BusinessLogicError)
async def business_logic_handler(request: Request, exc: BusinessLogicError):
    """处理业务逻辑异常"""
    logger.warning(f"Business logic error: {exc.message}")
    return JSONResponse(
        status_code=400,
        content={
            "error": "Business Logic Error",
            "message": exc.message,
            "timestamp": datetime.now().isoformat(),
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """处理HTTP异常"""
    logger.warning(f"HTTP exception: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP Error",
            "message": exc.detail,
            "timestamp": datetime.now().isoformat(),
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """处理未捕获的异常"""
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "服务器内部错误，请稍后重试",
            "timestamp": datetime.now().isoformat(),
        }
    )


# 应用启动事件
@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    logger.info("正在启动土地物业资产管理系统...")
    
    # 创建数据库表
    try:
        create_tables()
        logger.info("数据库表创建成功")
    except Exception as e:
        logger.error(f"数据库表创建失败: {e}")
        raise
    
    logger.info("土地物业资产管理系统启动完成")


# 应用关闭事件
@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行"""
    logger.info("土地物业资产管理系统正在关闭...")


# 导入并包含API路由
from .api import api_router
app.include_router(api_router)


# 基础路由
@app.get("/", tags=["基础"])
async def root() -> dict[str, str]:
    """根路径健康检查"""
    return {
        "message": "土地物业资产管理系统 API 服务正常运行",
        "version": "0.1.0",
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/health", tags=["基础"])
async def health_check() -> dict[str, str]:
    """健康检查端点"""
    return {
        "status": "healthy",
        "service": "land-property-management",
        "version": "0.1.0",
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/info", tags=["基础"])
async def app_info() -> dict[str, str]:
    """应用信息端点"""
    return {
        "name": "土地物业资产管理系统",
        "description": "专为资产管理经理设计的个人工作助手工具",
        "version": "0.1.0",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "openapi_url": "/openapi.json",
        "timestamp": datetime.now().isoformat(),
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8001,
        reload=True,
        log_level="info",
    )