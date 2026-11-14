from datetime import date

from pydantic import BaseModel


class ArchiveCategory(BaseModel):
    document_type: str
    label: str
    supported: bool = True
    required: int | None
    existing: int | None
    missing: int | None
    completion_rate: float | None


class ArchiveMissingItem(BaseModel):
    document_type: str
    target_type: str
    target_id: str
    label: str
    href: str


class ArchiveMatrixRow(BaseModel):
    unit_id: str
    unit_code: str
    unit_name: str
    categories: list[ArchiveCategory]
    missing_items: list[ArchiveMissingItem]


class ArchiveCompletion(BaseModel):
    as_of: date
    categories: list[ArchiveCategory]
    unlinked_unit_count: int


class ArchiveMatrix(BaseModel):
    as_of: date
    items: list[ArchiveMatrixRow]
    total: int
