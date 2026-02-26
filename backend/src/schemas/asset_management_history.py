"""Schemas for asset management-party history."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class AssetManagementHistoryBase(BaseModel):
    asset_id: str = Field(..., description="资产ID")
    manager_party_id: str = Field(..., description="经营管理方主体ID")
    start_date: date | None = Field(None, description="生效日期")
    end_date: date | None = Field(None, description="结束日期")
    agreement: str | None = Field(None, description="协议文件/编号")
    change_reason: str | None = Field(None, description="变更原因")
    changed_by: str | None = Field(None, description="变更人")


class AssetManagementHistoryCreate(AssetManagementHistoryBase):
    pass


class AssetManagementHistoryUpdate(BaseModel):
    manager_party_id: str | None = Field(None, description="经营管理方主体ID")
    start_date: date | None = Field(None, description="生效日期")
    end_date: date | None = Field(None, description="结束日期")
    agreement: str | None = Field(None, description="协议文件/编号")
    change_reason: str | None = Field(None, description="变更原因")
    changed_by: str | None = Field(None, description="变更人")


class AssetManagementHistoryResponse(AssetManagementHistoryBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
