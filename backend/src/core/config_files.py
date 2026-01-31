"""
File upload settings.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator
from pydantic_core import PydanticCustomError

from ..constants.rent_contract_constants import CONTRACT_ATTACHMENT_SUBDIR
from ..constants.file_size_constants import (
    DEFAULT_MAX_FILE_SIZE,
    MAX_FILE_SIZE_LIMIT,
    MIN_FILE_SIZE_BYTES,
)


class FileUploadSettings(BaseModel):
    """文件上传配置"""

    MAX_FILE_SIZE: int = Field(
        default=DEFAULT_MAX_FILE_SIZE, json_schema_extra={"env": "MAX_FILE_SIZE"}
    )
    UPLOAD_DIR: str = Field(
        default="./uploads", json_schema_extra={"env": "UPLOAD_DIR"}
    )
    RENT_CONTRACT_ATTACHMENT_SUBDIR: str = Field(
        default=CONTRACT_ATTACHMENT_SUBDIR,
        json_schema_extra={"env": "RENT_CONTRACT_ATTACHMENT_SUBDIR"},
    )

    @field_validator("MAX_FILE_SIZE")
    @classmethod
    def validate_max_file_size(cls, v: int) -> int:
        """验证最大文件大小"""
        max_allowed = MAX_FILE_SIZE_LIMIT
        if v > max_allowed:
            raise PydanticCustomError(
                "max_file_size_exceeded",
                "最大文件大小不能超过 {max_mb}MB，当前值: {current_mb}MB",
                {
                    "max_mb": max_allowed / (1024 * 1024),
                    "current_mb": v / (1024 * 1024),
                },
            )
        if v < MIN_FILE_SIZE_BYTES:
            raise PydanticCustomError(
                "max_file_size_too_small",
                "最大文件大小不能小于 1KB，当前值: {value} 字节",
                {"value": v},
            )
        return v
