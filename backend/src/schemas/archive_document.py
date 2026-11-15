"""Public archive projections never disclose storage keys or content hashes."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel


class ArchiveDocumentItem(BaseModel):
    id: str
    attachment_id: str
    document_type: Literal[
        "property_certificate",
        "supplement",
        "handover",
        "upstream_contract",
        "terminal_contract",
        "management_fee_statement",
    ] = "property_certificate"
    target_type: Literal[
        "property_certificate",
        "contract_supplement",
        "contract_lifecycle_event",
        "upstream_contract",
        "terminal_contract",
        "management_fee_statement",
    ] = "property_certificate"
    target_id: str
    file_name: str
    content_type: str
    file_size: int
    document_version: int
    replaces_document_id: str | None
    uploaded_at: datetime
    is_current: bool


class ArchiveDocumentListResponse(BaseModel):
    items: list[ArchiveDocumentItem]


class HandoverTarget(BaseModel):
    event_id: str
    event_type: Literal["terminated", "exited"]
    effective_date: date
    handover_status: str | None
    can_write: bool
    unavailable_reason: str | None


class HandoverTargets(BaseModel):
    items: list[HandoverTarget]
