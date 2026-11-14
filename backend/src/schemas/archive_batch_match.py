"""Batch pairing suggestions never auto-bind; commits carry explicit targets."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from .archive_document import ArchiveDocumentItem

BatchTargetType = Literal["upstream_contract", "terminal_contract"]


class BatchMatchCandidate(BaseModel):
    target_type: BatchTargetType
    target_id: str
    label: str


class BatchMatchPreviewItem(BaseModel):
    staging_id: str
    file_name: str
    file_size: int
    detected: BatchMatchCandidate | None
    ambiguous: list[BatchMatchCandidate]
    already_archived: bool


class BatchMatchPreviewResponse(BaseModel):
    preview_token: str
    expires_at: datetime
    items: list[BatchMatchPreviewItem]


class BatchMatchSelection(BaseModel):
    staging_id: str
    target_type: BatchTargetType
    target_id: str = Field(min_length=1)


class BatchMatchCommitRequest(BaseModel):
    preview_token: str
    matches: list[BatchMatchSelection] = Field(min_length=1)


class BatchMatchCommitResponse(BaseModel):
    items: list[ArchiveDocumentItem]
