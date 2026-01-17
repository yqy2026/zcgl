"""
缺陷跟踪数据模型和枚举定义
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class DefectSeverity(str, Enum):
    """缺陷严重程度"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DefectPriority(str, Enum):
    """缺陷优先级"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class DefectStatus(str, Enum):
    """缺陷状态"""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"
    REOPENED = "reopened"


class DefectCategory(str, Enum):
    """缺陷分类"""

    FUNCTIONAL = "functional"
    PERFORMANCE = "performance"
    SECURITY = "security"
    USABILITY = "usability"
    COMPATIBILITY = "compatibility"
    INTEGRATION = "integration"
    CONFIGURATION = "configuration"


class DefectReport(BaseModel):
    """缺陷报告模型"""

    defect_id: str | None = Field(None, description="缺陷ID")
    title: str = Field(..., description="缺陷标题")
    description: str = Field(..., description="缺陷描述")
    severity: DefectSeverity = Field(..., description="严重程度")
    priority: DefectPriority = Field(..., description="优先级")
    status: DefectStatus = Field(default=DefectStatus.OPEN, description="状态")
    category: DefectCategory = Field(..., description="分类")
    module: str = Field(..., description="所属模块")
    reproduction_steps: list[str] = Field(..., description="重现步骤")
    expected_behavior: str = Field(..., description="预期行为")
    actual_behavior: str = Field(..., description="实际行为")
    reporter: str = Field(..., description="报告人")
    assigned_to: str | None = Field(None, description="指派给")
    environment: str | None = Field(None, description="环境信息")
    attachments: list[str] | None = Field(default=[], description="附件")
    tags: list[str] | None = Field(default=[], description="标签")
    test_coverage_impact: dict[str, Any] | None = Field(
        None, description="测试覆盖率影响"
    )
    created_at: datetime | None = Field(None, description="创建时间")
    updated_at: datetime | None = Field(None, description="更新时间")
    resolved_at: datetime | None = Field(None, description="解决时间")
    fix_version: str | None = Field(None, description="修复版本")
    root_cause: str | None = Field(None, description="根本原因")
    resolution: str | None = Field(None, description="解决方案")


class DefectTrend(BaseModel):
    """缺陷趋势数据"""

    date: datetime = Field(..., description="日期")
    open_count: int = Field(..., description="新增缺陷数")
    resolved_count: int = Field(..., description="解决缺陷数")
    reopened_count: int = Field(..., description="重新打开数")
    total_active: int = Field(..., description="活跃缺陷总数")


class DefectAnalysis(BaseModel):
    """缺陷分析报告"""

    period_start: datetime = Field(..., description="分析开始时间")
    period_end: datetime = Field(..., description="分析结束时间")
    total_defects: int = Field(..., description="总缺陷数")
    new_defects: int = Field(..., description="新增缺陷数")
    resolved_defects: int = Field(..., description="解决缺陷数")
    average_resolution_time: float = Field(..., description="平均解决时间(小时)")
    severity_distribution: dict[str, int] = Field(..., description="严重程度分布")
    category_distribution: dict[str, int] = Field(..., description="分类分布")
    module_distribution: dict[str, int] = Field(..., description="模块分布")
    resolution_rate: float = Field(..., description="解决率")
    reopen_rate: float = Field(..., description="重新打开率")
    hotspots: list[dict[str, Any]] = Field(..., description="热点区域")
    recommendations: list[str] = Field(..., description="改进建议")


class DefectPrevention(BaseModel):
    """缺陷预防建议"""

    prevention_id: str = Field(..., description="预防ID")
    category: DefectCategory = Field(..., description="适用分类")
    title: str = Field(..., description="预防措施标题")
    description: str = Field(..., description="详细描述")
    implementation_steps: list[str] = Field(..., description="实施步骤")
    estimated_impact: str = Field(..., description="预期影响")
    priority: DefectPriority = Field(..., description="优先级")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
