"""Property certificate schemas."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PropertyCertificateFields(BaseModel):
    """Extracted property certificate fields."""

    certificate_number: str | None = Field(default=None, description="Certificate number")
    registration_date: date | None = Field(default=None, description="Registration date")
    owner_name: str | None = Field(default=None, description="Owner name")
    owner_id_type: str | None = Field(default=None, description="Owner ID type")
    owner_id_number: str | None = Field(default=None, description="Owner ID number")
    property_address: str | None = Field(default=None, description="Property address")
    property_type: str | None = Field(default=None, description="Property type")
    building_area: str | None = Field(default=None, description="Building area")
    land_area: str | None = Field(default=None, description="Land area")
    floor_info: str | None = Field(default=None, description="Floor info")
    land_use_type: str | None = Field(default=None, description="Land use type")
    land_use_term_start: date | None = Field(default=None, description="Land use term start")
    land_use_term_end: date | None = Field(default=None, description="Land use term end")
    co_ownership: str | None = Field(default=None, description="Co-ownership")
    restrictions: str | None = Field(default=None, description="Restrictions")
    remarks: str | None = Field(default=None, description="Remarks")

    def to_dict(self) -> dict[str, Any]:
        """Convert to a dict and drop null values."""
        result = {}
        for field_name, field_value in self.model_dump().items():
            if field_value is not None:
                if isinstance(field_value, (date, Decimal)):
                    result[field_name] = str(field_value)
                else:
                    result[field_name] = field_value
        return result


PROPERTY_CERT_EXTRACTION_PROMPT = """
Extract property certificate fields as JSON.
Return null for fields that cannot be recognized. Dates must use YYYY-MM-DD.
"""


class PropertyCertificateUploadResponse(BaseModel):
    """Property certificate upload response."""

    session_id: str = Field(description="Session ID")
    asset_ids: list[str] = []
    certificate_type: str = Field(default="property_cert", description="Certificate type")
    extracted_data: dict[str, Any] = Field(default_factory=dict)
    confidence_score: float = Field(ge=0.0, le=1.0, description="Confidence score")
    asset_matches: list[dict[str, Any]] = Field(default_factory=list)
    validation_errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class CertificateImportConfirm(BaseModel):
    """Property certificate import confirmation."""

    session_id: str = Field(description="Session ID")
    asset_ids: list[str] = Field(default_factory=list)
    extracted_data: dict[str, Any] = Field(description="Extracted field data")
    asset_link_id: str | None = Field(default=None, description="Linked asset ID")
    should_create_new_asset: bool = Field(default=False)
    owners: list[dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class PropertyCertificateBase(BaseModel):
    """Base property certificate fields."""

    certificate_number: str = Field(description="Certificate number")
    certificate_type: str = Field(description="Certificate type")
    registration_date: date | None = Field(default=None)
    property_address: str | None = Field(default=None)
    property_type: str | None = Field(default=None)
    building_area: str | None = Field(default=None)
    floor_info: str | None = Field(default=None)
    land_area: str | None = Field(default=None)
    land_use_type: str | None = Field(default=None)
    land_use_term_start: date | None = Field(default=None)
    land_use_term_end: date | None = Field(default=None)
    co_ownership: str | None = Field(default=None)
    restrictions: str | None = Field(default=None)
    remarks: str | None = Field(default=None)
    organization_id: str | None = Field(default=None, description="Deprecated organization ID")


class PropertyCertificateCreate(PropertyCertificateBase):
    """Create property certificate."""

    extraction_confidence: float | None = Field(default=None)
    extraction_source: str = Field(default="manual")


class PropertyCertificateUpdate(BaseModel):
    """Update property certificate."""

    certificate_number: str | None = Field(default=None)
    certificate_type: str | None = Field(default=None)
    registration_date: date | None = Field(default=None)
    property_address: str | None = Field(default=None)
    property_type: str | None = Field(default=None)
    building_area: str | None = Field(default=None)
    floor_info: str | None = Field(default=None)
    land_area: str | None = Field(default=None)
    land_use_type: str | None = Field(default=None)
    land_use_term_start: date | None = Field(default=None)
    land_use_term_end: date | None = Field(default=None)
    co_ownership: str | None = Field(default=None)
    restrictions: str | None = Field(default=None)
    remarks: str | None = Field(default=None)
    organization_id: str | None = Field(default=None, description="Deprecated organization ID")
    extraction_confidence: float | None = Field(default=None)
    extraction_source: str | None = Field(default=None)


class PropertyCertificateResponse(PropertyCertificateBase):
    """Property certificate response."""

    id: str = Field(description="Certificate ID")
    asset_ids: list[str] = []
    owners: list["PropertyOwnerResponse"] = Field(default_factory=list)
    extraction_confidence: float | None = Field(default=None)
    extraction_source: str = Field(description="Data source")
    created_at: datetime = Field(description="Created at")
    updated_at: datetime = Field(description="Updated at")
    created_by: str | None = Field(default=None)

    model_config = ConfigDict(from_attributes=True)


class PropertyOwnerBase(BaseModel):
    """Base property owner fields."""

    owner_type: str = Field(default="individual")
    name: str = Field(description="Owner name")
    id_type: str | None = Field(default=None)
    id_number: str | None = Field(default=None)
    phone: str | None = Field(default=None)
    address: str | None = Field(default=None)
    organization_id: str | None = Field(default=None, description="Deprecated organization ID")
    asset_ids: list[str] = []


class PropertyOwnerCreate(PropertyOwnerBase):
    """Create property owner."""

    pass


class PropertyOwnerUpdate(BaseModel):
    """Update property owner."""

    owner_type: str | None = Field(default=None)
    name: str | None = Field(default=None)
    id_type: str | None = Field(default=None)
    id_number: str | None = Field(default=None)
    phone: str | None = Field(default=None)
    address: str | None = Field(default=None)
    organization_id: str | None = Field(default=None, description="Deprecated organization ID")
    asset_ids: list[str] = []


class PropertyOwnerResponse(PropertyOwnerBase):
    """Property owner response."""

    id: str = Field(description="Owner ID")
    asset_ids: list[str] = []
    created_at: datetime = Field(description="Created at")
    updated_at: datetime = Field(description="Updated at")

    model_config = ConfigDict(from_attributes=True)


PropertyCertificateResponse.model_rebuild()
