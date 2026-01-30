from typing import Any

"""
枚举字段管理相关数据验证模式
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_core import PydanticCustomError


class EnumFieldTypeBase(BaseModel):
    """枚举字段类型基础模式"""

    name: str = Field(..., min_length=1, max_length=100, description="枚举类型名称")
    code: str = Field(..., min_length=1, max_length=50, description="枚举类型编码")
    category: str | None = Field(None, max_length=50, description="枚举类别")
    description: str | None = Field(None, description="枚举类型描述")

    is_system: bool = Field(default=False, description="是否系统内置")
    is_multiple: bool = Field(default=False, description="是否支持多选")
    is_hierarchical: bool = Field(default=False, description="是否层级结构")
    default_value: str | None = Field(None, max_length=100, description="默认值")

    validation_rules: dict[str, Any] | None = Field(None, description="验证规则")
    display_config: dict[str, Any] | None = Field(None, description="显示配置")
    status: str = Field(default="active", description="状态")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        allowed_statuses = ["active", "inactive"]  # pragma: no cover
        if v not in allowed_statuses:  # pragma: no cover
            raise PydanticCustomError(  # pragma: no cover
                "invalid_status",
                f"status must be one of {allowed_statuses}",
                {},
            )  # pragma: no cover
        return v  # pragma: no cover

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        # 编码只能包含字母、数字和下划线
        import re  # pragma: no cover

        if not re.match(r"^[a-zA-Z0-9_]+$", v):  # pragma: no cover
            raise PydanticCustomError(  # pragma: no cover
                "invalid_code",
                "code can only contain letters, numbers and underscores",
                {},
            )  # pragma: no cover
        return v  # pragma: no cover


class EnumFieldTypeCreate(EnumFieldTypeBase):
    """创建枚举字段类型模式"""

    created_by: str | None = Field(None, max_length=100, description="创建人")


class EnumFieldTypeUpdate(BaseModel):
    """更新枚举字段类型模式"""

    name: str | None = Field(
        None, min_length=1, max_length=100, description="枚举类型名称"
    )
    code: str | None = Field(
        None, min_length=1, max_length=50, description="枚举类型编码"
    )
    category: str | None = Field(None, max_length=50, description="枚举类别")
    description: str | None = Field(None, description="枚举类型描述")

    is_system: bool | None = Field(None, description="是否系统内置")
    is_multiple: bool | None = Field(None, description="是否支持多选")
    is_hierarchical: bool | None = Field(None, description="是否层级结构")
    default_value: str | None = Field(None, max_length=100, description="默认值")

    validation_rules: dict[str, Any] | None = Field(None, description="验证规则")
    display_config: dict[str, Any] | None = Field(None, description="显示配置")
    status: str | None = Field(None, description="状态")
    updated_by: str | None = Field(None, max_length=100, description="更新人")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v is not None:  # pragma: no cover
            allowed_statuses = ["active", "inactive"]  # pragma: no cover
            if v not in allowed_statuses:  # pragma: no cover
                raise PydanticCustomError(  # pragma: no cover
                    "invalid_status",
                    f"status must be one of {allowed_statuses}",
                    {},
                )  # pragma: no cover
        return v  # pragma: no cover

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        if v is not None:  # pragma: no cover
            import re  # pragma: no cover

            if not re.match(r"^[a-zA-Z0-9_]+$", v):  # pragma: no cover
                raise PydanticCustomError(  # pragma: no cover
                    "invalid_code",
                    "code can only contain letters, numbers and underscores",
                    {},
                )  # pragma: no cover
        return v  # pragma: no cover


class EnumFieldValueBase(BaseModel):
    """枚举字段值基础模式"""

    enum_type_id: str = Field(..., description="枚举类型ID")
    label: str = Field(..., min_length=1, max_length=100, description="显示标签")
    value: str = Field(..., min_length=1, max_length=100, description="枚举值")
    code: str | None = Field(None, max_length=50, description="枚举编码")
    description: str | None = Field(None, description="描述")

    parent_id: str | None = Field(None, description="父级枚举值ID")
    level: int = Field(default=1, ge=1, description="层级级别")

    sort_order: int = Field(default=0, ge=0, description="排序")
    color: str | None = Field(None, max_length=20, description="颜色标识")
    icon: str | None = Field(None, max_length=50, description="图标")

    extra_properties: dict[str, Any] | None = Field(None, description="扩展属性")

    is_active: bool = Field(default=True, description="是否启用")
    is_default: bool = Field(default=False, description="是否默认值")

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        """验证编码格式：只能包含字母、数字和下划线"""
        if v is not None:  # pragma: no cover
            import re  # pragma: no cover

            if not re.match(r"^[a-zA-Z0-9_]+$", v):  # pragma: no cover
                raise PydanticCustomError(  # pragma: no cover
                    "invalid_code",
                    "code can only contain letters, numbers and underscores",
                    {},
                )  # pragma: no cover
        return v  # pragma: no cover

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: str | None) -> str | None:
        if v is not None:  # pragma: no cover
            # 验证颜色格式（支持hex格式）
            import re  # pragma: no cover

            if not re.match(r"^#[0-9A-Fa-f]{6}$", v):  # pragma: no cover
                raise PydanticCustomError(  # pragma: no cover
                    "invalid_color",
                    "color must be in hex format (#RRGGBB)",
                    {},
                )  # pragma: no cover
        return v  # pragma: no cover


class EnumFieldValueCreate(EnumFieldValueBase):
    """创建枚举字段值模式"""

    created_by: str | None = Field(None, max_length=100, description="创建人")


class EnumFieldValueUpdate(BaseModel):
    """更新枚举字段值模式"""

    label: str | None = Field(
        None, min_length=1, max_length=100, description="显示标签"
    )
    value: str | None = Field(None, min_length=1, max_length=100, description="枚举值")
    code: str | None = Field(None, max_length=50, description="枚举编码")
    description: str | None = Field(None, description="描述")

    parent_id: str | None = Field(None, description="父级枚举值ID")
    level: int | None = Field(None, ge=1, description="层级级别")

    sort_order: int | None = Field(None, ge=0, description="排序")
    color: str | None = Field(None, max_length=20, description="颜色标识")
    icon: str | None = Field(None, max_length=50, description="图标")

    extra_properties: dict[str, Any] | None = Field(None, description="扩展属性")

    is_active: bool | None = Field(None, description="是否启用")
    is_default: bool | None = Field(None, description="是否默认值")
    updated_by: str | None = Field(None, max_length=100, description="更新人")

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: str | None) -> str | None:
        if v is not None:  # pragma: no cover
            import re  # pragma: no cover

            if not re.match(r"^#[0-9A-Fa-f]{6}$", v):  # pragma: no cover
                raise PydanticCustomError(  # pragma: no cover
                    "invalid_color",
                    "color must be in hex format (#RRGGBB)",
                    {},
                )  # pragma: no cover
        return v  # pragma: no cover


class EnumFieldUsageBase(BaseModel):
    """枚举字段使用记录基础模式"""

    enum_type_id: str = Field(..., description="枚举类型ID")
    table_name: str = Field(..., min_length=1, max_length=100, description="使用表名")
    field_name: str = Field(..., min_length=1, max_length=100, description="使用字段名")
    field_label: str | None = Field(None, max_length=100, description="字段显示名称")
    module_name: str | None = Field(None, max_length=100, description="所属模块")

    is_required: bool = Field(default=False, description="是否必填")
    default_value: str | None = Field(None, max_length=100, description="默认值")
    validation_config: dict[str, Any] | None = Field(None, description="验证配置")
    is_active: bool = Field(default=True, description="是否启用")


class EnumFieldUsageCreate(EnumFieldUsageBase):
    """创建枚举字段使用记录模式"""

    created_by: str | None = Field(None, max_length=100, description="创建人")


class EnumFieldUsageUpdate(BaseModel):
    """更新枚举字段使用记录模式"""

    field_label: str | None = Field(None, max_length=100, description="字段显示名称")
    module_name: str | None = Field(None, max_length=100, description="所属模块")

    is_required: bool | None = Field(None, description="是否必填")
    default_value: str | None = Field(None, max_length=100, description="默认值")
    validation_config: dict[str, Any] | None = Field(None, description="验证配置")
    is_active: bool | None = Field(None, description="是否启用")
    updated_by: str | None = Field(None, max_length=100, description="更新人")


# 响应模式
class EnumFieldValueResponse(EnumFieldValueBase):
    """枚举字段值响应模式"""

    id: str
    path: str | None = None
    is_deleted: bool = False
    created_at: datetime
    updated_at: datetime
    created_by: str | None = None
    updated_by: str | None = None

    children: list["EnumFieldValueResponse"] | None = []

    model_config = ConfigDict(from_attributes=True)


class EnumFieldTypeResponse(EnumFieldTypeBase):
    """枚举字段类型响应模式"""

    id: str
    is_system: bool = False
    is_deleted: bool = False
    created_at: datetime
    updated_at: datetime
    created_by: str | None = None
    updated_by: str | None = None

    enum_values: list[EnumFieldValueResponse] | None = []

    model_config = ConfigDict(from_attributes=True)


class EnumFieldUsageResponse(EnumFieldUsageBase):
    """枚举字段使用记录响应模式"""

    id: str
    created_at: datetime
    updated_at: datetime
    created_by: str | None = None
    updated_by: str | None = None

    model_config = ConfigDict(from_attributes=True)


class EnumFieldHistoryResponse(BaseModel):
    """枚举字段历史响应模式"""

    id: str
    enum_type_id: str | None = None
    enum_value_id: str | None = None
    action: str
    target_type: str
    field_name: str | None = None
    old_value: str | None = None
    new_value: str | None = None
    change_reason: str | None = None
    created_at: datetime
    created_by: str | None = None
    ip_address: str | None = None

    model_config = ConfigDict(from_attributes=True)


class EnumFieldTree(BaseModel):
    """枚举字段树形结构"""

    id: str
    label: str
    value: str
    code: str | None = None
    level: int
    sort_order: int
    is_active: bool
    color: str | None = None
    icon: str | None = None
    children: list["EnumFieldTree"] = []

    model_config = ConfigDict(from_attributes=True)


class EnumFieldStatistics(BaseModel):
    """枚举字段统计信息"""

    total_types: int = 0
    active_types: int = 0
    total_values: int = 0
    active_values: int = 0
    usage_count: int = 0
    categories: list[dict[str, Any]] = []


# 批量操作模式
class EnumFieldBatchCreate(BaseModel):
    """批量创建枚举值模式"""

    enum_type_id: str = Field(..., description="枚举类型ID")
    values: list[dict[str, Any]] = Field(..., description="枚举值列表")
    created_by: str | None = Field(None, description="创建人")


class EnumFieldBatchUpdate(BaseModel):
    """批量更新枚举值模式"""

    updates: list[dict[str, Any]] = Field(..., description="更新数据列表")
    updated_by: str | None = Field(None, description="更新人")


# 更新前向引用
EnumFieldValueResponse.model_rebuild()
EnumFieldTree.model_rebuild()
