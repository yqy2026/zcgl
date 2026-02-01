"""
Pagination settings.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, ValidationInfo, field_validator, model_validator
from pydantic_core import PydanticCustomError


class PaginationSettings(BaseModel):
    """分页配置"""

    DEFAULT_PAGE_SIZE: int = Field(
        default=20, json_schema_extra={"env": "DEFAULT_PAGE_SIZE"}
    )
    MAX_PAGE_SIZE: int = Field(default=100, json_schema_extra={"env": "MAX_PAGE_SIZE"})

    @field_validator("DEFAULT_PAGE_SIZE", "MAX_PAGE_SIZE")
    @classmethod
    def validate_page_size(cls, v: int, info: ValidationInfo) -> int:
        """验证分页大小"""
        if v < 1:
            raise PydanticCustomError(
                "page_size_too_small",
                "{field} 不能小于 1，当前值: {value}",
                {"field": info.field_name, "value": v},
            )
        if v > 1000:
            raise PydanticCustomError(
                "page_size_too_large",
                "{field} 不能大于 1000，当前值: {value}",
                {"field": info.field_name, "value": v},
            )
        return v

    @field_validator("DEFAULT_PAGE_SIZE")
    @classmethod
    def validate_default_page_size_not_exceed_max(cls, v: int) -> int:
        """验证默认分页大小不超过最大值"""
        # 这个验证器会在 MAX_PAGE_SIZE 之后运行
        return v

    @model_validator(mode="after")
    def validate_page_size_consistency(self) -> PaginationSettings:
        """验证分页大小一致性 - DEFAULT_PAGE_SIZE 不能超过 MAX_PAGE_SIZE"""
        if self.DEFAULT_PAGE_SIZE > self.MAX_PAGE_SIZE:
            raise PydanticCustomError(
                "page_size_inconsistent",
                "DEFAULT_PAGE_SIZE ({default_size}) 不能超过 MAX_PAGE_SIZE ({max_size})",
                {
                    "default_size": self.DEFAULT_PAGE_SIZE,
                    "max_size": self.MAX_PAGE_SIZE,
                },
            )
        return self
