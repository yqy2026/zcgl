"""
认证相关的Pydantic模型
"""

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from ..models.auth import UserRole


# 用户相关模型
class UserBase(BaseModel):
    """用户基础模型"""

    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: EmailStr = Field(..., description="邮箱地址")
    full_name: str = Field(..., min_length=2, max_length=100, description="全名")

    @field_validator("username")
    @classmethod
    def validate_username(cls, v):
        """验证用户名格式"""
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("用户名只能包含字母、数字、下划线和连字符")
        return v

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v):
        """验证姓名格式"""
        if not v.strip():
            raise ValueError("姓名不能为空")
        return v.strip()


class UserCreate(UserBase):
    """用户创建模型"""

    password: str = Field(..., min_length=8, max_length=128, description="密码")
    role: UserRole = Field(default=UserRole.USER, description="用户角色")
    employee_id: str | None = Field(None, description="关联员工ID")
    default_organization_id: str | None = Field(None, description="默认组织ID")

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v):
        """验证密码强度"""
        if len(v) < 8:
            raise ValueError("密码长度至少8位")

        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v)

        if not (has_upper and has_lower and has_digit):
            raise ValueError("密码必须包含大写字母、小写字母和数字")

        if not has_special:
            raise ValueError("密码必须包含至少一个特殊字符")

        return v


class UserUpdate(BaseModel):
    """用户更新模型"""

    email: EmailStr | None = Field(None, description="邮箱地址")
    full_name: str | None = Field(
        None, min_length=2, max_length=100, description="全名"
    )
    role: UserRole | None = Field(None, description="用户角色")
    is_active: bool | None = Field(None, description="是否激活")
    employee_id: str | None = Field(None, description="关联员工ID")
    default_organization_id: str | None = Field(None, description="默认组织ID")

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v):
        if v is not None:
            return v.strip()
        return v


class UserResponse(UserBase):
    """用户响应模型"""

    id: str
    role: UserRole
    is_active: bool
    is_locked: bool
    last_login_at: datetime | None
    employee_id: str | None
    default_organization_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# 认证相关模型
class LoginRequest(BaseModel):
    """登录请求模型"""

    username: str = Field(..., description="用户名或邮箱")
    password: str = Field(..., description="密码")


class TokenData(BaseModel):
    """JWT令牌数据模型"""

    sub: str  # 用户ID
    username: str
    role: UserRole
    exp: int | None = None


class TokenResponse(BaseModel):
    """令牌响应模型"""

    access_token: str = Field(..., description="访问令牌")
    refresh_token: str = Field(..., description="刷新令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    expires_in: int = Field(..., description="过期时间（秒）")


class LoginResponse(BaseModel):
    """登录响应模型"""

    user: UserResponse
    tokens: TokenResponse
    message: str = Field(default="登录成功", description="响应消息")


class RefreshTokenRequest(BaseModel):
    """刷新令牌请求模型"""

    refresh_token: str = Field(..., description="刷新令牌")


class PasswordChangeRequest(BaseModel):
    """修改密码请求模型"""

    current_password: str = Field(..., description="当前密码")
    new_password: str = Field(..., min_length=8, max_length=128, description="新密码")

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v):
        """验证密码强度"""
        if len(v) < 8:
            raise ValueError("密码长度至少8位")

        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v)

        if not (has_upper and has_lower and has_digit):
            raise ValueError("密码必须包含大写字母、小写字母和数字")

        if not has_special:
            raise ValueError("密码必须包含至少一个特殊字符")

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
    role: UserRole | None = Field(None, description="角色筛选")
    is_active: bool | None = Field(None, description="是否激活")
    organization_id: str | None = Field(None, description="组织ID筛选")


# 密码重置模型
class PasswordResetRequest(BaseModel):
    """密码重置请求模型"""

    email: EmailStr = Field(..., description="邮箱地址")


class PasswordResetConfirm(BaseModel):
    """密码重置确认模型"""

    token: str = Field(..., description="重置令牌")
    new_password: str = Field(..., min_length=8, max_length=128, description="新密码")

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v):
        """验证密码强度"""
        if len(v) < 8:
            raise ValueError("密码长度至少8位")

        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v)

        if not (has_upper and has_lower and has_digit):
            raise ValueError("密码必须包含大写字母、小写字母和数字")

        if not has_special:
            raise ValueError("密码必须包含至少一个特殊字符")

        return v
