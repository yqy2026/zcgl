"""
统一处理结果包模型定义

该模块定义了处理结果的统一外层包，以便后端与前端、
以及其他服务在不同实现之间共享一致的结构。
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class QualityAssessment(BaseModel):
    """质量评估结构，与 optimized_ocr_service._assess_quality 输出对齐。

    约定字段：
    - overall_quality: 总体质量等级，例如 high/medium/low
    - confidence_score: 质量评估置信度 [0,1]
    - page_quality: 分页质量统计（可选）
    - ocr_suitability: 是否适合OCR及说明
    - issues: 发现的问题列表及建议
    - recommendations: 建议的处理动作（如提高DPI、启用特定语言等）
    """

    overall_quality: str | None = None
    confidence_score: float | None = Field(default=None, ge=0.0, le=1.0)
    page_quality: dict[str, Any] | None = None
    ocr_suitability: dict[str, Any] | None = None
    issues: list[dict[str, Any]] | None = None
    recommendations: list[str] | None = None


class QualityMetrics(BaseModel):
    """性能与质量相关指标。

    - concurrency_used: 实际并发度
    - pages_per_second: 吞吐量（页/秒）
    - processing_time_seconds: 处理总时长（秒）
    """

    concurrency_used: int | None = None
    pages_per_second: float | None = None
    processing_time_seconds: float | None = None


class ProcessingResultEnvelope(BaseModel):
    """统一处理结果包。

    在不同处理路径（优化OCR、内置OCR或纯文本提取）下，
    提供稳定一致的顶层结构，便于持久化与API对齐。
    """

    success: bool = True
    text: str | None = None
    pages: list[dict[str, Any]] | None = None
    total_pages: int | None = None
    processing_method: str | None = None
    ocr_used: bool | None = None
    overall_confidence_score: float | None = None

    quality_assessment: QualityAssessment | None = None
    metrics: QualityMetrics | None = None
    processing_stats: dict[str, Any] | None = None

    extraction_metadata: dict[str, Any] | None = None
    file_info: dict[str, Any] | None = None
    extracted_at: str | None = None

    # 允许扩展字段以兼容历史或新增数据
    extra: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(arbitrary_types_allowed=True)
