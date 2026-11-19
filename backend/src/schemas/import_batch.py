"""Pydantic schemas for the three-sheet import batch API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ImportBatchChangeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    sheet_name: str
    row_number: int
    target_type: Literal["asset_unit", "upstream_contract", "terminal_contract"]
    target_key: str
    field_name: str
    old_value: dict[str, Any] | None = None
    new_value: dict[str, Any] | None = None
    selected: bool
    severity: Literal["change", "warning", "error"]
    effect_summary: str


class ImportBatchChangePage(BaseModel):
    items: list[ImportBatchChangeResponse]
    total: int


class ImportBatchListResponse(BaseModel):
    """Recent import batches for the side panel (both modes mixed)."""

    items: list[ImportBatchStatusResponse]
    total: int


class ImportBatchStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    mode: Literal["create", "update"]
    status: Literal[
        "uploaded",
        "validating",
        "invalid",
        "ready",
        "committed",
        "reverted",
    ]
    template_version: str
    row_count: int
    valid_count: int
    error_count: int
    warning_count: int
    proposal_hash: str | None
    version: int
    committed_at: str | None = None
    reverted_at: str | None = None


class ImportSelectionRequest(BaseModel):
    selections: dict[str, bool] = Field(..., min_length=1)


class ImportCommitPreviewResponse(BaseModel):
    batch_id: str
    change_count: int
    warning_count: int
    proposal_hash: str
    commit_token: str
    expires_at: str


class ImportCommitRequest(BaseModel):
    commit_token: str = Field(..., min_length=1)
    expected_version: int = Field(..., ge=1)
    proposal_hash: str = Field(..., min_length=1)
    idempotency_key: str = Field(..., min_length=1, max_length=100)


class ImportCommitResponse(BaseModel):
    batch_id: str
    status: str
    idempotent: bool
    committed_at: str | None = None


class ImportRevertPreviewResponse(BaseModel):
    batch_id: str
    deadline: str
    blockers: list[dict[str, str]]
    revert_token: str


class ImportRevertRequest(BaseModel):
    revert_token: str = Field(..., min_length=1)
    reason: str = Field(..., min_length=1, max_length=1000)
    idempotency_key: str = Field(..., min_length=1, max_length=100)


class ImportRevertResponse(BaseModel):
    batch_id: str
    status: str
    idempotent: bool


class ImportStagedFile(BaseModel):
    id: str
    file_name: str
    file_size: int


class ImportStagingResponse(BaseModel):
    files: list[ImportStagedFile]
