"""Pydantic schemas for ABAC authz endpoints and capabilities."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

AuthzAction = Literal["create", "read", "list", "update", "delete", "export"]
PerspectiveName = Literal["owner", "manager"]


class AuthzCheckRequest(BaseModel):
    """Request payload for /authz/check."""

    resource_type: str = Field(..., min_length=1, description="资源类型")
    action: AuthzAction = Field(..., description="动作")
    resource_id: str | None = Field(None, description="资源ID")
    resource: dict[str, Any] | None = Field(default=None, description="资源上下文字段")
    context: dict[str, Any] | None = Field(default=None, description="环境上下文")


class AuthzCheckResponse(BaseModel):
    """Authz decision response."""

    allowed: bool = Field(..., description="是否允许")
    reason_code: str | None = Field(default=None, description="决策原因")


class DataScope(BaseModel):
    """Data scope fragment in capabilities."""

    owner_party_ids: list[str] = Field(default_factory=list)
    manager_party_ids: list[str] = Field(default_factory=list)


class CapabilityItem(BaseModel):
    """Single resource capability."""

    resource: str
    actions: list[AuthzAction]
    perspectives: list[PerspectiveName]
    data_scope: DataScope


class CapabilitiesResponse(BaseModel):
    """Current-user capability snapshot."""

    version: str
    generated_at: datetime
    capabilities: list[CapabilityItem]

    model_config = ConfigDict(from_attributes=True)


__all__ = [
    "AuthzAction",
    "PerspectiveName",
    "AuthzCheckRequest",
    "AuthzCheckResponse",
    "DataScope",
    "CapabilityItem",
    "CapabilitiesResponse",
]
