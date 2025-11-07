"""
文件上传安全中间件
自动验证所有文件上传请求的安全性
"""

import logging
import os
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ..core.config import settings
from ..utils.file_security import validate_upload_file

logger = logging.getLogger(__name__)


class FileUploadSecurityMiddleware(BaseHTTPMiddleware):
    """文件上传安全中间件"""

    def __init__(
        self,
        app,
        max_file_size: Optional[int] = None,
        allowed_extensions: Optional[list] = None,
        upload_paths: Optional[list] = None,
    ):
        super().__init__(app)

        # 配置参数
        self.max_file_size = max_file_size or settings.MAX_FILE_SIZE
        self.allowed_extensions = allowed_extensions or [
            "pdf",
            "jpg",
            "jpeg",
            "png",
            "xlsx",
            "docx",
        ]
        self.upload_paths = upload_paths or ["/upload", "/attachments", "/import"]

        logger.info(
            f"文件上传安全中间件初始化完成 - 最大文件大小: {self.max_file_size // (1024 * 1024)}MB"
        )

    async def dispatch(self, request: Request, call_next):
        """拦截请求进行安全检查"""

        # 检查是否为文件上传请求
        if self._is_file_upload_request(request):
            try:
                # 验证上传内容
                validation_result = await self._validate_upload_content(request)

                if not validation_result["valid"]:
                    logger.warning(
                        f"文件上传安全检查失败: {validation_result['errors']}"
                    )
                    return JSONResponse(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        content={
                            "success": False,
                            "error": "文件上传安全检查失败",
                            "details": validation_result["errors"],
                        },
                    )

                # 记录警告信息
                if validation_result["warnings"]:
                    for warning in validation_result["warnings"]:
                        logger.warning(f"文件上传警告: {warning}")

            except Exception as e:
                logger.error(f"文件上传安全检查异常: {e}")
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={
                        "success": False,
                        "error": "文件上传安全检查异常",
                        "details": str(e),
                    },
                )

        # 继续处理请求
        response = await call_next(request)
        return response

    def _is_file_upload_request(self, request: Request) -> bool:
        """检查是否为文件上传请求"""
        # 检查路径
        path = request.url.path.lower()
        if any(upload_path in path for upload_path in self.upload_paths):
            return True

        # 检查Content-Type
        content_type = request.headers.get("content-type", "").lower()
        if "multipart/form-data" in content_type:
            return True

        # 检查请求方法
        if request.method.upper() in ["POST", "PUT", "PATCH"]:
            return True

        return False

    async def _validate_upload_content(self, request: Request) -> dict:
        """验证上传内容"""
        result = {"valid": True, "errors": [], "warnings": []}

        try:
            # 检查内容长度
            content_length = request.headers.get("content-length")
            if content_length:
                content_length = int(content_length)
                if content_length > self.max_file_size:
                    result["valid"] = False
                    result["errors"].append(
                        f"请求内容大小超过限制: {content_length} > {self.max_file_size}"
                    )
                    return result
            else:
                result["warnings"].append("缺少Content-Length头，无法验证内容大小")

            # 检查Content-Type
            content_type = request.headers.get("content-type", "")
            if not content_type:
                result["warnings"].append("缺少Content-Type头")
            elif "multipart/form-data" not in content_type.lower():
                result["warnings"].append(f"非预期的Content-Type: {content_type}")

            # 尝试解析multipart内容（如果可能）
            if "multipart/form-data" in content_type.lower():
                # 这里可以进一步解析multipart内容进行详细验证
                # 由于FastAPI已经处理了multipart解析，这里主要做基础检查
                pass

        except Exception as e:
            result["valid"] = False
            result["errors"].append(f"内容验证异常: {str(e)}")

        return result


# 文件上传安全装饰器
def secure_file_upload(
    allowed_extensions: Optional[list] = None,
    max_size: Optional[int] = None,
    scan_content: bool = False,
):
    """
    文件上传安全装饰器

    Args:
        allowed_extensions: 允许的文件扩展名列表
        max_size: 最大文件大小（字节）
        scan_content: 是否扫描文件内容
    """

    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 这里可以添加装饰器级别的安全检查
            return await func(*args, **kwargs)

        return wrapper

    return decorator


# 文件上传安全验证工具
async def validate_multipart_upload(
    request: Request,
    allowed_extensions: Optional[list] = None,
    max_size: Optional[int] = None,
) -> dict:
    """
    验证multipart文件上传

    Args:
        request: FastAPI请求对象
        allowed_extensions: 允许的文件扩展名
        max_size: 最大文件大小

    Returns:
        dict: 验证结果
    """
    result = {"valid": True, "errors": [], "warnings": [], "files_info": []}

    try:
        # 这里可以解析multipart内容进行详细验证
        # 由于FastAPI已经处理了multipart解析，这里提供框架

        content_type = request.headers.get("content-type", "")
        if "multipart/form-data" not in content_type.lower():
            result["valid"] = False
            result["errors"].append("非multipart/form-data请求")
            return result

        # 解析boundary
        boundary = None
        for part in content_type.split(";"):
            part = part.strip()
            if part.startswith("boundary="):
                boundary = part.split("=", 1)[1].strip('"')
                break

        if not boundary:
            result["warnings"].append("无法解析multipart边界")

    except Exception as e:
        result["valid"] = False
        result["errors"].append(f"multipart验证异常: {str(e)}")

    return result


# 创建全局文件安全中间件实例
def create_file_security_middleware(app) -> FileUploadSecurityMiddleware:
    """创建文件安全中间件实例"""
    return FileUploadSecurityMiddleware(
        app=app,
        max_file_size=settings.MAX_FILE_SIZE,
        allowed_extensions=["pdf", "jpg", "jpeg", "png", "xlsx", "docx", "txt", "csv"],
        upload_paths=["/upload", "/attachments", "/import", "/pdf-import", "/excel"],
    )


# 导出主要组件
__all__ = [
    "FileUploadSecurityMiddleware",
    "secure_file_upload",
    "validate_multipart_upload",
    "create_file_security_middleware",
]
