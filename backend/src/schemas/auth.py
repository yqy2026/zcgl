"""
认证相关的Pydantic模型
"""

import re
from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
)
from pydantic_core import PydanticCustomError


# 用户相关模型
class UserBase(BaseModel):
    """用户基础模型"""

    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: EmailStr | None = Field(None, description="邮箱地址")
    phone: str = Field(..., max_length=20, description="手机号码")
    full_name: str = Field(..., min_length=2, max_length=100, description="全名")

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """验证用户名格式"""
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise PydanticCustomError(
                "invalid_username",
                "用户名只能包含字母、数字、下划线和连字符",
                {},
            )
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """验证手机号格式"""
        if not re.match(r"^1[3-9]\d{9}$", v):
            raise PydanticCustomError(
                "invalid_phone",
                "手机号格式不正确，请输入11位中国大陆手机号",
                {},
            )
        return v

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        """验证姓名格式"""
        if not v.strip():
            raise PydanticCustomError("empty_full_name", "姓名不能为空", {})
        return v.strip()


class UserCreate(UserBase):
    """用户创建模型"""

    password: str = Field(..., min_length=8, max_length=128, description="密码")
    role_id: str | None = Field(None, description="主角色ID")
    default_organization_id: str | None = Field(
        None,
        description="默认组织ID",
    )

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """验证密码强度"""
        if len(v) < 8:
            raise PydanticCustomError("password_too_short", "密码长度至少8位", {})

        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v)

        if not (has_upper and has_lower and has_digit):
            raise PydanticCustomError(
                "password_missing_complexity",
                "密码必须包含大写字母、小写字母和数字",
                {},
            )

        if not has_special:
            raise PydanticCustomError(
                "password_missing_special",
                "密码必须包含至少一个特殊字符",
                {},
            )

        return v


class UserUpdate(BaseModel):
    """用户更新模型"""

    email: EmailStr | None = Field(None, description="邮箱地址")
    phone: str | None = Field(None, max_length=20, description="手机号码")
    full_name: str | None = Field(
        None, min_length=2, max_length=100, description="全名"
    )
    role_id: str | None = Field(None, description="主角色ID")
    is_active: bool | None = Field(None, description="是否激活")
    default_organization_id: str | None = Field(
        None,
        description="默认组织ID",
    )

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        """验证手机号格式"""
        if v is not None and not re.match(r"^1[3-9]\d{9}$", v):
            raise PydanticCustomError(
                "invalid_phone",
                "手机号格式不正确，请输入11位中国大陆手机号",
                {},
            )
        return v

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str | None) -> str | None:
        if v is not None:
            return v.strip()
        return v


