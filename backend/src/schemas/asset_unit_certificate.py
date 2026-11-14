"""Registered certificate facts and temporal links for a visible asset unit."""

from datetime import date

from pydantic import BaseModel, ConfigDict


class AssetUnitCertificateItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    certificate_number: str
    certificate_type: str
    property_address: str | None
    registration_date: date | None
    # Certificate areas are registered text, not calculable unit area facts.
    building_area: str | None
    land_area: str | None
    land_use_term_start: date | None
    land_use_term_end: date | None


class AssetUnitCertificateListResponse(BaseModel):
    items: list[AssetUnitCertificateItem]


class AssetUnitCertificateLinkCreate(BaseModel):
    certificate_id: str
    effective_from: date
    effective_to: date | None = None


class AssetUnitCertificateUnlink(BaseModel):
    """解绑生效日：该日起不再关联，覆盖区间截止到前一日。"""

    effective_from: date


class AssetUnitCertificateOptionsResponse(BaseModel):
    items: list[AssetUnitCertificateItem]
    total: int
