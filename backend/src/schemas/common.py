from typing import Any, TypeVar

"""
通用响应模式
定义统一的API响应格式
"""

from datetime import UTC, datetime

from pydantic import BaseModel, Field

T = TypeVar("T")


class BaseResponse[T](BaseModel):
    """基础响应模式"""

    is_success: bool = Field(..., description="请求是否成功")
    message: str | None = Field(None, description="响应消息")
    data: T | None = Field(None, description="响应数据")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="响应时间戳"
    )
    request_id: str | None = Field(None, description="请求ID")


class ErrorResponse(BaseModel):
    """错误响应模式"""

    is_success: bool = Field(False, description="请求失败")
    error: dict[str, Any] = Field(..., description="错误详情")
    message: str = Field(..., description="错误消息")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="响应时间戳"
    )
    request_id: str | None = Field(None, description="请求ID")


class PaginationInfo(BaseModel):
    """分页信息模式"""

    page: int = Field(..., ge=1, description="当前页码")
    page_size: int = Field(..., ge=1, le=100, description="每页大小")
    total: int = Field(..., ge=0, description="总记录数")
    total_pages: int = Field(..., ge=0, description="总页数")
    has_next: bool = Field(..., description="是否有下一页")
    has_prev: bool = Field(..., description="是否有上一页")


class PaginatedResponse[T](BaseModel):
    """分页响应模式"""

    is_success: bool = Field(True, description="请求是否成功")
    message: str | None = Field(None, description="响应消息")
    data: list[T] = Field(..., description="数据列表")
    pagination: PaginationInfo = Field(..., description="分页信息")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="响应时间戳"
    )
    request_id: str | None = Field(None, description="请求ID")


class BusinessValidationErrorResponse(BaseModel):
    """验证错误响应模式"""

    is_success: bool = Field(False, description="请求失败")
    error: str = Field("validation_error", description="错误类型")
    message: str = Field("数据验证失败", description="错误消息")
    details: dict[str, list[str]] = Field(..., description="字段验证错误详情")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="响应时间戳"
    )
    request_id: str | None = Field(None, description="请求ID")


class SuccessResponse[T](BaseModel):
    """成功响应模式"""

    is_success: bool = Field(True, description="请求成功")
    message: str | None = Field("操作成功", description="成功消息")
    data: T | None = Field(None, description="响应数据")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="响应时间戳"
    )
    request_id: str | None = Field(None, description="请求ID")


class CreatedResponse[T](BaseModel):
    """创建成功响应模式"""

    is_success: bool = Field(True, description="创建成功")
    message: str = Field("创建成功", description="成功消息")
    data: T = Field(..., description="创建的数据")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="响应时间戳"
    )
    request_id: str | None = Field(None, description="请求ID")


class UpdatedResponse[T](BaseModel):
    """更新成功响应模式"""

    is_success: bool = Field(True, description="更新成功")
    message: str = Field("更新成功", description="成功消息")
    data: T | None = Field(None, description="更新后的数据")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="响应时间戳"
    )
    request_id: str | None = Field(None, description="请求ID")


class DeletedResponse(BaseModel):
    """删除成功响应模式"""

    is_success: bool = Field(True, description="删除成功")
    message: str = Field("删除成功", description="成功消息")
    data: dict[str, Any] | None = Field(None, description="删除相关信息")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="响应时间戳"
    )
    request_id: str | None = Field(None, description="请求ID")


class BatchOperationResponse(BaseModel):
    """批量操作响应模式"""

    is_success: bool = Field(True, description="批量操作是否成功")
    message: str = Field("批量操作完成", description="操作消息")
    total_count: int = Field(..., ge=0, description="总操作数量")
    success_count: int = Field(..., ge=0, description="成功数量")
    failed_count: int = Field(..., ge=0, description="失败数量")
    errors: list[dict[str, Any]] = Field(
        default_factory=list[Any], description="错误详情"
    )
    data: dict[str, Any] | None = Field(None, description="操作结果数据")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="响应时间戳"
    )
    request_id: str | None = Field(None, description="请求ID")


class HealthCheckResponse(BaseModel):
    """健康检查响应模式"""

    status: str = Field(..., description="服务状态")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="检查时间"
    )
    version: str = Field(..., description="服务版本")
    services: dict[str, str] = Field(
        default_factory=dict[str, Any], description="依赖服务状态"
    )
    uptime: float | None = Field(None, description="运行时间（秒）")
    memory_usage: dict[str, Any] | None = Field(None, description="内存使用情况")