class UserResponse(BaseModel):
    """用户响应模型"""

    id: str
    username: str
    email: EmailStr | None = None
    phone: str
    full_name: str
    role_id: str | None = Field(None, description="主角色ID")
    role_name: str | None = Field(None, description="主角色名称")
    roles: list[str] = Field(default_factory=list, description="角色编码列表")
    role_ids: list[str] = Field(default_factory=list, description="角色ID列表")
    is_admin: bool = Field(False, description="是否管理员")
    is_active: bool
    is_locked: bool
    last_login_at: datetime | str | None
    default_organization_id: str | None
    created_at: datetime | str
    updated_at: datetime | str

    model_config = ConfigDict(from_attributes=True)

    @field_validator("is_active", "is_locked", mode="before")
    @classmethod
    def parse_boolean(cls, v: bool | int) -> bool | int:
        """Parse boolean from int or bool"""
        if isinstance(v, int):
            return bool(v)
        return v

    @field_validator("last_login_at", "created_at", "updated_at", mode="before")
    @classmethod
    def parse_datetime(cls, v: str | datetime | None) -> str | datetime | None:
        """Parse datetime from string or datetime object"""
        if v is None:
            return v
        if isinstance(v, datetime):
            return v
        if isinstance(v, str):
            try:
                # Try to parse ISO format datetime string
                return datetime.fromisoformat(v.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                # If parsing fails, return the original string
                # This allows the response to work even if datetime parsing fails
                return v
        return v


# 认证相关模型
class LoginRequest(BaseModel):
    """登录请求模型"""

    username: str = Field(..., description="用户名或邮箱")
    password: str = Field(..., description="密码")


class TokenData(BaseModel):
    """JWT令牌数据模型"""

    sub: str  # 用户ID
    username: str
    exp: int | None = None


# Permission相关模式
class PermissionSchema(BaseModel):
    """权限模式"""

    resource: str = Field(..., description="资源类型")
    action: str = Field(..., description="操作类型")
    description: str | None = Field(None, description="权限描述")

    model_config = ConfigDict(from_attributes=True)


class CookieAuthResponse(BaseModel):
    """基于Cookie的认证响应（不返回Token）"""

    user: UserResponse
    permissions: list["PermissionSchema"] = Field(
        default_factory=list, description="用户权限列表"
    )
    message: str = Field(default="登录成功", description="响应消息")
    auth_mode: str = Field(default="cookie", description="认证模式")


class CookieRefreshResponse(BaseModel):
    """Cookie刷新响应（不返回Token）"""

    message: str = Field(default="令牌刷新成功", description="响应消息")
    auth_mode: str = Field(default="cookie", description="认证模式")


class RefreshTokenRequest(BaseModel):
    """刷新令牌请求模型"""

    refresh_token: str | None = Field(default=None, description="刷新令牌")


class PasswordChangeRequest(BaseModel):
    """修改密码请求模型"""

    current_password: str = Field(..., description="当前密码")
    new_password: str = Field(..., min_length=8, max_length=128, description="新密码")

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """验证密码强度"""
        if len(v) < 8:
            raise PydanticCustomError("password_too_short", "密码长度至少8位", {})

        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v)

        if not (has_upper and has_lower and has_digit):
            raise PydanticCustomError(
                "password_missing_complexity",
                "密码必须包含大写字母、小写字母和数字",
                {},
            )

        if not has_special:
            raise PydanticCustomError(
                "password_missing_special",
                "密码必须包含至少一个特殊字符",
                {},
            )

        return v


# 会话相关模型
class UserSessionResponse(BaseModel):
    """用户会话响应模型"""

    id: str
    user_id: str
    device_info: str | None
    ip_address: str | None
    is_active: bool
    expires_at: datetime
    created_at: datetime
    last_accessed_at: datetime

    model_config = ConfigDict(from_attributes=True)


# 审计日志模型
class AuditLogResponse(BaseModel):
    """审计日志响应模型"""

    id: str
    username: str
    user_role: str | None
    action: str
    resource_type: str | None
    resource_name: str | None
    api_endpoint: str | None
    http_method: str | None
    response_status: int | None
    ip_address: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# 分页模型
class UserListResponse(BaseModel):
    """用户列表响应模型"""

    users: list[UserResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class UserQueryParams(BaseModel):
    """用户查询参数"""

    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")
    search: str | None = Field(None, description="搜索关键词")
    role_id: str | None = Field(None, description="角色筛选")
    is_active: bool | None = Field(None, description="是否激活")
    organization_id: str | None = Field(None, description="组织ID筛选")


# 密码重置模型
class PasswordResetRequest(BaseModel):
    """密码重置请求模型"""

    email: EmailStr = Field(..., description="邮箱地址")


class AdminPasswordResetRequest(BaseModel):
    """管理员重置用户密码请求模型"""

    new_password: str = Field(..., min_length=8, max_length=128, description="新密码")
    reason: str | None = Field(None, description="重置原因")

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """验证密码强度"""
        if len(v) < 8:
            raise PydanticCustomError("password_too_short", "密码长度至少8位", {})

        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v)

        if not (has_upper and has_lower and has_digit):
            raise PydanticCustomError(
                "password_missing_complexity",
                "密码必须包含大写字母、小写字母和数字",
                {},
            )

        if not has_special:
            raise PydanticCustomError(
                "password_missing_special",
                "密码必须包含至少一个特殊字符",
                {},
            )

        return v


class PasswordResetConfirm(BaseModel):
    """密码重置确认模型"""

    token: str = Field(..., description="重置令牌")
    new_password: str = Field(..., min_length=8, max_length=128, description="新密码")

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """验证密码强度"""
        if len(v) < 8:
            raise PydanticCustomError("password_too_short", "密码长度至少8位", {})

        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v)

        if not (has_upper and has_lower and has_digit):
            raise PydanticCustomError(
                "password_missing_complexity",
                "密码必须包含大写字母、小写字母和数字",
                {},
            )

        if not has_special:
            raise PydanticCustomError(
                "password_missing_special",
                "密码必须包含至少一个特殊字符",
                {},
            )

        return v
