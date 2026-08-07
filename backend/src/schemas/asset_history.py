"""资产变更历史（asset_history）响应 schema。

后端资产历史端点此前直接返回 ORM 对象导致 FastAPI 无法序列化（500），
本 schema 提供统一的响应形状，并对齐前端 AssetHistory 类型的增强字段
（change_type / changed_fields），缺省时由 operation_type / field_name 回填。
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator


class AssetHistoryItem(BaseModel):
    """资产变更历史条目（列表 / 详情展示）。"""

    model_config = ConfigDict(from_attributes=True, validate_default=True)

    id: str = Field(..., description="历史记录ID")
    asset_id: str = Field(..., description="资产ID")
    operation_type: str = Field(..., description="操作类型（create/update/delete 或业务动作）")
    change_type: str | None = Field(
        None,
        description="变更类型（增强字段，缺省回填 operation_type）",
    )
    field_name: str | None = Field(None, description="字段名称")
    changed_fields: list[str] = Field(
        default_factory=list,
        description="变更字段列表（增强字段，缺省由 field_name 回填）",
    )
    old_value: str | None = Field(None, description="原值")
    new_value: str | None = Field(None, description="新值")
    old_values: dict[str, Any] | None = Field(None, description="批量变更旧值")
    new_values: dict[str, Any] | None = Field(None, description="批量变更新值")
    operator: str | None = Field(None, description="操作人")
    operation_time: datetime = Field(..., description="操作时间")
    description: str | None = Field(None, description="操作描述")
    change_reason: str | None = Field(None, description="变更原因")
    ip_address: str | None = Field(None, description="IP地址")
    user_agent: str | None = Field(None, description="用户代理")
    session_id: str | None = Field(None, description="会话ID")

    @field_validator("change_type", mode="after")
    @classmethod
    def _backfill_change_type(cls, v: str | None, info: ValidationInfo) -> str | None:
        """change_type 未显式提供时回填 operation_type，保证前端 Tag 可读。"""
        if v is None:
            return info.data.get("operation_type")
        return v

    @field_validator("changed_fields", mode="after")
    @classmethod
    def _backfill_changed_fields(cls, v: list[str], info: ValidationInfo) -> list[str]:
        """changed_fields 为空时由 field_name 回填单字段列表。"""
        if not v:
            field_name = info.data.get("field_name")
            if field_name:
                return [field_name]
        return v
