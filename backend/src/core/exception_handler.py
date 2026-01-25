from typing import Any, NoReturn

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
from sqlalchemy.exc import IntegrityError

from ..constants.message_constants import ErrorMessages

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
        field_errors: dict[str, list[str]] | None = None,
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
        message = (
            f"{resource_type}{ErrorMessages.RESOURCE_NOT_FOUND.replace('资源', '')}"
        )
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
        message = f"{resource_type}{ErrorMessages.RESOURCE_ALREADY_EXISTS.replace('资源', '')}，{field}: {value}"

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
        message: str | None = None,
        required_permission: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message or ErrorMessages.PERMISSION_DENIED,
            code="PERMISSION_DENIED",
            details={"required_permission": required_permission, **(details or {})},
            status_code=status.HTTP_403_FORBIDDEN,
        )


class AuthenticationError(BaseBusinessError):
    """认证异常"""

    def __init__(
        self,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message or ErrorMessages.AUTHENTICATION_FAILED,
            code="AUTHENTICATION_ERROR",
            details=details,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class InvalidRequestError(BaseBusinessError):
    """错误请求异常"""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        detail_payload: dict[str, Any] = {}
        if field:
            detail_payload["field"] = field
        if details:
            detail_payload.update(details)
        super().__init__(
            message=message,
            code="INVALID_REQUEST",
            details=detail_payload,
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class ResourceConflictError(BaseBusinessError):
    """资源冲突异常"""

    def __init__(
        self,
        message: str,
        resource_type: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        payload = {"resource_type": resource_type} if resource_type else {}
        if details:
            payload.update(details)
        super().__init__(
            message=message,
            code="RESOURCE_CONFLICT",
            details=payload,
            status_code=status.HTTP_409_CONFLICT,
        )


class ServiceUnavailableError(BaseBusinessError):
    """服务不可用异常"""

    def __init__(
        self,
        message: str,
        service_name: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        payload = {"service": service_name} if service_name else {}
        if details:
            payload.update(details)
        super().__init__(
            message=message,
            code="SERVICE_UNAVAILABLE",
            details=payload,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


class OperationNotAllowedError(BaseBusinessError):
    """业务操作不允许异常"""

    def __init__(
        self,
        message: str,
        reason: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        payload = {"reason": reason} if reason else {}
        if details:
            payload.update(details)
        super().__init__(
            message=message,
            code="OPERATION_NOT_ALLOWED",
            details=payload,
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class InternalServerError(BaseBusinessError):
    """内部服务器异常"""

    def __init__(
        self,
        message: str,
        original_error: Exception | None = None,
        details: dict[str, Any] | None = None,
    ):
        payload = {"original_error": str(original_error)} if original_error else {}
        if details:
            payload.update(details)
        super().__init__(
            message=message,
            code="INTERNAL_SERVER_ERROR",
            details=payload,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
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

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)

    def handle_business_exception(
        self, request: Request, exc: BaseBusinessError
    ) -> JSONResponse:
        """处理业务异常"""
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

        response_data = {
            "success": False,
            "message": exc.message,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": safe_details,
            },
            "timestamp": exc.timestamp.isoformat(),
            "request_id": self._get_request_id(request),
        }

        return JSONResponse(status_code=exc.status_code, content=response_data)

    def _sanitize_exception_details(
        self, details: dict[str, Any]
    ) -> dict[str, Any] | str | None:
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
                elif isinstance(value, list | dict):
                    # 递归清理嵌套结构
                    cleaned_error[key] = self._clean_for_serialization(
                        value
                    )  # pragma: no cover
                else:
                    cleaned_error[key] = value
            cleaned_errors.append(cleaned_error)

        field_errors: dict[str, list[str]] = {}
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

    def _clean_for_serialization(self, obj: Any) -> Any:
        """递归清理对象以便JSON序列化"""
        from decimal import Decimal

        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, bytes):
            # Handle bytes by decoding to string, or return hex representation
            try:
                return obj.decode("utf-8")
            except UnicodeDecodeError:
                return obj.hex()
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

        message = "内部服务器错误"
        details: dict[str, Any] = {}

        business_exc = BaseBusinessError(
            message=message,
            code="INTERNAL_SERVER_ERROR",
            details=details,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

        return self.handle_business_exception(request, business_exc)

    def _get_request_id(self, request: Request) -> str | None:
        request_id = getattr(request.state, "request_id", None)
        if isinstance(request_id, str) and request_id:
            return request_id

        header_id = request.headers.get("X-Request-ID")
        if header_id:
            return header_id

        return request.headers.get("Request-ID")


# 全局异常处理器实例
exception_handler = ExceptionHandler()


def handle_service_exception(
    error: Exception, service_name: str, operation: str
) -> None:
    logger.error(f"{service_name} - {operation} failed", exc_info=error)

    if isinstance(error, IntegrityError):
        error_message = str(error).lower()
        if "unique constraint" in error_message or "unique violation" in error_message:
            raise DuplicateResourceError(service_name, "id", "duplicate")
        raise BusinessValidationError("数据完整性错误")

    if isinstance(error, ValueError | TypeError):
        raise BusinessValidationError("数据验证失败")

    raise error


def not_found(
    message: str = "资源未找到",
    *,
    resource_type: str | None = None,
    resource_id: str | None = None,
) -> BaseBusinessError:
    if resource_type:
        return ResourceNotFoundError(resource_type, resource_id)

    return BaseBusinessError(
        message=message,
        code="RESOURCE_NOT_FOUND",
        details={"resource_id": resource_id} if resource_id else {},
        status_code=status.HTTP_404_NOT_FOUND,
    )


def bad_request(
    message: str,
    *,
    field: str | None = None,
    details: str | dict[str, Any] | list[str] | None = None,
) -> BaseBusinessError:
    error_details: dict[str, Any] = {}
    if details is not None:
        error_details["details"] = details

    return InvalidRequestError(
        message=message,
        field=field,
        details=error_details or None,
    )


def validation_error(
    message: str = "数据验证失败",
    *,
    field_errors: list[str] | dict[str, str] | None = None,
) -> BaseBusinessError:
    if isinstance(field_errors, dict):
        normalized_field_errors = {
            field: [error] for field, error in field_errors.items()
        }
    elif isinstance(field_errors, list):
        normalized_field_errors = {"_errors": field_errors}
    else:
        normalized_field_errors = {}

    return BusinessValidationError(
        message=message,
        field_errors=normalized_field_errors,
    )


def unauthorized(message: str = "未授权，请登录") -> BaseBusinessError:
    return AuthenticationError(message=message)


def forbidden(message: str = "权限不足") -> BaseBusinessError:
    return PermissionDeniedError(message=message)


def conflict(
    message: str,
    *,
    resource_type: str | None = None,
) -> BaseBusinessError:
    return ResourceConflictError(
        message=message,
        resource_type=resource_type,
    )


def internal_error(
    message: str = "服务器内部错误",
    *,
    original_error: Exception | None = None,
) -> BaseBusinessError:
    return InternalServerError(
        message=message,
        original_error=original_error,
    )


def service_unavailable(
    message: str = "服务暂时不可用",
    *,
    service_name: str | None = None,
) -> BaseBusinessError:
    return ServiceUnavailableError(
        message=message,
        service_name=service_name,
    )


def operation_not_allowed(
    message: str,
    *,
    reason: str | None = None,
) -> BaseBusinessError:
    return OperationNotAllowedError(
        message=message,
        reason=reason,
    )


def setup_exception_handlers(app: Any) -> None:
    """设置应用异常处理器"""

    # 业务异常处理器
    @app.exception_handler(BaseBusinessError)  # type: ignore[misc]
    async def business_exception_handler(
        request: Request, exc: BaseBusinessError
    ) -> JSONResponse:
        return exception_handler.handle_business_exception(request, exc)

    # FastAPI验证异常处理器
    @app.exception_handler(RequestValidationError)  # type: ignore[misc]
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return exception_handler.handle_validation_exception(
            request, exc
        )  # pragma: no cover

    # HTTP异常处理器
    @app.exception_handler(HTTPException)  # type: ignore[misc]
    async def http_exception_handler(
        request: Request, exc: HTTPException
    ) -> JSONResponse:
        return exception_handler.handle_http_exception(request, exc)  # pragma: no cover

    # 通用异常处理器
    @app.exception_handler(Exception)  # type: ignore[misc]
    async def general_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        return exception_handler.handle_general_exception(
            request, exc
        )  # pragma: no cover


# 便捷异常抛出函数
def raise_not_found(
    resource_type: str, resource_id: str | None = None, **kwargs: Any
) -> NoReturn:
    """抛出资源未找到异常"""
    raise ResourceNotFoundError(resource_type, resource_id, kwargs)


def raise_duplicate(
    resource_type: str, field: str, value: str, **kwargs: Any
) -> NoReturn:
    """抛出资源重复异常"""
    raise DuplicateResourceError(resource_type, field, value, kwargs)


def raise_permission_denied(
    message: str | None = None, required_permission: str | None = None, **kwargs: Any
) -> NoReturn:
    """抛出权限不足异常"""
    raise PermissionDeniedError(message or "权限不足", required_permission, kwargs)


def raise_validation_error(
    message: str, field_errors: dict[str, list[str]] | None = None, **kwargs: Any
) -> NoReturn:
    """抛出验证异常"""
    raise BusinessValidationError(message, field_errors, kwargs)


def raise_file_error(
    message: str,
    file_name: str | None = None,
    file_type: str | None = None,
    **kwargs: Any,
) -> NoReturn:
    """抛出文件处理异常"""
    raise FileProcessingError(message, file_name, file_type, kwargs)


def raise_task_error(
    message: str,
    task_id: str | None = None,
    task_type: str | None = None,
    **kwargs: Any,
) -> NoReturn:
    """抛出任务处理异常"""
    raise TaskProcessingError(message, task_id, task_type, kwargs)


def raise_config_error(
    message: str, config_key: str | None = None, **kwargs: Any
) -> NoReturn:
    """抛出配置异常"""
    raise ConfigurationError(message, config_key, kwargs)


def raise_external_service_error(
    message: str, service_name: str | None = None, **kwargs: Any
) -> NoReturn:
    """抛出外部服务异常"""
    raise ExternalServiceError(message, service_name, **kwargs)


def raise_rate_limit(retry_after: int | None = None, **kwargs: Any) -> NoReturn:
    """抛出频率限制异常"""
    raise RateLimitError(retry_after=retry_after, **kwargs)


if __name__ == "__main__":
    # 测试异常处理
    try:
        raise_not_found("Asset", "123", reason="测试")
    except BaseBusinessError as e:
        logger.error(f"Exception handled: {e.to_dict()}")
