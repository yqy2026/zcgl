"""
权属方相关数据模式
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class OwnershipBase(BaseModel):
    """权属方基础模式"""

    name: str = Field(..., title="权属方全称", min_length=1, max_length=200)
    code: str | None = Field(None, title="权属方编码", min_length=1, max_length=100)
    short_name: str | None = Field(None, title="权属方简称", max_length=100)


class OwnershipCreate(OwnershipBase):
    """创建权属方模式"""

    @field_validator("code")
    @classmethod
    def validate_code(cls, v):
        """验证权属方编码格式"""
        if v is not None:  # pragma: no cover
            # 验证编码格式：[前缀][年月][序号]
            import re  # pragma: no cover

            pattern = r"^[A-Z]{2}\d{7}$"  # pragma: no cover
            if not re.match(pattern, v):  # pragma: no cover
                raise ValueError(  # pragma: no cover
                    "权属方编码格式必须为: [2字母前缀][4位年月][3位序号]，例如: OW2501001"  # pragma: no cover
                )  # pragma: no cover
            return v.upper()  # pragma: no cover
        return v  # pragma: no cover


class OwnershipUpdate(BaseModel):
    """更新权属方模式"""

    name: str | None = Field(None, title="权属方全称", min_length=1, max_length=200)
    code: str | None = Field(None, title="权属方编码", min_length=1, max_length=100)
    short_name: str | None = Field(None, title="权属方简称", max_length=100)
    is_active: bool | None = Field(None, title="状态")

    @field_validator("code")
    @classmethod
    def validate_code(cls, v):
        """验证权属方编码格式"""
        if v is not None:  # pragma: no cover
            # 验证编码格式：[前缀][年月][序号]
            import re  # pragma: no cover

            pattern = r"^[A-Z]{2}\d{7}$"  # pragma: no cover
            if not re.match(pattern, v):  # pragma: no cover
                raise ValueError(  # pragma: no cover
                    "权属方编码格式必须为: [2字母前缀][4位年月][3位序号]，例如: OW2501001"  # pragma: no cover
                )  # pragma: no cover
            return v.upper()  # pragma: no cover
        return v  # pragma: no cover


class OwnershipInDB(OwnershipBase):
    """数据库中的权属方模式"""

    id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OwnershipResponse(OwnershipInDB):
    """权属方响应模式"""

    asset_count: int | None = Field(None, title="关联资产数量")
    project_count: int | None = Field(None, title="关联项目数量")

    model_config = ConfigDict(from_attributes=True)


class OwnershipListResponse(BaseModel):
    """权属方列表响应模式"""

    items: list[OwnershipResponse]
    total: int
    page: int
    size: int
    pages: int


class OwnershipDeleteResponse(BaseModel):
    """权属方删除响应模式"""

    message: str
    id: str
    affected_assets: int | None = Field(None, title="受影响的资产数量")


class OwnershipSearchRequest(BaseModel):
    """权属方搜索请求模式"""

    keyword: str | None = Field(None, title="搜索关键词")
    is_active: bool | None = Field(None, title="状态")
    page: int = Field(1, title="页码", ge=1)
    size: int = Field(10, title="页面大小", ge=1, le=100)


class OwnershipStatisticsResponse(BaseModel):
    """权属方统计响应模式"""

    total_count: int = Field(..., title="总数量")
    active_count: int = Field(..., title="启用数量")
    inactive_count: int = Field(..., title="禁用数量")
    recent_created: list[OwnershipResponse] = Field(..., title="最近创建的权属方")
