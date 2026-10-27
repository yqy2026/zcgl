"""Read-only audit response; creation belongs to business commands."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BusinessChangeEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    target_type: str
    target_id: str
    action: str
    before: dict[str, object]
    after: dict[str, object]
    reason: str | None
    actor_id: str
    occurred_at: datetime
    correlation_id: str
    summary: str
    related_objects: list[dict[str, str]]


class BusinessChangeEventListResponse(BaseModel):
    items: list[BusinessChangeEventResponse]
    total: int
    page: int
    page_size: int
