"""Shared rent obligation preview impact."""

from pydantic import BaseModel, Field


class RentObligationImpact(BaseModel):
    created_count: int = 0
    updated_count: int = 0
    voided_count: int = 0
    restored_count: int = 0
    mismatched_entry_ids: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
