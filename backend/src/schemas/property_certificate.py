"""Property certificate API schemas."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class PropertyCertificateBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    certificate_number: str = Field(description="Certificate number")
    certificate_type: str = Field(description="Certificate type")
    registration_date: date | None = None
    property_address: str | None = None
    property_type: str | None = None
    building_area: str | None = None
    floor_info: str | None = None
    land_area: str | None = None
    land_use_type: str | None = None
    land_use_term_start: date | None = None
    land_use_term_end: date | None = None
    co_ownership: str | None = None
    restrictions: str | None = None
    remarks: str | None = None


class PropertyCertificateCreate(PropertyCertificateBase):
    asset_ids: list[str] = Field(default_factory=list)
    holder_party_ids: list[str] = Field(default_factory=list)


class PropertyCertificateUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    certificate_number: str | None = None
    certificate_type: str | None = None
    registration_date: date | None = None
    property_address: str | None = None
    property_type: str | None = None
    building_area: str | None = None
    floor_info: str | None = None
    land_area: str | None = None
    land_use_type: str | None = None
    land_use_term_start: date | None = None
    land_use_term_end: date | None = None
    co_ownership: str | None = None
    restrictions: str | None = None
    remarks: str | None = None
    asset_ids: list[str] | None = None
    holder_party_ids: list[str] | None = None


class PropertyCertificateResponse(PropertyCertificateBase):
    id: str = Field(description="Certificate ID")
    asset_ids: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    created_by: str | None = None

    model_config = ConfigDict(from_attributes=True)
