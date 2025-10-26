"""
PDF导入会话数据模型
用于跟踪PDF文件处理进度和状态
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Float, JSON, Boolean, Enum
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func
from datetime import datetime
import enum

Base = declarative_base()

class SessionStatus(str, enum.Enum):
    """会话状态枚举"""
    UPLOADING = "uploading"           # 文件上传中
    UPLOADED = "uploaded"             # 文件上传完成
    PROCESSING = "processing"         # PDF处理中
    TEXT_EXTRACTED = "text_extracted" # 文本提取完成
    INFO_EXTRACTED = "info_extracted" # 信息提取完成
    VALIDATING = "validating"         # 数据验证中
    MATCHING = "matching"             # 数据匹配中
    READY_FOR_REVIEW = "ready_for_review"  # 待用户确认
    COMPLETED = "completed"           # 处理完成
    FAILED = "failed"                 # 处理失败
    CANCELLED = "cancelled"           # 用户取消
    CONFIRMED = "confirmed"           # 用户确认导入

class ProcessingStep(str, enum.Enum):
    """处理步骤枚举"""
    FILE_UPLOAD = "file_upload"                    # 文件上传
    PDF_CONVERSION = "pdf_conversion"              # PDF转换
    TEXT_EXTRACTION = "text_extraction"            # 文本提取
    INFO_EXTRACTION = "info_extraction"            # 信息提取
    DATA_VALIDATION = "data_validation"            # 数据验证
    ASSET_MATCHING = "asset_matching"              # 资产匹配
    OWNERSHIP_MATCHING = "ownership_matching"      # 权属方匹配
    DUPLICATE_CHECK = "duplicate_check"            # 重复检查
    FINAL_REVIEW = "final_review"                  # 最终审核

class PDFImportSession(Base):
    """PDF导入会话模型"""
    __tablename__ = "pdf_import_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), unique=True, index=True, nullable=False)

    # 文件信息
    original_filename = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_path = Column(String(1000))
    content_type = Column(String(100), default="application/pdf")

    # 状态信息
    status = Column(Enum(SessionStatus), default=SessionStatus.UPLOADING, nullable=False)
    current_step = Column(Enum(ProcessingStep))
    progress_percentage = Column(Float, default=0.0)
    error_message = Column(Text)

    # 处理结果数据
    extracted_text = Column(Text)  # 原始提取的文本
    extracted_data = Column(JSON)  # 提取的结构化数据
    validation_results = Column(JSON)  # 验证结果
    matching_results = Column(JSON)   # 匹配结果
    confidence_score = Column(Float, default=0.0)  # 整体置信度

    # 处理配置
    processing_method = Column(String(50))  # pdfplumber, markitdown, ocr
    ocr_used = Column(Boolean, default=False)
    processing_options = Column(JSON)  # 用户选择的处理选项

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True))

    # 用户信息
    user_id = Column(Integer)  # 处理用户ID
    organization_id = Column(Integer)  # 组织ID

    def __repr__(self):
        return f"<PDFImportSession(session_id='{self.session_id}', status='{self.status}', progress={self.progress_percentage}%)>"

    @property
    def is_processing(self) -> bool:
        """是否正在处理中"""
        return self.status in [
            SessionStatus.UPLOADING,
            SessionStatus.PROCESSING,
            SessionStatus.TEXT_EXTRACTED,
            SessionStatus.INFO_EXTRACTED,
            SessionStatus.VALIDATING,
            SessionStatus.MATCHING
        ]

    @property
    def is_completed(self) -> bool:
        """是否已完成处理"""
        return self.status in [
            SessionStatus.COMPLETED,
            SessionStatus.FAILED,
            SessionStatus.CANCELLED
        ]

    @property
    def needs_user_action(self) -> bool:
        """是否需要用户操作"""
        return self.status == SessionStatus.READY_FOR_REVIEW

class SessionLog(Base):
    """会话操作日志"""
    __tablename__ = "pdf_import_session_logs"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), nullable=False, index=True)

    # 日志信息
    step = Column(Enum(ProcessingStep), nullable=False)
    status = Column(String(50), nullable=False)  # started, completed, failed, warning
    message = Column(Text, nullable=False)
    details = Column(JSON)  # 详细信息

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 性能数据
    duration_ms = Column(Float)  # 处理耗时
    memory_usage_mb = Column(Float)  # 内存使用

    def __repr__(self):
        return f"<SessionLog(session_id='{self.session_id}', step='{self.step}', status='{self.status}')>"

class ProcessingConfiguration(Base):
    """处理配置模型"""
    __tablename__ = "pdf_import_configurations"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), unique=True, nullable=False, index=True)

    # PDF处理配置
    prefer_ocr = Column(Boolean, default=False)
    ocr_languages = Column(JSON, default=["zh", "en"])  # OCR识别语言
    dpi = Column(Integer, default=300)  # OCR分辨率
    max_pages = Column(Integer, default=100)  # 最大处理页数

    # 信息提取配置
    extraction_confidence_threshold = Column(Float, default=0.7)
    validate_fields = Column(Boolean, default=True)
    strict_validation = Column(Boolean, default=False)

    # 匹配配置
    enable_asset_matching = Column(Boolean, default=True)
    enable_ownership_matching = Column(Boolean, default=True)
    enable_duplicate_check = Column(Boolean, default=True)
    matching_threshold = Column(Float, default=0.8)

    # 用户偏好
    auto_confirm_high_confidence = Column(Boolean, default=False)
    notification_enabled = Column(Boolean, default=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<ProcessingConfiguration(session_id='{self.session_id}', prefer_ocr={self.prefer_ocr})>"