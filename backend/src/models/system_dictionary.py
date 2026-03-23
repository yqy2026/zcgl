"""系统字典与资产自定义字段模型。"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class SystemDictionary(Base):
    """系统数据字典模型"""

    __tablename__ = "system_dictionaries"

    id: Mapped[str] = mapped_column(
        String(50), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    dict_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True, comment="字典类型"
    )
    dict_code: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True, comment="字典编码"
    )
    dict_label: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True, comment="字典标签"
    )
    dict_value: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True, comment="字典值"
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="排序"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment="是否启用"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        comment="创建时间",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        onupdate=lambda: datetime.now(UTC).replace(tzinfo=None),
        comment="更新时间",
    )

    def __repr__(self) -> str:
        return f"<SystemDictionary(type={self.dict_type}, code={self.dict_code}, label={self.dict_label})>"


class AssetCustomField(Base):
    """资产自定义字段模型"""

    __tablename__ = "asset_custom_fields"

    id: Mapped[str] = mapped_column(
        String(50), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    field_name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="字段名称"
    )
    display_name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="显示名称"
    )
    field_type: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="字段类型"
    )
    is_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="是否必填"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment="是否启用"
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="排序"
    )
    default_value: Mapped[str | None] = mapped_column(Text, comment="默认值")
    field_options: Mapped[str | None] = mapped_column(Text, comment="字段选项(JSON)")
    validation_rules: Mapped[str | None] = mapped_column(Text, comment="验证规则(JSON)")
    help_text: Mapped[str | None] = mapped_column(Text, comment="帮助文本")
    description: Mapped[str | None] = mapped_column(Text, comment="描述")
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        comment="创建时间",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        onupdate=lambda: datetime.now(UTC).replace(tzinfo=None),
        comment="更新时间",
    )

    def __repr__(self) -> str:
        return f"<AssetCustomField(field_name={self.field_name}, display_name={self.display_name})>"


__all__ = ["SystemDictionary", "AssetCustomField"]
