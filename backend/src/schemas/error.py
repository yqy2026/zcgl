#!/usr/bin/env python3
"""
统一错误响应模式
定义 PDF 处理和 OCR 相关的标准错误响应格式
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ============================================================================
# 错误码枚举
# ============================================================================

class ErrorCode(str, Enum):
    """标准错误码"""

    # 网络相关
    NETWORK_ERROR = "NETWORK_ERROR"
    API_TIMEOUT = "API_TIMEOUT"
    API_RATE_LIMIT = "API_RATE_LIMIT"
    API_KEY_INVALID = "API_KEY_INVALID"
    API_KEY_MISSING = "API_KEY_MISSING"

    # 文件相关
    INVALID_PDF = "INVALID_PDF"
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    CORRUPTED_FILE = "CORRUPTED_FILE"
    UNSUPPORTED_FILE_TYPE = "UNSUPPORTED_FILE_TYPE"

    # 服务相关
    OCR_UNAVAILABLE = "OCR_UNAVAILABLE"
    LLM_UNAVAILABLE = "LLM_UNAVAILABLE"
    VISION_UNAVAILABLE = "VISION_UNAVAILABLE"
    SERVICE_ERROR = "SERVICE_ERROR"
    SERVICE_OVERLOADED = "SERVICE_OVERLOADED"

    # 提取相关
    EXTRACTION_FAILED = "EXTRACTION_FAILED"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    NO_TEXT_DETECTED = "NO_TEXT_DETECTED"
    PARSE_ERROR = "PARSE_ERROR"
    INVALID_RESPONSE_FORMAT = "INVALID_RESPONSE_FORMAT"

    # 系统相关
    OUT_OF_MEMORY = "OUT_OF_MEMORY"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"

    # 会话相关
    SESSION_NOT_FOUND = "SESSION_NOT_FOUND"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    SESSION_ALREADY_PROCESSING = "SESSION_ALREADY_PROCESSING"


class ErrorSeverity(str, Enum):
    """错误严重程度"""
    LOW = "low"           # 可恢复，不影响主流程
    MEDIUM = "medium"     # 部分功能受限
    HIGH = "high"         # 严重错误，需要人工介入
    CRITICAL = "critical" # 系统级错误


# ============================================================================
# 基础错误响应
# ============================================================================

class ErrorResponse(BaseModel):
    """
    统一错误响应格式

    所有 API 错误应返回此格式
    """

    success: bool = Field(default=False, description="请求是否成功")
    error_code: ErrorCode = Field(description="错误码")
    error_message: str = Field(description="错误消息")
    error_type: Optional[str] = Field(None, description="异常类型名")
    severity: ErrorSeverity = Field(default=ErrorSeverity.MEDIUM, description="错误严重程度")

    # 重试建议
    retry_suggested: bool = Field(default=False, description="是否建议重试")
    retry_after_seconds: Optional[int] = Field(None, description="建议重试间隔（秒）")

    # 详细信息
    details: Optional[Dict[str, Any]] = Field(None, description="错误详情")
    stack_trace: Optional[str] = Field(None, description="堆栈跟踪（仅调试模式）")

    # 上下文
    request_id: Optional[str] = Field(None, description="请求 ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="错误时间")

    class Config:
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "success": False,
                "error_code": "API_TIMEOUT",
                "error_message": "Request timed out after 180 seconds",
                "severity": "medium",
                "retry_suggested": True,
                "retry_after_seconds": 5,
            }
        }


# ============================================================================
# 详细错误响应
# ============================================================================

class DetailedErrorResponse(ErrorResponse):
    """
    详细错误响应
    包含更多调试和上下文信息
    """

    # 错误来源
    source: str = Field(description="错误来源: api, service, database, external")

    # 相关资源
    session_id: Optional[str] = Field(None, description="相关的会话 ID")
    file_path: Optional[str] = Field(None, description="相关的文件路径")

    # 解决建议
    suggestions: List[str] = Field(default_factory=list, description="解决建议")

    # 支持信息
    support_url: Optional[str] = Field(None, description="支持文档 URL")
    issue_tracking_id: Optional[str] = Field(None, description="问题追踪 ID")

    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error_code": "OCR_UNAVAILABLE",
                "error_message": "OCR service is not available",
                "severity": "high",
                "source": "service",
                "retry_suggested": False,
                "suggestions": [
                    "Install OCR dependencies: uv sync --extra pdf-ocr",
                    "Check OCR service status: /api/v1/ocr/status",
                ],
            }
        }


# ============================================================================
# 批量错误响应
# ============================================================================

class BatchItemError(BaseModel):
    """批量操作中的单个错误"""

    index: int = Field(description="项目索引")
    identifier: Optional[str] = Field(None, description="项目标识符")
    error_code: ErrorCode = Field(description="错误码")
    error_message: str = Field(description="错误消息")


class BatchErrorResponse(ErrorResponse):
    """
    批量操作错误响应
    部分成功时的错误格式
    """

    total_count: int = Field(description="总项目数")
    success_count: int = Field(description="成功项目数")
    failed_count: int = Field(description="失败项目数")
    errors: List[BatchItemError] = Field(default_factory=list, description="失败项目详情")

    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error_code": "PARTIAL_FAILURE",
                "error_message": "3 out of 10 PDFs failed to process",
                "total_count": 10,
                "success_count": 7,
                "failed_count": 3,
                "errors": [
                    {
                        "index": 2,
                        "identifier": "file_2.pdf",
                        "error_code": "FILE_TOO_LARGE",
                        "error_message": "File size (80MB) exceeds limit (50MB)"
                    }
                ]
            }
        }


# ============================================================================
# 错误构建器
# ============================================================================

class ErrorBuilder:
    """
    错误响应构建器
    简化创建标准化错误响应
    """

    @staticmethod
    def network_error(
        message: str = "Network error occurred",
        details: Optional[Dict[str, Any]] = None,
        retry_after: int = 5,
    ) -> ErrorResponse:
        """创建网络错误响应"""
        return ErrorResponse(
            error_code=ErrorCode.NETWORK_ERROR,
            error_message=message,
            severity=ErrorSeverity.MEDIUM,
            retry_suggested=True,
            retry_after_seconds=retry_after,
            details=details,
        )

    @staticmethod
    def timeout_error(
        timeout_seconds: int,
        operation: str = "operation",
        details: Optional[Dict[str, Any]] = None,
    ) -> ErrorResponse:
        """创建超时错误响应"""
        return ErrorResponse(
            error_code=ErrorCode.API_TIMEOUT,
            error_message=f"{operation.capitalize()} timed out after {timeout_seconds} seconds",
            severity=ErrorSeverity.MEDIUM,
            retry_suggested=True,
            retry_after_seconds=10,
            details=details or {"timeout_seconds": timeout_seconds, "operation": operation},
        )

    @staticmethod
    def file_not_found(
        file_path: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> ErrorResponse:
        """创建文件未找到错误响应"""
        return ErrorResponse(
            error_code=ErrorCode.FILE_NOT_FOUND,
            error_message=f"File not found: {file_path}",
            severity=ErrorSeverity.HIGH,
            retry_suggested=False,
            details=details or {"file_path": file_path},
        )

    @staticmethod
    def file_too_large(
        file_size_mb: float,
        max_size_mb: int,
        details: Optional[Dict[str, Any]] = None,
    ) -> ErrorResponse:
        """创建文件过大错误响应"""
        return ErrorResponse(
            error_code=ErrorCode.FILE_TOO_LARGE,
            error_message=f"File size ({file_size_mb:.1f}MB) exceeds limit ({max_size_mb}MB)",
            severity=ErrorSeverity.MEDIUM,
            retry_suggested=False,
            details=details or {
                "file_size_mb": file_size_mb,
                "max_size_mb": max_size_mb,
            },
            suggestions=[
                f"Compress the PDF to under {max_size_mb}MB",
                f"Split the PDF into smaller files (max {max_size_mb}MB each)",
            ],
        )

    @staticmethod
    def ocr_unavailable(
        details: Optional[Dict[str, Any]] = None,
    ) -> DetailedErrorResponse:
        """创建 OCR 不可用错误响应"""
        return DetailedErrorResponse(
            error_code=ErrorCode.OCR_UNAVAILABLE,
            error_message="OCR service is not available",
            severity=ErrorSeverity.HIGH,
            source="service",
            retry_suggested=False,
            details=details,
            suggestions=[
                "Install OCR dependencies: uv sync --extra pdf-ocr",
                "Check OCR service status",
                "Use vision extraction as fallback",
            ],
        )

    @staticmethod
    def invalid_pdf(
        reason: str = "Invalid or corrupted PDF file",
        details: Optional[Dict[str, Any]] = None,
    ) -> ErrorResponse:
        """创建无效 PDF 错误响应"""
        return ErrorResponse(
            error_code=ErrorCode.INVALID_PDF,
            error_message=f"Invalid PDF: {reason}",
            severity=ErrorSeverity.HIGH,
            retry_suggested=False,
            details=details,
            suggestions=[
                "Verify the PDF file is not corrupted",
                "Try re-downloading or re-creating the PDF",
            ],
        )

    @staticmethod
    def extraction_failed(
        reason: str = "Failed to extract information from PDF",
        details: Optional[Dict[str, Any]] = None,
        confidence: Optional[float] = None,
    ) -> ErrorResponse:
        """创建提取失败错误响应"""
        error_response = ErrorResponse(
            error_code=ErrorCode.EXTRACTION_FAILED,
            error_message=reason,
            severity=ErrorSeverity.MEDIUM,
            retry_suggested=True,
            details=details,
        )
        if confidence is not None:
            error_response.details = error_response.details or {}
            error_response.details["confidence"] = confidence
        return error_response

    @staticmethod
    def low_confidence(
        confidence: float,
        threshold: float = 0.7,
        details: Optional[Dict[str, Any]] = None,
    ) -> ErrorResponse:
        """创建低置信度错误响应"""
        return ErrorResponse(
            error_code=ErrorCode.LOW_CONFIDENCE,
            error_message=f"Extraction confidence ({confidence:.2f}) below threshold ({threshold:.2f})",
            severity=ErrorSeverity.MEDIUM,
            retry_suggested=True,
            details=details or {
                "confidence": confidence,
                "threshold": threshold,
            },
            suggestions=[
                "Try using a different extraction method",
                "Verify the PDF quality",
                "Manually review and correct the extracted data",
            ],
        )

    @staticmethod
    def api_key_missing(
        service: str = "API",
        details: Optional[Dict[str, Any]] = None,
    ) -> ErrorResponse:
        """创建 API Key 缺失错误响应"""
        return ErrorResponse(
            error_code=ErrorCode.API_KEY_MISSING,
            error_message=f"{service} key not configured",
            severity=ErrorSeverity.HIGH,
            retry_suggested=False,
            details=details or {"service": service},
            suggestions=[
                f"Set {service.upper()}_API_KEY environment variable",
                f"Check configuration file",
            ],
        )

    @staticmethod
    def out_of_memory(
        details: Optional[Dict[str, Any]] = None,
    ) -> ErrorResponse:
        """创建内存不足错误响应"""
        return ErrorResponse(
            error_code=ErrorCode.OUT_OF_MEMORY,
            error_message="System out of memory",
            severity=ErrorSeverity.CRITICAL,
            retry_suggested=True,
            retry_after_seconds=60,
            details=details,
            suggestions=[
                "Reduce concurrent processing (OCR_MAX_CONCURRENT)",
                "Process smaller PDFs",
                "Increase system memory",
            ],
        )

    @staticmethod
    def internal_error(
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> ErrorResponse:
        """创建内部错误响应"""
        return ErrorResponse(
            error_code=ErrorCode.INTERNAL_ERROR,
            error_message=f"Internal error: {message}",
            severity=ErrorSeverity.HIGH,
            retry_suggested=True,
            details=details,
        )


# ============================================================================
# 错误转换工具
# ============================================================================

def exception_to_error_response(
    exception: Exception,
    request_id: Optional[str] = None,
    include_traceback: bool = False,
) -> ErrorResponse:
    """
    将异常转换为错误响应

    Args:
        exception: 异常对象
        request_id: 请求 ID
        include_traceback: 是否包含堆栈跟踪

    Returns:
        ErrorResponse: 错误响应
    """
    import traceback

    error_type = type(exception).__name__
    error_message = str(exception)

    # 根据异常类型确定错误码
    if isinstance(exception, (ConnectionError, httpx.NetworkError)):
        return ErrorBuilder.network_error(error_message)

    if isinstance(exception, (TimeoutError, httpx.TimeoutException)):
        return ErrorBuilder.timeout_error(180, "request")

    if isinstance(exception, FileNotFoundError):
        return ErrorBuilder.file_not_found(error_message)

    if isinstance(exception, MemoryError):
        return ErrorBuilder.out_of_memory()

    # 默认内部错误
    error_response = ErrorBuilder.internal_error(error_message)
    error_response.error_type = error_type
    error_response.request_id = request_id

    if include_traceback:
        error_response.stack_trace = traceback.format_exc()

    return error_response


# 导入 httpx（如果可用）
try:
    import httpx
    httpx.TimeoutException = httpx.TimeoutException
except ImportError:
    class MockTimeoutException(Exception):
        pass
    httpx = type("obj", (object,), {"TimeoutException": MockTimeoutException})


# ============================================================================
# FastAPI 集成
# ============================================================================

from fastapi import Request, status
from fastapi.responses import JSONResponse


async def error_response_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """
    FastAPI 异常处理器

    Usage:
        app.add_exception_handler(Exception, error_response_handler)
    """
    error_response = exception_to_error_response(exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump(),
    )


# ============================================================================
# 使用示例
# ============================================================================

if __name__ == "__main__":  # pragma: no cover
    # 网络错误
    print(ErrorBuilder.network_error("Connection failed"))

    # 超时错误
    print(ErrorBuilder.timeout_error(180, "PDF processing"))

    # 文件过大
    print(ErrorBuilder.file_too_large(80.5, 50))

    # OCR 不可用
    print(ErrorBuilder.ocr_unavailable())

    # 低置信度
    print(ErrorBuilder.low_confidence(0.5, 0.7))

    # 异常转换
    try:
        raise FileNotFoundError("test.pdf")
    except Exception as e:
        print(exception_to_error_response(e, request_id="req-123"))
