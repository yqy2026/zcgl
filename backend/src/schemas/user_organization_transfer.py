"""Contracts for sensitive human-user organization transfers."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .user_party_scope import UserPartyScopeState


class UserOrganizationTransferProposal(BaseModel):
    """The only proposal that can change a human user's organization."""

    organization_id: str = Field(..., min_length=1, max_length=128)

    @field_validator("organization_id")
    @classmethod
    def reject_blank_organization_id(cls, value: str) -> str:
        normalized = value.strip()
        if normalized == "":
            raise ValueError("organization_id must not be blank")
        return normalized

    model_config = ConfigDict(extra="forbid")


class UserOrganizationTransferImpact(BaseModel):
    """Observable consequences of a proposed organization transfer."""

    organization_changed: bool
    scope_changed: bool
    current_explicit_binding_count: int = Field(..., ge=0)
    uses_explicit_party_scope_after: bool
    cache_invalidation_required: bool = True


class UserOrganizationTransferPreviewResponse(BaseModel):
    user_id: str
    before_scope: UserPartyScopeState
    after_scope: UserPartyScopeState
    impact: UserOrganizationTransferImpact
    preview_token: str
    expires_at: datetime


class UserOrganizationTransferCommitRequest(BaseModel):
    preview_token: str = Field(..., min_length=1, max_length=512)
    reason: str = Field(..., min_length=1, max_length=500)
    idempotency_key: str = Field(..., min_length=1, max_length=128)

    @field_validator("preview_token", "reason", "idempotency_key")
    @classmethod
    def reject_blank_value(cls, value: str) -> str:
        normalized = value.strip()
        if normalized == "":
            raise ValueError("value must not be blank")
        return normalized

    model_config = ConfigDict(extra="forbid")


class UserOrganizationTransferCommitResponse(BaseModel):
    user_id: str
    organization_id: str
    before_scope: UserPartyScopeState
    after_scope: UserPartyScopeState
    impact: UserOrganizationTransferImpact
    committed_at: datetime
    idempotent: bool = False


__all__ = [
    "UserOrganizationTransferCommitRequest",
    "UserOrganizationTransferCommitResponse",
    "UserOrganizationTransferImpact",
    "UserOrganizationTransferPreviewResponse",
    "UserOrganizationTransferProposal",
]
