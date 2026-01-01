"""
统一错误处理系统
整合所有错误处理机制，提供一致的错误处理体验
"""

import logging
import traceback
from datetime import datetime
from enum import Enum
from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorCode(str, Enum):
    """统一错误码枚举"""

    # 通用错误 (1000-1999)
    INTERNAL_SERVER_ERROR = "E1000"
    INVALID_REQUEST = "E1001"
    VALIDATION_ERROR = "E1002"
    UNAUTHORIZED = "E1003"
    FORBIDDEN = "E1004"
    NOT_FOUND = "E1005"
    METHOD_NOT_ALLOWED = "E1006"
    TIMEOUT = "E1007"

    # 业务错误 (2000-2999)
    BUSINESS_ERROR = "E2000"
    RESOURCE_NOT_FOUND = "E2001"
    RESOURCE_ALREADY_EXISTS = "E2002"
    RESOURCE_CONFLICT = "E2003"
    OPERATION_NOT_ALLOWED = "E2004"
    INVALID_OPERATION = "E2005"

    # 数据验证错误 (3000-3999)
    DATA_VALIDATION_ERROR = "E3000"
    REQUIRED_FIELD_MISSING = "E3001"
    INVALID_FIELD_FORMAT = "E3002"
    FIELD_VALUE_OUT_OF_RANGE = "E3003"
    INVALID_DATE_FORMAT = "E3004"

    # 权限和认证错误 (4000-4999)
    AUTHENTICATION_FAILED = "E4000"
    TOKEN_EXPIRED = "E4001"
    TOKEN_INVALID = "E4002"
    INSUFFICIENT_PERMISSIONS = "E4003"
    ACCOUNT_LOCKED = "E4004"
    ACCOUNT_DISABLED = "E4005"

    # 外部服务错误 (5000-5999)
    EXTERNAL_SERVICE_ERROR = "E5000"
    DATABASE_ERROR = "E5001"
    FILE_UPLOAD_ERROR = "E5002"
    EMAIL_SERVICE_ERROR = "E5003"
    PDF_PROCESSING_ERROR = "E5004"


