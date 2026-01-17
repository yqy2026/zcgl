"""
API错误快捷函数模块

提供HTTPException兼容的便捷函数，自动使用统一错误处理系统。
用于替代直接的 `raise HTTPException(...)` 调用。

使用方法:
    from ...core.api_errors import not_found, bad_request, forbidden, internal_error

    # 替代: raise HTTPException(status_code=404, detail="资源不存在")
    raise not_found("资源不存在")

    # 替代: raise HTTPException(status_code=400, detail="参数无效")
    raise bad_request("参数无效")

    # 替代: raise HTTPException(status_code=403, detail="权限不足")
    raise forbidden("权限不足")

    # 替代: raise HTTPException(status_code=500, detail=f"操作失败: {str(e)}")
    raise internal_error(f"操作失败: {str(e)}")
"""

from typing import Any

from fastapi import status

from .unified_error_handler import (
    ErrorCode,
    ErrorSeverity,
    UnifiedError,
)


def not_found(
    message: str = "资源未找到",
    *,
    resource_type: str | None = None,
    resource_id: str | None = None,
) -> UnifiedError:
    """
    创建404未找到错误

    Args:
        message: 错误消息
        resource_type: 资源类型（如"合同"、"资产"）
        resource_id: 资源ID

    Examples:
        raise not_found("合同不存在")
        raise not_found("资产不存在", resource_type="asset", resource_id="123")
    """
    extra_data: dict[str, Any] = {}
    if resource_type:
        extra_data["resource_type"] = resource_type
    if resource_id:
        extra_data["resource_id"] = resource_id

    return UnifiedError(
        message=message,
        code=ErrorCode.NOT_FOUND,
        status_code=status.HTTP_404_NOT_FOUND,
        severity=ErrorSeverity.LOW,
        extra_data=extra_data,
    )


def bad_request(
    message: str,
    *,
    field: str | None = None,
    details: str | dict[str, Any] | list[str] | None = None,
) -> UnifiedError:
    """
    创建400错误请求错误

    Args:
        message: 错误消息
        field: 出错字段名
        details: 额外详情

    Examples:
        raise bad_request("参数无效")
        raise bad_request("日期格式错误", field="start_date")
    """
    extra_data: dict[str, Any] = {}
    if field:
        extra_data["field"] = field

    return UnifiedError(
        message=message,
        code=ErrorCode.INVALID_REQUEST,
        status_code=status.HTTP_400_BAD_REQUEST,
        details=details,
        severity=ErrorSeverity.MEDIUM,
        extra_data=extra_data,
    )


def validation_error(
    message: str = "数据验证失败",
    *,
    field_errors: list[str] | dict[str, str] | None = None,
) -> UnifiedError:
    """
    创建422验证错误

    Args:
        message: 错误消息
        field_errors: 字段错误列表或字典

    Examples:
        raise validation_error("必填字段缺失", field_errors=["name", "email"])
    """
    details = field_errors if field_errors else None

    return UnifiedError(
        message=message,
        code=ErrorCode.VALIDATION_ERROR,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        details=details,
        severity=ErrorSeverity.MEDIUM,
    )


def unauthorized(message: str = "未授权，请登录") -> UnifiedError:
    """
    创建401未授权错误

    Examples:
        raise unauthorized()
        raise unauthorized("登录已过期")
    """
    return UnifiedError(
        message=message,
        code=ErrorCode.UNAUTHORIZED,
        status_code=status.HTTP_401_UNAUTHORIZED,
        severity=ErrorSeverity.HIGH,
    )


def forbidden(message: str = "权限不足") -> UnifiedError:
    """
    创建403禁止访问错误

    Examples:
        raise forbidden()
        raise forbidden("只有管理员可以执行此操作")
    """
    return UnifiedError(
        message=message,
        code=ErrorCode.FORBIDDEN,
        status_code=status.HTTP_403_FORBIDDEN,
        severity=ErrorSeverity.HIGH,
    )


def conflict(
    message: str,
    *,
    resource_type: str | None = None,
) -> UnifiedError:
    """
    创建409冲突错误

    Examples:
        raise conflict("资源已存在")
        raise conflict("合同编号已存在", resource_type="contract")
    """
    extra_data: dict[str, Any] = {}
    if resource_type:
        extra_data["resource_type"] = resource_type

    return UnifiedError(
        message=message,
        code=ErrorCode.RESOURCE_CONFLICT,
        status_code=status.HTTP_409_CONFLICT,
        severity=ErrorSeverity.MEDIUM,
        extra_data=extra_data,
    )


def internal_error(
    message: str = "服务器内部错误",
    *,
    original_error: Exception | None = None,
) -> UnifiedError:
    """
    创建500内部服务器错误

    Args:
        message: 错误消息
        original_error: 原始异常（用于日志记录）

    Examples:
        raise internal_error(f"操作失败: {str(e)}")
        raise internal_error("数据库错误", original_error=e)
    """
    extra_data: dict[str, Any] = {}
    if original_error:
        extra_data["original_error"] = str(original_error)

    return UnifiedError(
        message=message,
        code=ErrorCode.INTERNAL_SERVER_ERROR,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        severity=ErrorSeverity.CRITICAL,
        extra_data=extra_data,
    )


def service_unavailable(
    message: str = "服务暂时不可用",
    *,
    service_name: str | None = None,
) -> UnifiedError:
    """
    创建503服务不可用错误

    Examples:
        raise service_unavailable("数据库管理器不可用")
    """
    extra_data: dict[str, Any] = {}
    if service_name:
        extra_data["service"] = service_name

    return UnifiedError(
        message=message,
        code=ErrorCode.EXTERNAL_SERVICE_ERROR,
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        severity=ErrorSeverity.HIGH,
        extra_data=extra_data,
    )


def operation_not_allowed(
    message: str,
    *,
    reason: str | None = None,
) -> UnifiedError:
    """
    创建业务操作不允许错误

    Examples:
        raise operation_not_allowed("合同状态不允许此操作")
    """
    extra_data: dict[str, Any] = {}
    if reason:
        extra_data["reason"] = reason

    return UnifiedError(
        message=message,
        code=ErrorCode.OPERATION_NOT_ALLOWED,
        status_code=status.HTTP_400_BAD_REQUEST,
        severity=ErrorSeverity.MEDIUM,
        extra_data=extra_data,
    )


# 导出所有函数
__all__ = [
    "not_found",
    "bad_request",
    "validation_error",
    "unauthorized",
    "forbidden",
    "conflict",
    "internal_error",
    "service_unavailable",
    "operation_not_allowed",
    # Re-export core types for convenience
    "UnifiedError",
    "ErrorCode",
    "ErrorSeverity",
]
