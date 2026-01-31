"""
Metrics and performance settings.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel, Field, field_validator
from pydantic_core import PydanticCustomError

logger = logging.getLogger(__name__)


class MetricsSettings(BaseModel):
    """性能监控配置"""

    ENABLE_METRICS: bool = Field(
        default=True, json_schema_extra={"env": "ENABLE_METRICS"}
    )
    SLOW_QUERY_THRESHOLD: float = Field(
        default=1.0, json_schema_extra={"env": "SLOW_QUERY_THRESHOLD"}
    )

    @field_validator("SLOW_QUERY_THRESHOLD")
    @classmethod
    def validate_slow_query_threshold(cls, v: float) -> float:
        """验证慢查询阈值"""
        if v < 0:
            raise PydanticCustomError(
                "invalid_slow_query_threshold",
                "慢查询阈值不能为负数，当前值: {value}",
                {"value": v},
            )
        if v > 60:
            logger.warning(f"慢查询阈值 {v} 秒过高，建议设置为 0.1-10 秒之间")
        return v
