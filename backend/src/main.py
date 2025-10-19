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
from .config import settings
from .middleware.api_security import api_security_middleware

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

# 添加API安全中间件
# app.middleware("http")(api_security_middleware)  # 临时禁用以调试500错误

# 配置CORS中间件 - 临时简化以调试500错误
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 临时使用简化配置
    allow_credentials=True,
    allow_methods=["*"],  # 临时使用简化配置
    allow_headers=["*"],  # 临时使用简化配置
    expose_headers=["*"]
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
            "message": f"未找到ID为{exc.asset_id} 的资产",
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


@app.exception_handler(JWTError)
async def jwt_exception_handler(request: Request, exc: JWTError):
    """处理JWT认证错误"""
    logger.warning(f"JWT authentication error: {exc}")
    return JSONResponse(
        status_code=401,
        content={
            "error": "Authentication Error",
            "message": "无效的认证令牌，请重新登录",
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
    print(f"=== 未捕获的异常 ===")
    print(f"请求URL: {request.url}")
    print(f"请求方法: {request.method}")
    print(f"异常类型: {type(exc)}")
    print(f"异常消息: {exc}")
    print(f"异常追踪:")
    traceback.print_exc()
    print(f"===================")

    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": f"服务器内部错误: {str(exc)}",
            "timestamp": datetime.now().isoformat(),
        }
    )


# 应用启动事件 - 临时简化以调试500错误
@app.on_event("startup")
async def startup_event():
    """应用启动时执行 - 简化版本"""
    logger.info("正在启动土地物业资产管理系统 (简化模式)...")

    # 仅创建数据库表
    try:
        create_tables()
        logger.info("数据库表创建成功")
    except Exception as e:
        logger.error(f"数据库表创建失败: {e}")
        raise

    # 暂时禁用其他启动组件以调试500错误
    # TODO: 重新启用后排查具体问题组件
    logger.info("土地物业资产管理系统启动完成 (简化模式)")


def validate_configurations():
    """验证关键配置参数"""
    # 验证SECRET_KEY
    if settings.SECRET_KEY == "your-secret-key-change-in-production":
        logger.warning("警告: 使用默认SECRET_KEY，生产环境应更换为安全密钥")
    
    # 验证数据库URL
    if "sqlite" in settings.DATABASE_URL and "test" not in settings.DATABASE_URL:
        logger.warning("警告: 使用SQLite数据库，生产环境建议使用PostgreSQL或MySQL")
    
    # 验证DEBUG模式
    if settings.DEBUG:
        logger.warning("警告: DEBUG模式已启用，生产环境应关闭DEBUG模式")
    
    # 验证CORS配置
    if "*" in settings.CORS_ORIGINS or "localhost" in ",".join(settings.CORS_ORIGINS):
        logger.warning("警告: CORS配置可能过于宽松，生产环境应限制具体域名")
    
    # 验证JWT配置
    if settings.ACCESS_TOKEN_EXPIRE_MINUTES > 1440:  # 24小时
        logger.warning("警告: 访问令牌过期时间过长，建议设置为较短时间以提高安全性")
    
    # 验证密码策略
    if settings.MIN_PASSWORD_LENGTH < 8:
        logger.warning("警告: 密码最小长度过短，建议至少8位")
    
    # 验证会话配置
    if settings.SESSION_EXPIRE_DAYS > 30:
        logger.warning("警告: 会话过期时间过长，建议设置为较短时间以提高安全性")
    
    # 验证上传配置
    if settings.MAX_FILE_SIZE > 52428800:  # 50MB
        logger.warning("警告: 最大文件上传大小超过50MB，可能影响系统性能")
    
    logger.info("配置验证完成")


# 应用关闭事件
@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行"""
    logger.info("土地物业资产管理系统正在关闭...")

    # 停止安全监控
    from .services.security_monitor import security_monitor
    await security_monitor.stop_monitoring()

    # 关闭缓存连接
    try:
        await cache_manager.close()
        logger.info("缓存连接已关闭")
    except Exception as e:
        logger.warning(f"关闭缓存连接失败: {e}")


# 导入并包含API路由
from .api import api_router
from .api.v1 import auth as auth_api
from .api.v1 import export as export_api
from .api.v1 import monitoring as monitoring_api
# from .api.v1 import chinese_ocr as chinese_ocr_api  # 已删除
# from .api.v1 import next_gen_pdf_import as next_gen_pdf_api  # 暂时禁用

# 调试：检查enum-field路由是否正确加载
enum_routes = [r for r in api_router.routes if hasattr(r, 'path') and 'enum' in r.path]
logger.info(f"Loading {len(enum_routes)} enum-field routes:")
for route in enum_routes[:5]:  # 只显示前5个
    logger.info(f"  - {route.path}: {route.methods}")

app.include_router(api_router)
app.include_router(auth_api.router, prefix="/api/v1/auth", tags=["认证管理"])
app.include_router(export_api.router, prefix="/api/v1/export", tags=["数据导出"])
app.include_router(monitoring_api.router, prefix="/api/v1/monitoring", tags=["系统监控"])
# app.include_router(chinese_ocr_api.router, prefix="/api/v1/chinese_ocr", tags=["中文OCR服务"])  # 已删除
# app.include_router(next_gen_pdf_api.router, prefix="/api/v1", tags=["下一代PDF智能导入"])  # 暂时禁用

# 添加租赁合同扫描件API（专用）
# from .api.v1 import rental_contract_scanner as rental_scanner_api  # 暂时注释，有导入错误
# app.include_router(rental_scanner_api.router, prefix="/api/v1", tags=["租赁合同扫描件"])

# 添加统一PDF导入API（通用）
# from .api.v1 import unified_pdf_import as unified_pdf_api  # 暂时注释，有导入错误
# app.include_router(unified_pdf_api.router, prefix="/api/v1", tags=["统一PDF导入"])


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


@app.get("/test-api", tags=["基础"])
async def test_api():
    """API测试端点"""
    try:
        from .database import SessionLocal
        from .models.asset import Asset

        db = SessionLocal()
        try:
            asset_count = db.query(Asset).count()
            return {
                "success": True,
                "message": "API测试成功",
                "database_status": "正常",
                "asset_count": asset_count,
                "timestamp": datetime.now().isoformat()
            }
        finally:
            db.close()
    except Exception as e:
        return {
            "success": False,
            "message": f"API测试失败: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8002,
        reload=True,
        log_level="info",
    )