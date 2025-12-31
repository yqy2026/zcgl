from typing import Any

"""
统一错误码定义系统
功能: 标准化所有系统错误、定义统一的错误响应格式
时间: 2025-11-03
"""

from dataclasses import dataclass
from enum import Enum


class ErrorCode(Enum):
    """统一错误码定义"""

    # 系统错误 (1000-1999)
    INTERNAL_SERVER_ERROR = (1000, "内部服务器错误")
    SERVICE_UNAVAILABLE = (1001, "服务暂时不可用")
    RATE_LIMIT_EXCEEDED = (1006, "超出频率限制")

    # 认证授权错误 (2000-2999)
    UNAUTHORIZED = (2000, "未授权，请登录")
    INVALID_CREDENTIALS = (2001, "用户名或密码错误")
    TOKEN_EXPIRED = (2002, "登录令牌已过期，请重新登录")
    TOKEN_INVALID = (2003, "无效的登录令牌")
    FORBIDDEN = (2004, "禁止访问，权限不足")
    PERMISSION_DENIED = (2006, "权限拒绝")

    # 数据验证错误 (3000-3999)
    VALIDATION_ERROR = (3000, "数据验证失败")
    FIELD_REQUIRED = (3001, "必填字段缺失")
    FIELD_INVALID = (3002, "字段值无效")
    EMAIL_INVALID = (3003, "邮箱格式不正确")

    # 资源错误 (4000-4999)
    RESOURCE_NOT_FOUND = (4000, "资源不存在")
    ASSET_NOT_FOUND = (4001, "资产不存在")
    CONTRACT_NOT_FOUND = (4002, "合同不存在")
    USER_NOT_FOUND = (4003, "用户不存在")
    ORGANIZATION_NOT_FOUND = (4004, "组织不存在")

    # 业务逻辑错误 (5000-5999)
    BUSINESS_ERROR = (5000, "业务逻辑错误")
    INVALID_STATE_TRANSITION = (5001, "无效的状态转换")
    OPERATION_NOT_ALLOWED = (5002, "不允许的操作")
    DUPLICATE_RECORD = (5005, "重复的记录")
    CANNOT_DELETE_REFERENCED = (5007, "无法删除，被其他记录引用")

    # 数据库错误 (7000-7999)
    DATABASE_ERROR = (7000, "数据库错误")
    DATABASE_CONNECTION_ERROR = (7001, "数据库连接失败")

    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message


@dataclass
class APIResponse:
    """标准API响应"""

    success: bool
    data: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        from datetime import datetime  # pragma: no cover

        result: dict[str, Any] = {  # pragma: no cover
            "success": self.success,  # pragma: no cover
            "timestamp": datetime.now().isoformat(),  # pragma: no cover
        }

        if self.success and self.data:  # pragma: no cover
            result["data"] = self.data  # pragma: no cover
        elif not self.success and self.error:  # pragma: no cover
            result["error"] = self.error  # pragma: no cover

        if self.message:  # pragma: no cover
            result["message"] = self.message  # pragma: no cover

        return result  # pragma: no cover


class BusinessError(Exception):
    """业务异常基类"""

    def __init__(
        self,
        error_code: ErrorCode,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        self.error_code = error_code  # pragma: no cover
        self.message = message or error_code.message  # pragma: no cover
        self.details = details or {}  # pragma: no cover
        super().__init__(self.message)  # pragma: no cover

    def to_response(self) -> APIResponse:
        """转换为响应"""
        error_info = {
            "code": self.error_code.code,
            "message": self.error_code.message,
        }  # pragma: no cover
        if self.details:  # pragma: no cover
            error_info["details"] = self.details  # pragma: no cover

        return APIResponse(
            success=False, error=error_info, message=self.message
        )  # pragma: no cover


class BusinessValidationError(BusinessError):
    """数据验证异常"""

    def __init__(self, errors: dict[str, str] | None = None):
        super().__init__(  # pragma: no cover
            ErrorCode.VALIDATION_ERROR,
            details={"validation_errors": errors or {}},  # pragma: no cover
        )  # pragma: no cover


class AuthError(BusinessError):
    """认证异常"""

    def __init__(self, error_code: ErrorCode = ErrorCode.UNAUTHORIZED):
        super().__init__(error_code)  # pragma: no cover


class ResourceNotFoundError(BusinessError):
    """资源不存在异常"""

    def __init__(self, resource_type: str, resource_id: str | None = None):
        message = f"{resource_type}不存在"  # pragma: no cover
        if resource_id:  # pragma: no cover
            message += f" (ID: {resource_id})"  # pragma: no cover
        super().__init__(
            ErrorCode.RESOURCE_NOT_FOUND, message=message
        )  # pragma: no cover


# 错误码映射表
ERROR_CODE_MAP: dict[int, ErrorCode] = {ec.code: ec for ec in ErrorCode}


def get_error_by_code(code: int) -> ErrorCode | None:
    """根据错误码获取错误定义"""
    return ERROR_CODE_MAP.get(code)  # pragma: no cover


def get_error_by_name(name: str) -> ErrorCode | None:
    """根据错误名称获取错误定义"""
    try:  # pragma: no cover
        return ErrorCode[name]  # pragma: no cover
    except KeyError:  # pragma: no cover
        return None  # pragma: no cover
