"""
LLM Prompt管理的Pydantic Schema
用于API请求和响应的数据验证
"""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field

# ============================================================================
# Prompt模板相关Schema
# ============================================================================


class PromptTemplateBase(BaseModel):
    """Prompt模板基础Schema"""

    name: str = Field(..., min_length=1, max_length=100, description="Prompt名称")
    doc_type: str = Field(..., description="文档类型: CONTRACT, PROPERTY_CERT等")
    provider: str = Field(..., description="LLM提供商: qwen, hunyuan, deepseek, glm")
    description: str | None = Field(None, max_length=500, description="Prompt描述")
    system_prompt: str = Field(..., min_length=1, description="系统提示词")
    user_prompt_template: str = Field(..., min_length=1, description="用户提示词模板")
    few_shot_examples: dict[str, Any] | None = Field(
        default={}, description="Few-shot示例"
    )
    tags: list[str] | None = Field(default=[], description="标签列表")


class PromptTemplateCreate(PromptTemplateBase):
    """创建Prompt模板"""

    pass


class PromptTemplateUpdate(BaseModel):
    """更新Prompt模板"""

    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    system_prompt: str | None = Field(None, min_length=1)
    user_prompt_template: str | None = Field(None, min_length=1)
    few_shot_examples: dict[str, Any] | None = None
    tags: list[str] | None = None
    change_description: str | None = Field(None, max_length=500, description="变更说明")


class PromptTemplateResponse(PromptTemplateBase):
    """Prompt模板响应"""

    id: str
    version: str
    status: str
    avg_accuracy: float
    avg_confidence: float
    total_usage: int
    current_version_id: str | None
    created_at: datetime
    updated_at: datetime
    created_by: str | None

    class Config:
        from_attributes = True


class PromptTemplateListResponse(BaseModel):
    """Prompt模板列表响应"""

    items: list[PromptTemplateResponse]
    total: int
    page: int
    limit: int


# ============================================================================
# Prompt版本相关Schema
# ============================================================================


class PromptVersionResponse(BaseModel):
    """Prompt版本响应"""

    id: str
    template_id: str
    version: str
    system_prompt: str
    user_prompt_template: str
    few_shot_examples: dict[str, Any]
    change_description: str
    change_type: str
    auto_generated: bool
    accuracy: float | None
    confidence: float | None
    usage_count: int
    created_at: datetime
    created_by: str | None

    class Config:
        from_attributes = True


class PromptVersionHistory(BaseModel):
    """Prompt版本历史"""

    template_id: str
    versions: list[PromptVersionResponse]


# ============================================================================
# 反馈相关Schema
# ============================================================================


class ExtractionFeedbackCreate(BaseModel):
    """创建提取反馈"""

    template_id: str
    version_id: str | None
    doc_type: str
    file_path: str
    session_id: str | None
    field_name: str
    original_value: str
    corrected_value: str
    confidence_before: float
    user_action: str = Field(..., description="用户动作: corrected, accepted, rejected")


class ExtractionFeedbackResponse(BaseModel):
    """提取反馈响应"""

    id: str
    template_id: str
    version_id: str | None
    doc_type: str
    field_name: str
    original_value: str
    corrected_value: str
    confidence_before: float
    user_action: str
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# 性能指标相关Schema
# ============================================================================


class PromptMetricsResponse(BaseModel):
    """Prompt性能指标响应"""

    id: str
    template_id: str
    version_id: str | None
    date: date
    total_extractions: int
    successful_extractions: int
    corrected_fields: int
    avg_accuracy: float
    avg_confidence: float

    class Config:
        from_attributes = True


class MetricsDashboard(BaseModel):
    """性能指标Dashboard"""

    total_extractions: int
    avg_accuracy: float
    avg_confidence: float
    total_corrections: int
    daily_accuracy: list[dict[str, Any]]
    field_errors: list[dict[str, Any]]


# ============================================================================
# 操作相关Schema
# ============================================================================


class PromptOptimizationResult(BaseModel):
    """Prompt优化结果"""

    template_id: str
    old_version: str
    new_version: str
    rules_added: int
    feedback_count: int
    improvement_summary: str


class PromptRollbackRequest(BaseModel):
    """Prompt回滚请求"""

    version_id: str = Field(..., description="要回滚到的目标版本ID")


class PromptActivationRequest(BaseModel):
    """Prompt激活请求"""

    template_id: str = Field(..., description="要激活的Prompt模板ID")
