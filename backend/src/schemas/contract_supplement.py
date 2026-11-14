from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SupplementCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    contract_kind: Literal["upstream", "terminal"]
    contract_id: str = Field(min_length=1)
    agreement_number: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=200)
    signed_on: date | None = None

    @field_validator("agreement_number", "title", mode="before")
    @classmethod
    def trim_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class SupplementWithdrawal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    reason: str = Field(min_length=1, max_length=1000)

    @field_validator("reason", mode="before")
    @classmethod
    def trim_reason(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class SupplementItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    contract_kind: Literal["upstream", "terminal"]
    contract_id: str
    agreement_number: str
    title: str
    signed_on: date | None
    version: int
    withdrawn_at: datetime | None


class SupplementList(BaseModel):
    items: list[SupplementItem]
