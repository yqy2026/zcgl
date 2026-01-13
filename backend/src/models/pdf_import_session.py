"""
PDF导入会话数据模型
用于跟踪PDF文件处理进度和状态
"""

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from ..database import Base


class SessionStatus(str, enum.Enum):
    """会话状态枚举"""

    UPLOADING = "uploading"  # 文件上传中
    UPLOADED = "uploaded"  # 文件上传完成
    PROCESSING = "processing"  # PDF处理中
    TEXT_EXTRACTED = "text_extracted"  # 文本提取完成
    INFO_EXTRACTED = "info_extracted"  # 信息提取完成
    VALIDATING = "validating"  # 数据验证中
    MATCHING = "matching"  # 数据匹配中
    READY_FOR_REVIEW = "ready_for_review"  # 待用户确认
    COMPLETED = "completed"  # 处理完成
    FAILED = "failed"  # 处理失败
    CANCELLED = "cancelled"  # 用户取消
    CONFIRMED = "confirmed"  # 用户确认导入


class ProcessingStep(str, enum.Enum):
    """处理步骤枚举"""

    FILE_UPLOAD = "file_upload"  # 文件上传
    PDF_CONVERSION = "pdf_conversion"  # PDF转换
    TEXT_EXTRACTION = "text_extraction"  # 文本提取
    INFO_EXTRACTION = "info_extraction"  # 信息提取
    DATA_VALIDATION = "data_validation"  # 数据验证
    ASSET_MATCHING = "asset_matching"  # 资产匹配
    OWNERSHIP_MATCHING = "ownership_matching"  # 权属方匹配
    DUPLICATE_CHECK = "duplicate_check"  # 重复检查
    FINAL_REVIEW = "final_review"  # 最终审核


class PDFImportSession(Base):  # type: ignore[valid-type, misc]
    """PDF导入会话模型"""

    __tablename__ = "pdf_import_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)

    # 文件信息
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    file_path: Mapped[str | None] = mapped_column(String(1000))
    content_type: Mapped[str] = mapped_column(String(100), default="application/pdf")

    # 状态信息
    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus), default=SessionStatus.UPLOADING, nullable=False
    )
    current_step: Mapped[ProcessingStep | None] = mapped_column(Enum(ProcessingStep))
    progress_percentage: Mapped[float] = mapped_column(Float, default=0.0)
    error_message: Mapped[str | None] = mapped_column(Text)

    # 处理结果数据
    extracted_text: Mapped[str | None] = mapped_column(Text)  # 原始提取的文本
    extracted_data: Mapped[dict[str, Any] | None] = mapped_column(JSON)  # 提取的结构化数据
    # 完整处理结果（包含质量评估与性能指标，如并发和吞吐量）
    processing_result: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    validation_results: Mapped[dict[str, Any] | None] = mapped_column(JSON)  # 验证结果
    matching_results: Mapped[dict[str, Any] | None] = mapped_column(JSON)  # 匹配结果
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)  # 整体置信度

    # 处理配置
    processing_method: Mapped[str | None] = mapped_column(String(50))  # pdfplumber, markitdown, ocr
    ocr_used: Mapped[bool] = mapped_column(Boolean, default=False)
    processing_options: Mapped[dict[str, Any] | None] = mapped_column(JSON)  # 用户选择的处理选项

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # 用户信息
    user_id: Mapped[int | None] = mapped_column(Integer)  # 处理用户ID
    organization_id: Mapped[int | None] = mapped_column(Integer)  # 组织ID

    def __repr__(self) -> str:
        return f"<PDFImportSession(session_id='{self.session_id}', status='{self.status}', progress={self.progress_percentage}%>)"  # pragma: no cover

    @property
    def is_processing(self) -> bool:
        """是否正在处理中"""
        return self.status in [  # pragma: no cover
            SessionStatus.UPLOADING,  # pragma: no cover
            SessionStatus.PROCESSING,  # pragma: no cover
            SessionStatus.TEXT_EXTRACTED,  # pragma: no cover
            SessionStatus.INFO_EXTRACTED,  # pragma: no cover
            SessionStatus.VALIDATING,  # pragma: no cover
            SessionStatus.MATCHING,  # pragma: no cover
        ]  # pragma: no cover

    @property
    def is_completed(self) -> bool:
        """是否已完成处理"""
        return self.status in [  # pragma: no cover
            SessionStatus.COMPLETED,  # pragma: no cover
            SessionStatus.FAILED,  # pragma: no cover
            SessionStatus.CANCELLED,  # pragma: no cover
        ]  # pragma: no cover

    @property
    def needs_user_action(self) -> bool:
        """是否需要用户操作"""
        return self.status == SessionStatus.READY_FOR_REVIEW  # pragma: no cover


class SessionLog(Base):  # type: ignore[valid-type, misc]
    """会话操作日志"""

    __tablename__ = "pdf_import_session_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # 日志信息
    step: Mapped[ProcessingStep] = mapped_column(Enum(ProcessingStep), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)  # started, completed, failed, warning
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON)  # 详细信息

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # 性能数据
    duration_ms: Mapped[float | None] = mapped_column(Float)  # 处理耗时
    memory_usage_mb: Mapped[float | None] = mapped_column(Float)  # 内存使用

    def __repr__(self) -> str:
        return f"<SessionLog(session_id='{self.session_id}', step='{self.step}', status='{self.status}')>"  # pragma: no cover


class ProcessingConfiguration(Base):  # type: ignore[valid-type, misc]
    """处理配置模型"""

    __tablename__ = "pdf_import_configurations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # PDF处理配置
    prefer_ocr: Mapped[bool] = mapped_column(Boolean, default=False)
    ocr_languages: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=list)  # OCR识别语言
    dpi: Mapped[int] = mapped_column(Integer, default=300)  # OCR分辨率
    max_pages: Mapped[int] = mapped_column(Integer, default=100)  # 最大处理页数

    # 信息提取配置
    extraction_confidence_threshold: Mapped[float] = mapped_column(Float, default=0.7)
    validate_fields: Mapped[bool] = mapped_column(Boolean, default=True)
    strict_validation: Mapped[bool] = mapped_column(Boolean, default=False)

    # 匹配配置
    enable_asset_matching: Mapped[bool] = mapped_column(Boolean, default=True)
    enable_ownership_matching: Mapped[bool] = mapped_column(Boolean, default=True)
    enable_duplicate_check: Mapped[bool] = mapped_column(Boolean, default=True)
    matching_threshold: Mapped[float] = mapped_column(Float, default=0.8)

    # 用户偏好
    auto_confirm_high_confidence: Mapped[bool] = mapped_column(Boolean, default=False)
    notification_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<ProcessingConfiguration(session_id='{self.session_id}', prefer_ocr={self.prefer_ocr})>"  # pragma: no cover
