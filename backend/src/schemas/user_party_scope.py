"""Contracts for sensitive explicit user Party-scope changes."""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..models.user_party_binding import RelationType
from .party import UserPartyBindingResponse

UserPartyBindingScopeOperation = Literal["create", "update", "close"]
UserPartyScopeSource = Literal["explicit", "organization", "unrestricted", "none"]
UserPartyScopeMode = Literal["owner", "manager", "all", "unrestricted", "none"]


class UserPartyScopeBatchUser(BaseModel):
    """Minimal target-user view for a user Party-scope batch item."""

    id: str
    username: str
    full_name: str
    account_type: Literal["human", "service", "system"]
    organization_id: str | None = None

    model_config = ConfigDict(from_attributes=True)


class UserPartyBindingScopeProposal(BaseModel):
    """The only write proposal for one explicit user Party binding."""

    operation: UserPartyBindingScopeOperation
    binding_id: str | None = Field(default=None, max_length=128)
    party_id: str | None = Field(default=None, max_length=128)
    relation_type: RelationType | None = None
    valid_from: datetime | None = None
    valid_to: datetime | None = None

    @field_validator("valid_from", "valid_to")
    @classmethod
    def normalize_datetime_to_naive_utc(cls, value: datetime | None) -> datetime | None:
        if value is None or value.tzinfo is None:
            return value
        return value.astimezone(UTC).replace(tzinfo=None)

    @field_validator("binding_id", "party_id")
    @classmethod
    def reject_blank_identifier(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if normalized == "":
            raise ValueError("identifier must not be blank")
        return normalized

    @model_validator(mode="after")
    def validate_operation_shape(self) -> "UserPartyBindingScopeProposal":
        editable_fields = {
            "party_id",
            "relation_type",
            "valid_from",
            "valid_to",
        }
        provided_fields = self.model_fields_set

        if self.operation == "create":
            if self.binding_id is not None:
                raise ValueError("create must not include binding_id")
            if self.party_id is None or self.relation_type is None:
                raise ValueError("create requires party_id and relation_type")
        elif self.operation == "update":
            if self.binding_id is None:
                raise ValueError("update requires binding_id")
            if len(editable_fields.intersection(provided_fields)) == 0:
                raise ValueError("update requires at least one editable field")
            if "party_id" in provided_fields and self.party_id is None:
                raise ValueError("party_id must not be null")
            if "relation_type" in provided_fields and self.relation_type is None:
                raise ValueError("relation_type must not be null")
            if "valid_from" in provided_fields and self.valid_from is None:
                raise ValueError("valid_from must not be null")
        else:
            if self.binding_id is None:
                raise ValueError("close requires binding_id")
            if len(editable_fields.intersection(provided_fields)) > 0:
                raise ValueError("close must not include editable binding fields")

        if (
            self.valid_from is not None
            and self.valid_to is not None
            and self.valid_to < self.valid_from
        ):
            raise ValueError("valid_to must be greater than or equal to valid_from")
        return self

    model_config = ConfigDict(extra="forbid")


class UserPartyScopeIssue(BaseModel):
    code: str
    node_type: Literal["organization", "party", "binding"]
    safe_label: str
    node_ref: str | None = None


class UserPartyScopeState(BaseModel):
    """Resolved effective scope before or after one binding proposal."""

    source: UserPartyScopeSource
    scope_mode: UserPartyScopeMode
    owner_party_ids: list[str] = Field(default_factory=list)
    manager_party_ids: list[str] = Field(default_factory=list)
    organization_id: str | None = None
    source_organization_id: str | None = None
    next_transition_at: datetime | None = None
    error_code: str | None = None
    issues: list[UserPartyScopeIssue] = Field(default_factory=list)


class UserPartyScopeView(BaseModel):
    """Read-only effective Party-scope diagnostic for one user."""

    user_id: str
    source: UserPartyScopeSource
    scope_mode: UserPartyScopeMode
    owner_party_ids: list[str] = Field(default_factory=list)
    manager_party_ids: list[str] = Field(default_factory=list)
    organization_id: str | None = None
    source_organization_id: str | None = None
    next_transition_at: datetime | None = None
    error_code: str | None = None
    issues: list[UserPartyScopeIssue] = Field(default_factory=list)


class UserPartyScopeImpact(BaseModel):
    """The scope consequences of one user's explicit binding change."""

    before_current_binding_count: int = Field(..., ge=0)
    after_current_binding_count: int = Field(..., ge=0)
    scope_changed: bool
    uses_organization_default_after: bool


class UserPartyScopePreviewResponse(BaseModel):
    user_id: str
    operation: UserPartyBindingScopeOperation
    before_scope: UserPartyScopeState
    after_scope: UserPartyScopeState
    impact: UserPartyScopeImpact
    preview_token: str
    expires_at: datetime


class UserPartyScopeCommitRequest(BaseModel):
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


class UserPartyScopeCommitResponse(BaseModel):
    binding: UserPartyBindingResponse
    operation: UserPartyBindingScopeOperation
    before_scope: UserPartyScopeState
    after_scope: UserPartyScopeState
    impact: UserPartyScopeImpact
    committed_at: datetime
    idempotent: bool = False


class UserPartyScopeBatchProposal(UserPartyBindingScopeProposal):
    """One explicit user Party-binding proposal inside a batch."""

    user_id: str = Field(..., min_length=1, max_length=128)

    @field_validator("user_id")
    @classmethod
    def normalize_user_id(cls, value: str) -> str:
        normalized = value.strip()
        if normalized == "":
            raise ValueError("user_id must not be blank")
        return normalized


class UserPartyScopeBatchImpact(BaseModel):
    """Aggregate consequences of one user Party-binding batch."""

    user_count: int = Field(..., ge=0)
    binding_change_count: int = Field(..., ge=0)
    scope_change_count: int = Field(..., ge=0)
    uses_organization_default_after_count: int = Field(..., ge=0)


class UserPartyScopeBatchPreviewRequest(BaseModel):
    items: list[UserPartyScopeBatchProposal] = Field(..., min_length=2, max_length=100)

    @model_validator(mode="after")
    def reject_duplicate_users(self) -> "UserPartyScopeBatchPreviewRequest":
        user_ids = [item.user_id for item in self.items]
        if len(set(user_ids)) != len(user_ids):
            raise ValueError("user_id must be unique within a batch")
        return self

    model_config = ConfigDict(extra="forbid")


class UserPartyScopeBatchPreviewItem(BaseModel):
    user: UserPartyScopeBatchUser
    operation: UserPartyBindingScopeOperation
    before_scope: UserPartyScopeState
    after_scope: UserPartyScopeState
    impact: UserPartyScopeImpact


class UserPartyScopeBatchPreviewResponse(BaseModel):
    items: list[UserPartyScopeBatchPreviewItem]
    impact: UserPartyScopeBatchImpact
    preview_token: str
    expires_at: datetime


class UserPartyScopeBatchCommitRequest(BaseModel):
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


class UserPartyScopeBatchCommitResponse(BaseModel):
    items: list[UserPartyScopeBatchPreviewItem]
    impact: UserPartyScopeBatchImpact
    committed_at: datetime
    idempotent: bool = False


__all__ = [
    "UserPartyScopeBatchCommitRequest",
    "UserPartyScopeBatchCommitResponse",
    "UserPartyScopeBatchImpact",
    "UserPartyScopeBatchPreviewItem",
    "UserPartyScopeBatchPreviewRequest",
    "UserPartyScopeBatchPreviewResponse",
    "UserPartyScopeBatchProposal",
    "UserPartyScopeBatchUser",
    "UserPartyBindingScopeOperation",
    "UserPartyBindingScopeProposal",
    "UserPartyScopeCommitRequest",
    "UserPartyScopeCommitResponse",
    "UserPartyScopeImpact",
    "UserPartyScopeIssue",
    "UserPartyScopePreviewResponse",
    "UserPartyScopeState",
    "UserPartyScopeView",
]
