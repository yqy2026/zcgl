"""
统一处理结果包模型定义

该模块定义了处理结果的统一外层包，以便后端与前端、
以及其他服务在不同实现之间共享一致的结构。
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict


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

    overall_quality: Optional[str] = None
    confidence_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    page_quality: Optional[Dict[str, Any]] = None
    ocr_suitability: Optional[Dict[str, Any]] = None
    issues: Optional[List[Dict[str, Any]]] = None
    recommendations: Optional[List[str]] = None


class QualityMetrics(BaseModel):
    """性能与质量相关指标。

    - concurrency_used: 实际并发度
    - pages_per_second: 吞吐量（页/秒）
    - processing_time_seconds: 处理总时长（秒）
    """

    concurrency_used: Optional[int] = None
    pages_per_second: Optional[float] = None
    processing_time_seconds: Optional[float] = None


class ProcessingResultEnvelope(BaseModel):
    """统一处理结果包。

    在不同处理路径（优化OCR、内置OCR或纯文本提取）下，
    提供稳定一致的顶层结构，便于持久化与API对齐。
    """

    success: bool = True
    text: Optional[str] = None
    pages: Optional[List[Dict[str, Any]]] = None
    total_pages: Optional[int] = None
    processing_method: Optional[str] = None
    ocr_used: Optional[bool] = None
    overall_confidence_score: Optional[float] = None

    quality_assessment: Optional[QualityAssessment] = None
    metrics: Optional[QualityMetrics] = None
    processing_stats: Optional[Dict[str, Any]] = None

    extraction_metadata: Optional[Dict[str, Any]] = None
    file_info: Optional[Dict[str, Any]] = None
    extracted_at: Optional[str] = None

    # 允许扩展字段以兼容历史或新增数据
    extra: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(
        arbitrary_types_allowed=True
    )