"""
LLM Prompt管理相关数据模型
用于统一管理系统中的所有LLM Prompt模板
"""

import uuid
from datetime import UTC, date, datetime
from enum import Enum
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class PromptStatus(str, Enum):
    """Prompt状态枚举"""

    DRAFT = "draft"  # 草稿
    ACTIVE = "active"  # 活跃(正在使用)
    ARCHIVED = "archived"  # 已归档


class PromptTemplate(Base):
    """Prompt模板表 - 存储所有LLM Prompt模板"""

    __tablename__ = "prompt_templates"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # 基本信息
    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        comment="Prompt名称,如: contract_extraction_v1",
    )
    doc_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="文档类型: CONTRACT, PROPERTY_CERT等",
    )
    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="LLM提供商: qwen, hunyuan, deepseek, glm",
    )
    description: Mapped[str | None] = mapped_column(String(500), comment="Prompt描述")

    # Prompt内容
    system_prompt: Mapped[str] = mapped_column(
        Text, nullable=False, comment="系统提示词"
    )
    user_prompt_template: Mapped[str] = mapped_column(
        Text, nullable=False, comment="用户提示词模板,可用变量如{file_name}"
    )
    few_shot_examples: Mapped[dict[str, Any]] = mapped_column(
        JSON, comment="Few-shot示例(JSON格式)"
    )

    # 元数据
    version: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="版本号: v1.0.0"
    )
    status: Mapped[PromptStatus] = mapped_column(
        String(20), default=PromptStatus.DRAFT, comment="状态: draft, active, archived"
    )
    tags: Mapped[list[str]] = mapped_column(
        JSON, comment="标签列表,如: ['optimized', 'stable']"
    )

    # 性能指标
    avg_accuracy: Mapped[float] = mapped_column(
        Float, default=0.0, comment="平均准确率(0-1)"
    )
    avg_confidence: Mapped[float] = mapped_column(
        Float, default=0.0, comment="平均置信度(0-1)"
    )
    total_usage: Mapped[int] = mapped_column(Integer, default=0, comment="总使用次数")

    # 关系
    current_version_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("prompt_versions.id"), comment="当前版本ID"
    )
    parent_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("prompt_templates.id"), comment="父模板ID(用于派生Prompt)"
    )

    # 审计字段
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        comment="更新时间",
    )
    created_by: Mapped[str | None] = mapped_column(String(100), comment="创建人ID")

    # 关系
    versions: Mapped[list["PromptVersion"]] = relationship(
        "PromptVersion",
        back_populates="template",
        foreign_keys="PromptVersion.template_id",
    )
    feedbacks: Mapped[list["ExtractionFeedback"]] = relationship(
        "ExtractionFeedback", back_populates="template"
    )
    metrics: Mapped[list["PromptMetrics"]] = relationship(
        "PromptMetrics", back_populates="template"
    )


class PromptVersion(Base):
    """Prompt版本表 - 存储Prompt的所有历史版本"""

    __tablename__ = "prompt_versions"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # 关联
    template_id: Mapped[str] = mapped_column(
        String, ForeignKey("prompt_templates.id"), nullable=False, index=True
    )

    # 版本信息
    version: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="版本号: v1.0.0, v1.0.1等"
    )

    # 完整的Prompt快照
    system_prompt: Mapped[str] = mapped_column(
        Text, nullable=False, comment="系统提示词快照"
    )
    user_prompt_template: Mapped[str] = mapped_column(
        Text, nullable=False, comment="用户提示词模板快照"
    )
    few_shot_examples: Mapped[dict[str, Any]] = mapped_column(
        JSON, comment="Few-shot示例快照"
    )

    # 变更信息
    change_description: Mapped[str] = mapped_column(String(500), comment="变更描述")
    change_type: Mapped[str] = mapped_column(
        String(50), comment="变更类型: created, optimized, rollback"
    )
    auto_generated: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="是否为自动生成"
    )

    # 性能指标
    accuracy: Mapped[float | None] = mapped_column(Float, comment="该版本的准确率")
    confidence: Mapped[float | None] = mapped_column(
        Float, comment="该版本的平均置信度"
    )
    usage_count: Mapped[int] = mapped_column(Integer, default=0, comment="使用次数")

    # 审计字段
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), comment="创建时间"
    )
    created_by: Mapped[str | None] = mapped_column(String(100), comment="创建人ID")

    # 关系
    template: Mapped["PromptTemplate"] = relationship(
        "PromptTemplate", back_populates="versions", foreign_keys=[template_id]
    )
    feedbacks: Mapped[list["ExtractionFeedback"]] = relationship(
        "ExtractionFeedback", back_populates="version"
    )
    metrics: Mapped[list["PromptMetrics"]] = relationship(
        "PromptMetrics", back_populates="version"
    )


