"""
Cache settings.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel, Field, model_validator
from pydantic_core import PydanticCustomError

logger = logging.getLogger(__name__)


class CacheSettings(BaseModel):
    """缓存配置"""

    CACHE_TTL: int = Field(
        default=3600, json_schema_extra={"env": "CACHE_TTL"}
    )  # 1小时
    CACHE_PREFIX: str = Field(default="zcgl", json_schema_extra={"env": "CACHE_PREFIX"})

    @model_validator(mode="after")
    def validate_cache_configuration(self) -> "CacheSettings":
        """验证缓存配置一致性"""
        if self.CACHE_TTL < 0:
            raise PydanticCustomError(
                "invalid_cache_ttl",
                "CACHE_TTL 不能为负数，当前值: {value}",
                {"value": self.CACHE_TTL},
            )
        if self.CACHE_TTL > 86400:  # 24小时
            logger.warning(
                f"CACHE_TTL ({self.CACHE_TTL}s) 超过 24 小时，可能导致缓存数据过期"
            )
        return self
