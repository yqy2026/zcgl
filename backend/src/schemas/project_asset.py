"""Schemas for project-assets bindings."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProjectAssetBindRequest(BaseModel):
    project_id: str = Field(..., description="项目ID")
    asset_id: str = Field(..., description="资产ID")
    valid_from: datetime | None = Field(None, description="生效时间")
    bind_reason: str | None = Field(None, description="绑定原因")


class ProjectAssetUnbindRequest(BaseModel):
    valid_to: datetime | None = Field(None, description="失效时间")
    unbind_reason: str | None = Field(None, description="解绑原因")


class ProjectAssetResponse(BaseModel):
    id: str
    project_id: str
    asset_id: str
    valid_from: datetime
    valid_to: datetime | None = None
    bind_reason: str | None = None
    unbind_reason: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
