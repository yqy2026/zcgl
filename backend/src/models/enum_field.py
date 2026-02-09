"""
枚举值字段管理相关数据库模型
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class EnumFieldType(Base):
    """枚举字段类型模型"""

    __tablename__ = "enum_field_types"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # 基本信息
    name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="枚举类型名称"
    )
    code: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, comment="枚举类型编码"
    )
    category: Mapped[str | None] = mapped_column(String(50), comment="枚举类别")
    description: Mapped[str | None] = mapped_column(Text, comment="枚举类型描述")

    # 配置信息
    is_system: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="是否系统内置"
    )
    is_multiple: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="是否支持多选"
    )
    is_hierarchical: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="是否层级结构"
    )
    default_value: Mapped[str | None] = mapped_column(String(100), comment="默认值")

    # 验证规则
    validation_rules: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, comment="验证规则(JSON格式)"
    )
    display_config: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, comment="显示配置(JSON格式)"
    )

    # 状态信息
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active", comment="状态(active/inactive)"
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="是否删除"
    )

    # 时间信息
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC).replace(tzinfo=None), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        onupdate=lambda: datetime.now(UTC).replace(tzinfo=None),
        comment="更新时间",
    )
    created_by: Mapped[str | None] = mapped_column(String(100), comment="创建人")
    updated_by: Mapped[str | None] = mapped_column(String(100), comment="更新人")

    # 关系定义
    enum_values: Mapped[list["EnumFieldValue"]] = relationship(
        "EnumFieldValue", back_populates="enum_type", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<EnumFieldType(id={self.id}, name={self.name}, code={self.code})>"  # pragma: no cover


class EnumFieldValue(Base):
    """枚举字段值模型"""

    __tablename__ = "enum_field_values"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # 关联信息
    enum_type_id: Mapped[str] = mapped_column(
        String, ForeignKey("enum_field_types.id"), nullable=False, comment="枚举类型ID"
    )

    # 基本信息
    label: Mapped[str] = mapped_column(String(100), nullable=False, comment="显示标签")
    value: Mapped[str] = mapped_column(String(100), nullable=False, comment="枚举值")
    code: Mapped[str | None] = mapped_column(String(50), comment="枚举编码")
    description: Mapped[str | None] = mapped_column(Text, comment="描述")

    # 层级信息
    parent_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("enum_field_values.id"), comment="父级枚举值ID"
    )
    level: Mapped[int] = mapped_column(Integer, default=1, comment="层级级别")
    path: Mapped[str | None] = mapped_column(String(1000), comment="层级路径")

    # 显示配置
    sort_order: Mapped[int] = mapped_column(Integer, default=0, comment="排序")
    color: Mapped[str | None] = mapped_column(String(20), comment="颜色标识")
    icon: Mapped[str | None] = mapped_column(String(50), comment="图标")

    # 扩展属性
    extra_properties: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, comment="扩展属性(JSON格式)"
    )

    # 状态信息
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment="是否启用"
    )
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="是否默认值"
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="是否删除"
    )

    # 时间信息
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC).replace(tzinfo=None), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        onupdate=lambda: datetime.now(UTC).replace(tzinfo=None),
        comment="更新时间",
    )
    created_by: Mapped[str | None] = mapped_column(String(100), comment="创建人")
    updated_by: Mapped[str | None] = mapped_column(String(100), comment="更新人")

    # 关系定义
    enum_type: Mapped["EnumFieldType"] = relationship(
        "EnumFieldType", back_populates="enum_values"
    )
    parent: Mapped["EnumFieldValue | None"] = relationship(
        "EnumFieldValue", remote_side=[id], back_populates="children"
    )
    children: Mapped[list["EnumFieldValue"]] = relationship(
        "EnumFieldValue", back_populates="parent", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<EnumFieldValue(id={self.id}, label={self.label}, value={self.value})>"  # pragma: no cover


class EnumFieldUsage(Base):
    """枚举字段使用记录模型"""

    __tablename__ = "enum_field_usage"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # 关联信息
    enum_type_id: Mapped[str] = mapped_column(
        String, ForeignKey("enum_field_types.id"), nullable=False, comment="枚举类型ID"
    )

    # 使用信息
    table_name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="使用表名"
    )
    field_name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="使用字段名"
    )
    field_label: Mapped[str | None] = mapped_column(String(100), comment="字段显示名称")
    module_name: Mapped[str | None] = mapped_column(String(100), comment="所属模块")

    # 配置信息
    is_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="是否必填"
    )
    default_value: Mapped[str | None] = mapped_column(String(100), comment="默认值")
    validation_config: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, comment="验证配置"
    )

    # 状态信息
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment="是否启用"
    )

    # 时间信息
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC).replace(tzinfo=None), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        onupdate=lambda: datetime.now(UTC).replace(tzinfo=None),
        comment="更新时间",
    )
    created_by: Mapped[str | None] = mapped_column(String(100), comment="创建人")
    updated_by: Mapped[str | None] = mapped_column(String(100), comment="更新人")

    # 关系定义
    enum_type: Mapped["EnumFieldType"] = relationship("EnumFieldType")

    def __repr__(self) -> str:
        return f"<EnumFieldUsage(id={self.id}, table={self.table_name}, field={self.field_name})>"  # pragma: no cover


class EnumFieldHistory(Base):
    """枚举字段变更历史模型"""

    __tablename__ = "enum_field_history"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # 关联信息
    enum_type_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("enum_field_types.id"), comment="枚举类型ID"
    )
    enum_value_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("enum_field_values.id"), comment="枚举值ID"
    )

    # 变更信息
    action: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="操作类型(create/update/delete)"
    )
    target_type: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="目标类型(type/value)"
    )
    field_name: Mapped[str | None] = mapped_column(String(100), comment="变更字段")
    old_value: Mapped[str | None] = mapped_column(Text, comment="原值")
    new_value: Mapped[str | None] = mapped_column(Text, comment="新值")
    change_reason: Mapped[str | None] = mapped_column(String(500), comment="变更原因")

    # 操作信息
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, comment="操作时间"
    )
    created_by: Mapped[str | None] = mapped_column(String(100), comment="操作人")
    ip_address: Mapped[str | None] = mapped_column(String(45), comment="IP地址")
    user_agent: Mapped[str | None] = mapped_column(Text, comment="用户代理")

    # 关系定义
    enum_type: Mapped["EnumFieldType | None"] = relationship("EnumFieldType")
    enum_value: Mapped["EnumFieldValue | None"] = relationship("EnumFieldValue")

    def __repr__(self) -> str:
        return f"<EnumFieldHistory(id={self.id}, action={self.action}, target_type={self.target_type})>"  # pragma: no cover
