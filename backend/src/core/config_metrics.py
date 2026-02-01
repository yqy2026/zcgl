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
    SENTRY_ENABLED: bool = Field(
        default=False, json_schema_extra={"env": "SENTRY_ENABLED"}
    )
    SENTRY_DSN: str | None = Field(
        default=None, json_schema_extra={"env": "SENTRY_DSN"}
    )
    SENTRY_ENVIRONMENT: str | None = Field(
        default=None, json_schema_extra={"env": "SENTRY_ENVIRONMENT"}
    )
    SENTRY_TRACES_SAMPLE_RATE: float = Field(
        default=0.0, json_schema_extra={"env": "SENTRY_TRACES_SAMPLE_RATE"}
    )
    SENTRY_PROFILES_SAMPLE_RATE: float = Field(
        default=0.0, json_schema_extra={"env": "SENTRY_PROFILES_SAMPLE_RATE"}
    )
    SENTRY_SEND_DEFAULT_PII: bool = Field(
        default=False, json_schema_extra={"env": "SENTRY_SEND_DEFAULT_PII"}
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

    @field_validator("SENTRY_TRACES_SAMPLE_RATE", "SENTRY_PROFILES_SAMPLE_RATE")
    @classmethod
    def validate_sentry_sample_rate(cls, v: float) -> float:
        """验证 Sentry 采样率"""
        if v < 0 or v > 1:
            raise PydanticCustomError(
                "invalid_sample_rate",
                "Sentry采样率必须在 0 到 1 之间，当前值: {value}",
                {"value": v},
            )
        return v