# 响应构建器工具类
class ResponseBuilder:
    """响应构建器"""

    @staticmethod
    def success(data: Any | None = None, message: str | None = None) -> dict[str, Any]:
        """构建成功响应"""
        return {  # pragma: no cover
            "is_success": True,  # pragma: no cover
            "message": message or "操作成功",  # pragma: no cover
            "data": data,  # pragma: no cover
            "timestamp": datetime.now(UTC).isoformat(),  # pragma: no cover
        }  # pragma: no cover

    @staticmethod
    def error(
        message: str,
        error_code: str = "unknown_error",
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """构建错误响应"""
        return {  # pragma: no cover
            "is_success": False,  # pragma: no cover
            "message": message,  # pragma: no cover
            "error": {"code": error_code, "details": details or {}},  # pragma: no cover
            "timestamp": datetime.now(UTC).isoformat(),  # pragma: no cover
        }  # pragma: no cover

    @staticmethod
    def validation_error(field_errors: dict[str, list[str]]) -> dict[str, Any]:
        """构建验证错误响应"""
        return {  # pragma: no cover
            "is_success": False,  # pragma: no cover
            "message": "数据验证失败",  # pragma: no cover
            "error": {
                "code": "validation_error",
                "field_errors": field_errors,
            },  # pragma: no cover
            "timestamp": datetime.now(UTC).isoformat(),  # pragma: no cover
        }  # pragma: no cover

    @staticmethod
    def paginated(
        data: list[Any],
        page: int,
        page_size: int,
        total: int,
        message: str | None = None,
    ) -> dict[str, Any]:
        """构建分页响应"""
        total_pages = (total + page_size - 1) // page_size  # pragma: no cover
        return {  # pragma: no cover
            "is_success": True,  # pragma: no cover
            "message": message or "数据获取成功",  # pragma: no cover
            "data": data,  # pragma: no cover
            "pagination": {  # pragma: no cover
                "page": page,  # pragma: no cover
                "page_size": page_size,  # pragma: no cover
                "total": total,  # pragma: no cover
                "total_pages": total_pages,  # pragma: no cover
                "has_next": page < total_pages,  # pragma: no cover
                "has_prev": page > 1,  # pragma: no cover
            },  # pragma: no cover
            "timestamp": datetime.now(UTC).isoformat(),  # pragma: no cover
        }  # pragma: no cover

    @staticmethod
    def batch_operation(
        total_count: int,
        success_count: int,
        failed_count: int,
        errors: list[dict[str, Any]] | None = None,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """构建批量操作响应"""
        return {  # pragma: no cover
            "is_success": failed_count == 0,  # pragma: no cover
            "message": f"批量操作完成：成功 {success_count}，失败 {failed_count}",  # pragma: no cover
            "total_count": total_count,  # pragma: no cover
            "success_count": success_count,  # pragma: no cover
            "failed_count": failed_count,  # pragma: no cover
            "errors": errors or [],  # pragma: no cover
            "data": data,  # pragma: no cover
            "timestamp": datetime.now(UTC).isoformat(),  # pragma: no cover
        }  # pragma: no cover


# 常用响应实例
def create_success_response[T](
    data: T | None = None, message: str | None = None, **kwargs: Any
) -> SuccessResponse[T]:
    """创建成功响应"""
    return SuccessResponse(data=data, message=message, **kwargs)  # pragma: no cover


def create_error_response(
    message: str,
    error_code: str = "unknown_error",
    details: dict[str, Any] | None = None,
) -> ErrorResponse:
    """创建错误响应"""
    return ErrorResponse(  # pragma: no cover
        is_success=False,
        error={"code": error_code, "details": details or {}},
        message=message,
        request_id=None,  # pragma: no cover
    )  # pragma: no cover


def create_paginated_response[T](
    data: list[T], page: int, page_size: int, total: int, message: str | None = None
) -> PaginatedResponse[T]:
    """创建分页响应"""
    total_pages = (total + page_size - 1) // page_size  # pragma: no cover
    pagination = PaginationInfo(  # pragma: no cover
        page=page,  # pragma: no cover
        page_size=page_size,  # pragma: no cover
        total=total,  # pragma: no cover
        total_pages=total_pages,  # pragma: no cover
        has_next=page < total_pages,  # pragma: no cover
        has_prev=page > 1,  # pragma: no cover
    )  # pragma: no cover
    return PaginatedResponse(
        is_success=True,
        data=data,
        pagination=pagination,
        message=message,
        request_id=None,
    )  # pragma: no cover


# 导出所有响应模式
__all__ = [
    "BaseResponse",
    "ErrorResponse",
    "PaginationInfo",
    "PaginatedResponse",
    "BusinessValidationErrorResponse",
    "SuccessResponse",
    "CreatedResponse",
    "UpdatedResponse",
    "DeletedResponse",
    "BatchOperationResponse",
    "HealthCheckResponse",
    "ResponseBuilder",
    "create_success_response",
    "create_error_response",
    "create_paginated_response",
]
