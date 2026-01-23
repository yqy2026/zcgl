"""
PDF导入相关的Pydantic模型

从 pdf_import_unified.py 提取的DTOs
"""

from typing import Any

from pydantic import BaseModel, Field


# === V1兼容性数据传输对象 ===
class ExtractionRequest(BaseModel):
    """PDF信息提取请求模型 (V1兼容)"""

    text: str
    should_include_raw_text: bool = Field(default=False, description="是否包含原始文本")
    should_validate_fields: bool = Field(default=True, description="是否验证字段有效性")


class ExtractionResponse(BaseModel):
    """PDF信息提取响应模型 (V1兼容)"""

    success: bool
    extractor_used: str = "rental_contract_extractor"
    confidence: float = 0.0
    extracted_fields: dict[str, Any] = {}
    validation_results: dict[str, Any] = {}
    error: str | None = None
    processing_time_ms: float = 0.0
    real_data_verified: bool = False


# === 数据传输对象 (DTOs) ===
class FileUploadResponse(BaseModel):
    """文件上传响应"""

    success: bool
    message: str
    session_id: str | None = None
    estimated_time: str | None = None
    error: str | None = None


class SessionProgressResponse(BaseModel):
    """会话进度响应"""

    success: bool
    session_status: dict[str, Any] | None = None
    error: str | None = None


class MatchingResults(BaseModel):
    """匹配结果详细模型"""

    matched_assets: list[dict[str, Any]] = []
    matched_ownerships: list[dict[str, Any]] = []
    duplicate_contracts: list[dict[str, Any]] = []
    recommendations: dict[str, str] = {}
    overall_match_confidence: float = 0.0


class ExtractionResult(BaseModel):
    """提取结果详细模型"""

    success: bool
    data: dict[str, Any] = {}
    confidence_score: float = 0.0
    extraction_method: str = ""
    processed_fields: int = 0
    total_fields: int = 0
    error: str | None = None


class ValidationResult(BaseModel):
    """验证结果详细模型"""

    success: bool
    errors: list[str] = []
    warnings: list[str] = []
    validated_data: dict[str, Any] = {}
    validation_score: float = 0.0
    processed_fields: int = 0
    required_fields_count: int = 0
    missing_required_fields: list[str] = []


class ConfirmImportRequest(BaseModel):
    """确认导入请求"""

    session_id: str
    confirmed_data: dict[str, Any]
    selected_asset_id: str | None = None
    selected_ownership_id: str | None = None


class ConfirmImportResponse(BaseModel):
    """确认导入响应"""

    success: bool
    message: str
    contract_id: str | None = None
    contract_number: str | None = None
    created_terms_count: int | None = None
    processing_time: float | None = None
    error: str | None = None


class ActiveSessionResponse(BaseModel):
    """活跃会话响应"""

    success: bool
    active_sessions: list[dict[str, Any]]
    total_count: int
    error: str | None = None


class SystemCapabilities(BaseModel):
    """系统能力"""

    pdfplumber_available: bool = True
    pymupdf_available: bool = True
    spacy_available: bool = True
    ocr_available: bool = True
    supported_formats: list[str] = [".pdf", ".jpg", ".jpeg", ".png"]
    max_file_size_mb: int = 50
    estimated_processing_time: str = "10-30秒"


class SystemInfoResponse(BaseModel):
    """系统信息响应"""

    success: bool
    message: str
    capabilities: SystemCapabilities
    extractor_summary: dict[str, Any] | None = None
    validator_summary: dict[str, Any] | None = None
