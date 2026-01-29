from typing import Any, TypeVar

"""
统一响应处理器
提供标准化的API响应格式和错误处理
"""

import logging
from datetime import UTC, datetime

from fastapi import HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T")


class APIResponse[T](BaseModel):
    """统一API响应格式"""

    success: bool = True
    message: str | None = None
    data: T | None = None
    error: dict[str, Any] | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    request_id: str | None = None
    pagination: dict[str, Any] | None = None


class PaginationInfo(BaseModel):
    """分页信息"""

    page: int
    page_size: int
    total: int
    total_pages: int
    has_next: bool
    has_prev: bool


class PaginatedData[T](BaseModel):
    """分页数据结构（items + pagination）"""

    items: list[T]
    pagination: PaginationInfo


class ResponseHandler:
    """统一响应处理器"""

    @staticmethod
    def success(
        data: Any = None,
        message: str = "操作成功",
        status_code: int = status.HTTP_200_OK,
        request_id: str | None = None,
        pagination: PaginationInfo | None = None,
    ) -> JSONResponse:
        """成功响应"""

        response_data = {
            "success": True,
            "message": message,
            "data": data,
            "timestamp": datetime.now(UTC).isoformat(),
            "request_id": request_id,
            "pagination": pagination.model_dump() if pagination else None,
        }

        return JSONResponse(status_code=status_code, content=response_data)

    @staticmethod
    def error(
        message: str,
        error_code: str = "UNKNOWN_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: dict[str, Any] | None = None,
        request_id: str | None = None,
    ) -> JSONResponse:
        """错误响应"""

        error_info = {"code": error_code, "message": message, "details": details or {}}

        response_data = {
            "success": False,
            "message": message,
            "error": error_info,
            "timestamp": datetime.now(UTC).isoformat(),
            "request_id": request_id,
        }

        # 记录错误日志
        logger.error(
            f"API Error: {error_code} - {message}",
            extra={
                "error_code": error_code,
                "status_code": status_code,
                "details": details,
                "request_id": request_id,
            },
        )

        return JSONResponse(status_code=status_code, content=response_data)

    @staticmethod
    def validation_error(
        errors: list[dict[str, Any]],
        message: str = "请求参数验证失败",
        request_id: str | None = None,
    ) -> JSONResponse:
        """验证错误响应"""

        return ResponseHandler.error(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details={"validation_errors": errors},
            request_id=request_id,
        )

    @staticmethod
    def not_found(
        resource: str = "资源",
        resource_id: str | None = None,
        request_id: str | None = None,
    ) -> JSONResponse:
        """404未找到响应"""

        message = f"{resource}未找到"
        if resource_id:
            message += f" (ID: {resource_id})"

        return ResponseHandler.error(
            message=message,
            error_code="NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"resource": resource, "resource_id": resource_id},
            request_id=request_id,
        )

    @staticmethod
    def conflict(
        message: str,
        conflict_type: str = "CONFLICT",
        details: dict[str, Any] | None = None,
        request_id: str | None = None,
    ) -> JSONResponse:
        """409冲突响应"""

        return ResponseHandler.error(
            message=message,
            error_code=conflict_type,
            status_code=status.HTTP_409_CONFLICT,
            details=details,
            request_id=request_id,
        )

    @staticmethod
    def unauthorized(
        message: str = "未授权访问", request_id: str | None = None
    ) -> JSONResponse:
        """401未授权响应"""

        return ResponseHandler.error(
            message=message,
            error_code="UNAUTHORIZED",
            status_code=status.HTTP_401_UNAUTHORIZED,
            request_id=request_id,
        )

    @staticmethod
    def forbidden(
        message: str = "禁止访问", request_id: str | None = None
    ) -> JSONResponse:
        """403禁止访问响应"""

        return ResponseHandler.error(
            message=message,
            error_code="FORBIDDEN",
            status_code=status.HTTP_403_FORBIDDEN,
            request_id=request_id,
        )

    @staticmethod
    def database_error(
        error: Exception, message: str = "数据库操作失败"
    ) -> HTTPException:
        """数据库错误异常 - 用于CRUD操作中抛出

        注意：此方法返回HTTPException而不是JSONResponse，
        因为它需要在CRUD操作中被抛出，而不是直接返回响应。
        """
        logger.error(f"Database error: {message} - {str(error)}", exc_info=True)

        # 在开发环境中包含详细错误信息
        if settings.DEBUG:
            details = {
                "exception_type": type(error).__name__,
                "exception_message": str(error),
                "operation": message,
            }
        else:
            details = {"operation": message}

        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": message,
                "error_code": "DATABASE_ERROR",
                "details": details,
            },
        )

    @staticmethod
    def paginated(
        data: list[Any],
        page: int,
        page_size: int,
        total: int,
        message: str = "获取成功",
        request_id: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> JSONResponse:
        """分页响应"""

        total_pages = (total + page_size - 1) // page_size
        pagination_info = PaginationInfo(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        )

        payload_dict: dict[str, Any] = {
            "items": data,
            "pagination": pagination_info,
        }

        if extra:
            for key, value in extra.items():
                if key not in payload_dict:
                    payload_dict[key] = value

        payload = PaginatedData(items=payload_dict["items"], pagination=pagination_info)
        if extra:
            # Allow additional fields beyond the standard payload
            payload_dict["pagination"] = pagination_info
            encoded_payload = jsonable_encoder(payload_dict)
        else:
            encoded_payload = jsonable_encoder(payload)

        return ResponseHandler.success(
            data=encoded_payload,
            message=message,
            request_id=request_id,
        )


def get_request_id(request: Request) -> str | None:
    """从请求中获取请求ID"""
    # 尝试从header中获取
    request_id = request.headers.get("X-Request-ID")
    if request_id:
        return request_id

    # 尝试从其他header中获取
    request_id = request.headers.get("Request-ID")
    if request_id:
        return request_id

    # 生成新的请求ID
    import uuid

    return str(uuid.uuid4())


# 便捷函数
def success_response(
    data: Any = None, message: str = "操作成功", **kwargs: Any
) -> JSONResponse:
    """成功响应便捷函数"""
    return ResponseHandler.success(data=data, message=message, **kwargs)


def error_response(
    message: str, error_code: str = "UNKNOWN_ERROR", **kwargs: Any
) -> JSONResponse:
    """错误响应便捷函数"""
    return ResponseHandler.error(message=message, error_code=error_code, **kwargs)


def not_found_response(
    resource: str = "资源", resource_id: str | None = None, **kwargs: Any
) -> JSONResponse:
    """404响应便捷函数"""
    return ResponseHandler.not_found(
        resource=resource, resource_id=resource_id, **kwargs
    )


def paginated_response(
    data: list[Any],
    page: int,
    page_size: int,
    total: int,
    extra: dict[str, Any] | None = None,
    **kwargs: Any,
) -> JSONResponse:
    """分页响应便捷函数"""
    return ResponseHandler.paginated(
        data=data,
        page=page,
        page_size=page_size,
        total=total,
        extra=extra,
        **kwargs,
    )
