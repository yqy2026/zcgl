"""
Logging settings.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel, Field, field_validator
from pydantic_core import PydanticCustomError

logger = logging.getLogger(__name__)


class LoggingSettings(BaseModel):
    """日志配置"""

    LOG_LEVEL: str = Field(default="INFO", json_schema_extra={"env": "LOG_LEVEL"})
    LOG_FILE: str | None = Field(default=None, json_schema_extra={"env": "LOG_FILE"})

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """验证日志级别"""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise PydanticCustomError(
                "invalid_log_level",
                "无效的日志级别: {level}. 有效值为: {valid_levels}",
                {
                    "level": v,
                    "valid_levels": ", ".join(sorted(valid_levels)),
                },
            )
        return v_upper
