"""
系统监控数据模型定义
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SystemMetrics(BaseModel):
    """系统性能指标模型"""

    timestamp: datetime = Field(..., description="指标采集时间")
    cpu_percent: float = Field(..., ge=0, le=100, description="CPU使用率(%)")
    memory_percent: float = Field(..., ge=0, le=100, description="内存使用率(%)")
    memory_available_gb: float = Field(..., ge=0, description="可用内存(GB)")
    disk_usage_percent: float = Field(..., ge=0, le=100, description="磁盘使用率(%)")
    disk_free_gb: float = Field(..., ge=0, description="可用磁盘空间(GB)")
    network_io: dict[str, int] = Field(..., description="网络IO统计")
    process_count: int = Field(..., ge=0, description="运行进程数")
    load_average: list[float] | None = Field(None, description="系统负载平均值")

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})


class ApplicationMetrics(BaseModel):
    """应用性能指标模型"""

    timestamp: datetime = Field(..., description="指标采集时间")
    active_connections: int = Field(..., ge=0, description="活跃连接数")
    total_requests: int = Field(..., ge=0, description="总请求数")
    average_response_time: float = Field(..., ge=0, description="平均响应时间(ms)")
    error_rate: float = Field(..., ge=0, le=100, description="错误率(%)")
    cache_hit_rate: float = Field(..., ge=0, le=100, description="缓存命中率(%)")
    database_connections: int = Field(..., ge=0, description="数据库连接数")

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})


class HealthStatus(BaseModel):
    """健康状态模型"""

    status: str = Field(
        ..., pattern="^(healthy|degraded|unhealthy)$", description="健康状态"
    )
    timestamp: datetime = Field(..., description="检查时间")
    components: dict[str, dict[str, Any]] = Field(..., description="组件状态详情")
    overall_score: float = Field(..., ge=0, le=100, description="总体健康评分")

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})


class PerformanceAlert(BaseModel):
    """性能告警模型"""

    id: str = Field(..., description="告警ID")
    level: str = Field(..., pattern="^(info|warning|critical)$", description="告警级别")
    message: str = Field(..., description="告警消息")
    metric_name: str = Field(..., description="指标名称")
    current_value: float = Field(..., description="当前值")
    threshold: float = Field(..., description="阈值")
    timestamp: datetime = Field(..., description="告警时间")
    resolved: bool = Field(False, description="是否已解决")

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})


class DatabaseHealthMetrics(BaseModel):
    """数据库健康指标模型"""

    timestamp: datetime = Field(..., description="指标采集时间")
    connection_pool_status: dict[str, Any] = Field(..., description="连接池状态")
    active_connections: int = Field(..., ge=0, description="活跃连接数")
    total_queries: int = Field(..., ge=0, description="总查询数")
    slow_queries: int = Field(..., ge=0, description="慢查询数")
    avg_response_time: float = Field(..., ge=0, description="平均响应时间(ms)")
    pool_hit_rate: float = Field(..., ge=0, le=100, description="连接池命中率(%)")
    database_size_mb: float = Field(..., ge=0, description="数据库大小(MB)")
    health_score: float = Field(..., ge=0, le=100, description="数据库健康评分")

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})


class DatabaseOptimizationReport(BaseModel):
    """数据库优化报告模型"""

    timestamp: datetime = Field(..., description="报告生成时间")
    actions_taken: list[str] = Field(..., description="已执行的优化操作")
    recommendations: list[str] = Field(..., description="优化建议")
    performance_improvement: dict[str, float] = Field(..., description="性能改进指标")
    cleanup_results: dict[str, Any] = Field(..., description="清理结果")

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})
