"""Public schemas for the unified temporary document-extraction session API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ExtractionFieldAction(BaseModel):
    """One explicit human decision for one extracted field."""

    model_config = ConfigDict(extra="forbid")

    field_key: str = Field(min_length=1, max_length=100)
    action: Literal[
        "accept_candidate",
        "correct_candidate",
        "manual",
        "clear_optional",
        "keep_existing",
    ]
    candidate_value: str | None = None
    value: str | None = None


class ContractPartyIds(BaseModel):
    """Existing parties selected explicitly during contract confirmation."""

    model_config = ConfigDict(extra="forbid")

    operator_party_id: str = Field(min_length=1)
    owner_party_id: str = Field(min_length=1)
    lessor_party_id: str = Field(min_length=1)
    lessee_party_id: str = Field(min_length=1)


class ExtractionSessionConfirmRequest(BaseModel):
    """Confirmation input that excludes client-controlled field provenance."""

    model_config = ConfigDict(extra="forbid")

    actions: list[ExtractionFieldAction]
    party_ids: ContractPartyIds
    asset_ids: list[str] = Field(default_factory=list)
class PropertyCertificateExtractionConfirmRequest(BaseModel):
    """Explicit review decisions for a property-certificate extraction session."""

    model_config = ConfigDict(extra="forbid")

    actions: list[ExtractionFieldAction]
    certificate_type: Literal[
        "real_estate", "house_ownership", "land_use", "other"
    ] = "other"
    holder_party_ids: list[str] = Field(default_factory=list)
    link_existing_certificate_id: str | None = Field(default=None, min_length=1)
    attach_staged: bool = True

class PropertyCertificateExistingExtractionConfirmRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    actions: list[ExtractionFieldAction]