class ExtractionFeedback(Base):
    """提取反馈表 - 收集用户对识别结果的修正"""

    __tablename__ = "extraction_feedback"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # 关联
    template_id: Mapped[str] = mapped_column(
        String, ForeignKey("prompt_templates.id"), nullable=False, index=True
    )
    version_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("prompt_versions.id"), index=True
    )

    # 文档信息
    doc_type: Mapped[str] = mapped_column(String(50), comment="文档类型")
    file_path: Mapped[str] = mapped_column(String(500), comment="文件路径")
    session_id: Mapped[str | None] = mapped_column(String(100), comment="导入会话ID")

    # 反馈内容
    field_name: Mapped[str] = mapped_column(String(100), comment="字段名称")
    original_value: Mapped[str] = mapped_column(Text, comment="原始识别值")
    corrected_value: Mapped[str] = mapped_column(Text, comment="用户修正后的值")

    # 上下文
    confidence_before: Mapped[float] = mapped_column(Float, comment="修正前的置信度")
    user_action: Mapped[str] = mapped_column(
        String(50), comment="用户动作: corrected, accepted, rejected"
    )

    # 🔒 安全修复: 添加用户ID用于审计和追踪
    user_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("users.id"), index=True, comment="提交反馈的用户ID"
    )

    # 审计字段
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), comment="创建时间"
    )

    # 关系
    template: Mapped["PromptTemplate"] = relationship(
        "PromptTemplate", back_populates="feedbacks"
    )
    version: Mapped["PromptVersion"] = relationship(
        "PromptVersion", back_populates="feedbacks"
    )


class PromptMetrics(Base):
    """Prompt性能指标表 - 按日期聚合的统计指标"""

    __tablename__ = "prompt_metrics"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # 关联
    template_id: Mapped[str] = mapped_column(
        String, ForeignKey("prompt_templates.id"), nullable=False, index=True
    )
    version_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("prompt_versions.id"), index=True
    )

    # 时间窗口
    date: Mapped[date] = mapped_column(
        Date, nullable=False, index=True, comment="统计日期"
    )

    # 指标
    total_extractions: Mapped[int] = mapped_column(
        Integer, default=0, comment="总提取次数"
    )
    successful_extractions: Mapped[int] = mapped_column(
        Integer, default=0, comment="成功提取次数(置信度≥0.8)"
    )
    corrected_fields: Mapped[int] = mapped_column(
        Integer, default=0, comment="用户修正的字段数"
    )

    avg_accuracy: Mapped[float] = mapped_column(
        Float, default=0.0, comment="平均准确率"
    )
    avg_confidence: Mapped[float] = mapped_column(
        Float, default=0.0, comment="平均置信度"
    )

    # 审计字段
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), comment="创建时间"
    )

    # 关系
    template: Mapped["PromptTemplate"] = relationship(
        "PromptTemplate", back_populates="metrics"
    )
    version: Mapped["PromptVersion"] = relationship(
        "PromptVersion", back_populates="metrics"
    )
