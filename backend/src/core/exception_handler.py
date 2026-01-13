from typing import Any

"""
统一异常处理机制
提供标准化的异常定义、处理和响应格式
"""

import logging
import traceback
from datetime import UTC, datetime

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class BaseBusinessError(Exception):
    """业务异常基类"""

    def __init__(
        self,
        message: str,
        code: str = "BUSINESS_ERROR",
        details: dict[str, Any] | None = None,
        status_code: int = status.HTTP_400_BAD_REQUEST,
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        self.status_code = status_code
        self.timestamp = datetime.now(UTC)
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "success": False,
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
                "timestamp": self.timestamp.isoformat(),
            },
        }


class BusinessValidationError(BaseBusinessError):
    """数据验证异常"""

    def __init__(
        self,
        message: str,
        field_errors: dict[str, list] | None = None,
        details: dict[str, Any] | None = None,
    ):
        self.field_errors = field_errors or {}
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            details={"field_errors": self.field_errors, **(details or {})},
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


class ResourceNotFoundError(BaseBusinessError):
    """资源未找到异常"""

    def __init__(
        self,
        resource_type: str,
        resource_id: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        message = f"{resource_type}未找到"
        if resource_id:
            message += f" (ID: {resource_id})"

        super().__init__(
            message=message,
            code="RESOURCE_NOT_FOUND",
            details={
                "resource_type": resource_type,
                "resource_id": resource_id,
                **(details or {}),
            },
            status_code=status.HTTP_404_NOT_FOUND,
        )


class DuplicateResourceError(BaseBusinessError):
    """资源重复异常"""

    def __init__(
        self,
        resource_type: str,
        field: str,
        value: str,
        details: dict[str, Any] | None = None,
    ):
        message = f"{resource_type}已存在，{field}: {value}"

        super().__init__(
            message=message,
            code="DUPLICATE_RESOURCE",
            details={
                "resource_type": resource_type,
                "field": field,
                "value": value,
                **(details or {}),
            },
            status_code=status.HTTP_409_CONFLICT,
        )


class PermissionDeniedError(BaseBusinessError):
    """权限不足异常"""

    def __init__(
        self,
        message: str = "权限不足",
        required_permission: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            code="PERMISSION_DENIED",
            details={"required_permission": required_permission, **(details or {})},
            status_code=status.HTTP_403_FORBIDDEN,
        )


class AuthenticationError(BaseBusinessError):
    """认证异常"""

    def __init__(
        self, message: str = "认证失败", details: dict[str, Any] | None = None
    ):
        super().__init__(
            message=message,
            code="AUTHENTICATION_ERROR",
            details=details,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class FileProcessingError(BaseBusinessError):
    """文件处理异常"""

    def __init__(
        self,
        message: str,
        file_name: str | None = None,
        file_type: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            code="FILE_PROCESSING_ERROR",
            details={"file_name": file_name, "file_type": file_type, **(details or {})},
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class TaskProcessingError(BaseBusinessError):
    """任务处理异常"""

    def __init__(
        self,
        message: str,
        task_id: str | None = None,
        task_type: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            code="TASK_PROCESSING_ERROR",
            details={"task_id": task_id, "task_type": task_type, **(details or {})},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class ConfigurationError(BaseBusinessError):
    """配置异常"""

    def __init__(
        self,
        message: str,
        config_key: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            code="CONFIGURATION_ERROR",
            details={"config_key": config_key, **(details or {})},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class ExternalServiceError(BaseBusinessError):
    """外部服务异常"""

    def __init__(
        self,
        message: str,
        service_name: str | None = None,
        service_error: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            code="EXTERNAL_SERVICE_ERROR",
            details={
                "service_name": service_name,
                "service_error": service_error,
                **(details or {}),
            },
            status_code=status.HTTP_502_BAD_GATEWAY,
        )


class RateLimitError(BaseBusinessError):
    """频率限制异常"""

    def __init__(
        self,
        message: str = "请求过于频繁，请稍后再试",
        retry_after: int | None = None,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            code="RATE_LIMIT_EXCEEDED",
            details={"retry_after": retry_after, **(details or {})},
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )


class ExceptionHandler:
    """统一异常处理器"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def handle_business_exception(
        self, request: Request, exc: BaseBusinessError
    ) -> JSONResponse:
        """处理业务异常"""
        # 清理异常详情中的不可序列化内容
        safe_details = self._sanitize_exception_details(exc.details)

        self.logger.warning(
            f"Business exception: {exc.code} - {exc.message}",
            extra={
                "exception_code": exc.code,
                "exception_details": safe_details,
                "request_path": str(request.url.path),
                "request_method": request.method,
            },
        )

        return JSONResponse(status_code=exc.status_code, content=exc.to_dict())

    def _sanitize_exception_details(self, details):
        """清理异常详情中的不可序列化内容"""
        if details is None:
            return None

        try:
            import json

            # 测试序列化
            json.dumps(details)
            return details
        except (TypeError, ValueError):
            # 如果无法序列化，转换为字符串
            try:
                details_str = str(details)
                # 限制长度
                if len(details_str) > 200:
                    details_str = details_str[:200] + "...(截断)"
                return details_str
            except Exception:  # pragma: no cover
                return "<无法序列化的异常详情>"  # pragma: no cover

    def handle_validation_exception(
        self, request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """处理请求验证异常"""
        from decimal import Decimal

        # 清理错误详情，移除不可序列化的对象
        cleaned_errors = []
        for error in exc.errors():
            cleaned_error = {}
            for key, value in error.items():
                # 跳过'input'字段，因为它可能包含不可序列化的Decimal对象
                if key == "input":  # pragma: no cover
                    continue  # pragma: no cover
                # 对于其他字段，转换Decimal为float
                if isinstance(value, Decimal):
                    cleaned_error[key] = float(value)
                elif isinstance(value, (list[Any], dict)):
                    # 递归清理嵌套结构
                    cleaned_error[key] = self._clean_for_serialization(
                        value
                    )  # pragma: no cover
                else:
                    cleaned_error[key] = value
            cleaned_errors.append(cleaned_error)

        field_errors = {}
        for error in exc.errors():
            field_name = ".".join(str(loc) for loc in error["loc"])
            if field_name not in field_errors:
                field_errors[field_name] = []
            field_errors[field_name].append(error["msg"])

        business_exc = BusinessValidationError(
            message="请求参数验证失败",
            field_errors=field_errors,
            details={"errors": cleaned_errors},
        )

        return self.handle_business_exception(request, business_exc)

    def _clean_for_serialization(self, obj):
        """递归清理对象以便JSON序列化"""
        from decimal import Decimal

        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, dict):
            return {k: self._clean_for_serialization(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._clean_for_serialization(item) for item in obj]
        elif isinstance(obj, tuple):
            return tuple(self._clean_for_serialization(item) for item in obj)
        elif isinstance(obj, BaseException):
            # Handle exception objects
            return {
                "type": type(obj).__name__,
                "message": str(obj)[:500],
            }
        else:
            return obj

    def handle_pydantic_validation_exception(  # pragma: no cover
        self,
        request: Request,
        exc: BusinessValidationError,  # pragma: no cover
    ) -> JSONResponse:  # pragma: no cover
        """处理Pydantic验证异常"""
        field_errors = {}  # pragma: no cover
        for error in exc.errors():  # pragma: no cover
            field_name = ".".join(str(loc) for loc in error["loc"])  # pragma: no cover
            if field_name not in field_errors:  # pragma: no cover
                field_errors[field_name] = []  # pragma: no cover
            field_errors[field_name].append(error["msg"])  # pragma: no cover

        business_exc = BusinessValidationError(  # pragma: no cover
            message="数据验证失败",  # pragma: no cover
            field_errors=field_errors,  # pragma: no cover
            details={"errors": exc.errors()},  # pragma: no cover
        )  # pragma: no cover

        return self.handle_business_exception(request, business_exc)  # pragma: no cover

    def handle_http_exception(
        self, request: Request, exc: HTTPException
    ) -> JSONResponse:
        """处理HTTP异常"""
        business_exc = BaseBusinessError(
            message=exc.detail,
            code=f"HTTP_{exc.status_code}",
            status_code=exc.status_code,
        )

        return self.handle_business_exception(request, business_exc)

    def handle_general_exception(
        self, request: Request, exc: Exception
    ) -> JSONResponse:
        """处理通用异常"""
        # 记录完整的错误堆栈
        self.logger.error(
            f"Unhandled exception: {type(exc).__name__} - {str(exc)}",
            extra={
                "exception_type": type(exc).__name__,
                "exception_message": str(exc),
                "request_path": str(request.url.path),
                "request_method": request.method,
                "traceback": traceback.format_exc(),
            },
        )

        # 根据环境决定是否暴露详细错误信息
        from .config import get_config

        debug_mode = get_config("debug", True)

        if debug_mode:
            message = f"内部服务器错误: {str(exc)}"
            details = {
                "exception_type": type(exc).__name__,
                "traceback": traceback.format_exc(),
            }
        else:
            message = "内部服务器错误"
            details = {}

        business_exc = BaseBusinessError(
            message=message,
            code="INTERNAL_SERVER_ERROR",
            details=details,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

        return self.handle_business_exception(request, business_exc)


# 全局异常处理器实例
exception_handler = ExceptionHandler()


def setup_exception_handlers(app):
    """设置应用异常处理器"""

    # 业务异常处理器
    @app.exception_handler(BaseBusinessError)
    async def business_exception_handler(request: Request, exc: BaseBusinessError):
        return exception_handler.handle_business_exception(request, exc)

    # FastAPI验证异常处理器
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        return exception_handler.handle_validation_exception(
            request, exc
        )  # pragma: no cover

    # Pydantic验证异常处理器
    @app.exception_handler(BusinessValidationError)
    async def pydantic_validation_exception_handler(
        request: Request, exc: BusinessValidationError
    ):
        return exception_handler.handle_pydantic_validation_exception(
            request, exc
        )  # pragma: no cover

    # HTTP异常处理器
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return exception_handler.handle_http_exception(request, exc)  # pragma: no cover

    # 通用异常处理器
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        return exception_handler.handle_general_exception(
            request, exc
        )  # pragma: no cover


# 便捷异常抛出函数
def raise_not_found(resource_type: str, resource_id: str | None = None, **kwargs):
    """抛出资源未找到异常"""
    raise ResourceNotFoundError(resource_type, resource_id, kwargs)


def raise_duplicate(resource_type: str, field: str, value: str, **kwargs):
    """抛出资源重复异常"""
    raise DuplicateResourceError(resource_type, field, value, kwargs)


def raise_permission_denied(
    message: str | None = None, required_permission: str | None = None, **kwargs
):
    """抛出权限不足异常"""
    raise PermissionDeniedError(message or "权限不足", required_permission, kwargs)


def raise_validation_error(
    message: str, field_errors: dict[str, list] | None = None, **kwargs
):
    """抛出验证异常"""
    raise BusinessValidationError(message, field_errors, kwargs)


def raise_file_error(
    message: str, file_name: str | None = None, file_type: str | None = None, **kwargs
):
    """抛出文件处理异常"""
    raise FileProcessingError(message, file_name, file_type, kwargs)


def raise_task_error(
    message: str, task_id: str | None = None, task_type: str | None = None, **kwargs
):
    """抛出任务处理异常"""
    raise TaskProcessingError(message, task_id, task_type, kwargs)


def raise_config_error(message: str, config_key: str | None = None, **kwargs):
    """抛出配置异常"""
    raise ConfigurationError(message, config_key, kwargs)


def raise_external_service_error(
    message: str, service_name: str | None = None, **kwargs
):
    """抛出外部服务异常"""
    raise ExternalServiceError(message, service_name, **kwargs)


def raise_rate_limit(retry_after: int | None = None, **kwargs):
    """抛出频率限制异常"""
    raise RateLimitError(retry_after=retry_after, **kwargs)


if __name__ == "__main__":
    # 测试异常处理
    try:
        raise_not_found("Asset", "123", reason="测试")
    except BaseBusinessError as e:
        print("Exception handled:", e.to_dict())