class ErrorSeverity(str, Enum):
    """错误严重程度"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorDetail(BaseModel):
    """错误详情模型"""

    field: str | None = None
    message: str
    code: str | None = None


class UnifiedErrorResponse(BaseModel):
    """统一错误响应模型"""

    success: bool = False
    error: dict[str, Any]
    timestamp: datetime
    request_id: str | None = None


class UnifiedError(Exception):
    """统一错误异常类"""

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.BUSINESS_ERROR,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: str | dict[str, Any] | list | None = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        extra_data: dict[str, Any] | None = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details
        self.severity = severity
        self.extra_data = extra_data or {}
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        error_data = {
            "code": self.code.value,
            "message": self.message,
            "severity": self.severity.value,
            "timestamp": datetime.utcnow().isoformat(),
            **self.extra_data,
        }

        if self.details:
            if isinstance(self.details, str):
                error_data["details"] = self.details
            elif isinstance(self.details, dict):
                error_data.update(self.details)
            elif isinstance(self.details, list):
                error_data["field_errors"] = self.details

        return error_data


class UnifiedErrorHandler:
    """统一错误处理器"""

    def __init__(self, logger: logging.Logger | None = None):
        self.logger = logger or logging.getLogger(__name__)
        self._setup_logger()

    def _setup_logger(self):
        """设置日志格式"""
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def handle_error(
        self, error: Exception, request: Request | None = None
    ) -> JSONResponse:
        """处理错误并返回统一响应"""

        request_id = getattr(request.state, "request_id", None) if request else None

        # 记录错误日志
        self._log_error(error, request)

        # 根据错误类型创建响应
        if isinstance(error, UnifiedError):
            error_data = error.to_dict()
            status_code = error.status_code
        elif isinstance(error, HTTPException):
            error_data = self._handle_http_exception(error)
            status_code = error.status_code
        elif isinstance(error, ValueError):
            error_data = self._handle_validation_error(error)
            status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
        else:
            error_data = self._handle_unknown_error(error)
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

        # 添加请求ID
        if request_id:
            error_data["request_id"] = request_id

        response = UnifiedErrorResponse(
            error=error_data, timestamp=datetime.utcnow(), request_id=request_id
        )

        return JSONResponse(
            status_code=status_code, content=response.model_dump(mode="json")
        )

    def _log_error(self, error: Exception, request: Request | None = None):
        """记录错误日志"""
        error_info = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": datetime.utcnow().isoformat(),
        }

        if request:
            error_info.update(
                {
                    "method": request.method,
                    "url": str(request.url),
                    "client_ip": request.client.host if request.client else None,
                    "user_agent": request.headers.get("user-agent"),
                }
            )

        # 根据错误严重程度选择日志级别
        if isinstance(error, UnifiedError):
            if error.severity == ErrorSeverity.CRITICAL:
                self.logger.critical("Critical error occurred", extra=error_info)
            elif error.severity == ErrorSeverity.HIGH:
                self.logger.error("High severity error occurred", extra=error_info)
            elif error.severity == ErrorSeverity.MEDIUM:
                self.logger.warning("Medium severity error occurred", extra=error_info)
            else:
                self.logger.info("Low severity error occurred", extra=error_info)
        else:
            self.logger.error("Unexpected error occurred", extra=error_info)

        # 记录详细的堆栈跟踪
        if not isinstance(error, (UnifiedError, HTTPException)):
            self.logger.debug(f"Error traceback: {traceback.format_exc()}")

    def _handle_http_exception(self, error: HTTPException) -> dict[str, Any]:
        """处理HTTP异常"""
        return {
            "code": f"E{error.status_code}",
            "message": error.detail,
            "severity": ErrorSeverity.MEDIUM.value,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def _handle_validation_error(self, error: ValueError) -> dict[str, Any]:
        """处理验证错误"""
        return {
            "code": ErrorCode.DATA_VALIDATION_ERROR.value,
            "message": "数据验证失败",
            "details": str(error),
            "severity": ErrorSeverity.MEDIUM.value,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def _handle_unknown_error(self, error: Exception) -> dict[str, Any]:
        """处理未知错误"""
        return {
            "code": ErrorCode.INTERNAL_SERVER_ERROR.value,
            "message": "服务器内部错误",
            "details": str(error) if self._is_development() else None,
            "severity": ErrorSeverity.HIGH.value,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def _is_development(self) -> bool:
        """检查是否为开发环境"""
        import os

        return os.getenv("ENVIRONMENT", "development").lower() == "development"


# 创建全局错误处理器实例
unified_error_handler = UnifiedErrorHandler()


# 便捷的错误创建函数
def create_business_error(
    message: str,
    code: ErrorCode = ErrorCode.BUSINESS_ERROR,
    details: Any | None = None,
) -> UnifiedError:
    """创建业务错误"""
    return UnifiedError(
        message=message,
        code=code,
        status_code=status.HTTP_400_BAD_REQUEST,
        details=details,
        severity=ErrorSeverity.MEDIUM,
    )


def create_not_found_error(
    message: str = "资源未找到", resource_type: str | None = None
) -> UnifiedError:
    """创建资源未找到错误"""
    extra_data = {}
    if resource_type:
        extra_data["resource_type"] = resource_type

    return UnifiedError(
        message=message,
        code=ErrorCode.RESOURCE_NOT_FOUND,
        status_code=status.HTTP_404_NOT_FOUND,
        severity=ErrorSeverity.LOW,
        extra_data=extra_data,
    )


def create_validation_error(
    message: str, field_errors: list | None = None
) -> UnifiedError:
    """创建验证错误"""
    return UnifiedError(
        message=message,
        code=ErrorCode.DATA_VALIDATION_ERROR,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        details=field_errors,
        severity=ErrorSeverity.MEDIUM,
    )


def create_authentication_error(message: str = "认证失败") -> UnifiedError:
    """创建认证错误"""
    return UnifiedError(
        message=message,
        code=ErrorCode.AUTHENTICATION_FAILED,
        status_code=status.HTTP_401_UNAUTHORIZED,
        severity=ErrorSeverity.HIGH,
    )


def create_authorization_error(message: str = "权限不足") -> UnifiedError:
    """创建授权错误"""
    return UnifiedError(
        message=message,
        code=ErrorCode.INSUFFICIENT_PERMISSIONS,
        status_code=status.HTTP_403_FORBIDDEN,
        severity=ErrorSeverity.HIGH,
    )


def create_internal_error(
    message: str = "服务器内部错误", original_error: Exception | None = None
) -> UnifiedError:
    """创建内部服务器错误"""
    extra_data = {}
    if original_error:
        extra_data["original_error"] = str(original_error)

    return UnifiedError(
        message=message,
        code=ErrorCode.INTERNAL_SERVER_ERROR,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        severity=ErrorSeverity.CRITICAL,
        extra_data=extra_data,
    )


class ErrorHandler:
    """统一错误处理器类"""

    def __init__(self, logger_name: str = "unified_error_handler"):
        self.logger = logging.getLogger(logger_name)
        self.error_handlers = {
            UnifiedError: self._handle_unified_error,
            HTTPException: self._handle_http_exception,
            ValueError: self._handle_validation_error,
            Exception: self._handle_unknown_error,
        }

    def handle_error(
        self, error: Exception, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """处理错误并返回标准化响应"""
        error_type = type(error)
        handler = self.error_handlers.get(error_type, self._handle_unknown_error)

        error_response = handler(error)

        if context:
            error_response["context"] = context

        # 记录错误
        self._log_error(error, error_response)

        return error_response

    def _handle_unified_error(self, error: UnifiedError) -> dict[str, Any]:
        """处理统一错误"""
        return {
            "code": error.code.value,
            "message": error.message,
            "details": error.details,
            "severity": error.severity.value,
            "timestamp": datetime.utcnow().isoformat(),
            "extra_data": error.extra_data,
        }

    def _handle_http_exception(self, error: HTTPException) -> dict[str, Any]:
        """处理HTTP异常"""
        return {
            "code": f"E{error.status_code}",
            "message": error.detail,
            "severity": ErrorSeverity.MEDIUM.value,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def _handle_validation_error(self, error: ValueError) -> dict[str, Any]:
        """处理验证错误"""
        return {
            "code": ErrorCode.DATA_VALIDATION_ERROR.value,
            "message": "数据验证失败",
            "details": str(error),
            "severity": ErrorSeverity.MEDIUM.value,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def _handle_unknown_error(self, error: Exception) -> dict[str, Any]:
        """处理未知错误"""
        return {
            "code": ErrorCode.INTERNAL_SERVER_ERROR.value,
            "message": "服务器内部错误",
            "details": str(error) if self._is_development() else None,
            "severity": ErrorSeverity.HIGH.value,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def _log_error(self, error: Exception, error_response: dict[str, Any]):
        """记录错误日志"""
        error_info = {
            "error_type": type(error).__name__,
            "error_code": error_response["code"],
            "error_message": error_response["message"],
            "severity": error_response["severity"],
        }

        if isinstance(error, UnifiedError):
            if error.severity == ErrorSeverity.CRITICAL:
                self.logger.critical("Critical error occurred", extra=error_info)
            elif error.severity == ErrorSeverity.HIGH:
                self.logger.error("High severity error occurred", extra=error_info)
            elif error.severity == ErrorSeverity.MEDIUM:
                self.logger.warning("Medium severity error occurred", extra=error_info)
            else:
                self.logger.info("Low severity error occurred", extra=error_info)
        else:
            self.logger.error("Unexpected error occurred", extra=error_info)

    def _is_development(self) -> bool:
        """检查是否为开发环境"""
        import os

        return os.getenv("ENVIRONMENT", "development").lower() == "development"
