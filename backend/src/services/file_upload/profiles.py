"""Immutable upload contracts selected by business purpose."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final

from src.constants.document_processing_constants import (
    CONTRACT_MAX_PDF_PAGES,
    PROPERTY_CERTIFICATE_MAX_PDF_PAGES,
)

MIB: Final[int] = 1024 * 1024
XLSX_MIME: Final[str] = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


class UploadPurpose(StrEnum):
    CONTRACT_EXTRACTION = "contract_extraction"
    PROPERTY_CERTIFICATE_EXTRACTION = "property_certificate_extraction"
    ASSET_ATTACHMENT = "asset_attachment"
    PAYMENT_VOUCHER = "payment_voucher"
    EXCEL_PREVIEW = "excel_preview"
    EXCEL_IMPORT = "excel_import"
    SYSTEM_SETTINGS_RESTORE = "system_settings_restore"


@dataclass(frozen=True)
class UploadFormat:
    canonical_mime: str
    parser: str
    signatures: tuple[bytes, ...]


@dataclass(frozen=True)
class XlsxResourceLimits:
    max_members: int = 2_048
    max_member_bytes: int = 64 * MIB
    max_total_uncompressed_bytes: int = 256 * MIB
    max_compression_ratio: int = 100


@dataclass(frozen=True)
class UploadProfile:
    purpose: UploadPurpose
    max_bytes: int
    formats: Mapping[str, UploadFormat]
    max_pdf_pages: int | None = None
    max_image_pixels: int | None = None
    xlsx_limits: XlsxResourceLimits | None = None


PDF = UploadFormat("application/pdf", "pdf", (b"%PDF-",))
JPEG = UploadFormat("image/jpeg", "image", (b"\xff\xd8\xff",))
PNG = UploadFormat("image/png", "image", (b"\x89PNG\r\n\x1a\n",))
XLSX = UploadFormat(XLSX_MIME, "xlsx", (b"PK\x03\x04",))
JSON = UploadFormat("application/json", "json", (b"{", b"["))
XLSX_LIMITS = XlsxResourceLimits()


def _formats(**formats: UploadFormat) -> Mapping[str, UploadFormat]:
    return MappingProxyType(
        {f".{extension}": value for extension, value in formats.items()}
    )


UPLOAD_PROFILES: Final[Mapping[UploadPurpose, UploadProfile]] = MappingProxyType(
    {
        UploadPurpose.CONTRACT_EXTRACTION: UploadProfile(
            UploadPurpose.CONTRACT_EXTRACTION,
            50 * MIB,
            _formats(pdf=PDF),
            max_pdf_pages=CONTRACT_MAX_PDF_PAGES,
        ),
        UploadPurpose.PROPERTY_CERTIFICATE_EXTRACTION: UploadProfile(
            UploadPurpose.PROPERTY_CERTIFICATE_EXTRACTION,
            20 * MIB,
            _formats(pdf=PDF, jpg=JPEG, jpeg=JPEG, png=PNG),
            max_pdf_pages=PROPERTY_CERTIFICATE_MAX_PDF_PAGES,
            max_image_pixels=50_000_000,
        ),
        UploadPurpose.ASSET_ATTACHMENT: UploadProfile(
            UploadPurpose.ASSET_ATTACHMENT,
            10 * MIB,
            _formats(pdf=PDF),
        ),
        UploadPurpose.PAYMENT_VOUCHER: UploadProfile(
            UploadPurpose.PAYMENT_VOUCHER,
            20 * MIB,
            _formats(pdf=PDF, jpg=JPEG, jpeg=JPEG, png=PNG),
            max_image_pixels=50_000_000,
        ),
        UploadPurpose.EXCEL_PREVIEW: UploadProfile(
            UploadPurpose.EXCEL_PREVIEW,
            50 * MIB,
            _formats(xlsx=XLSX),
            xlsx_limits=XLSX_LIMITS,
        ),
        UploadPurpose.EXCEL_IMPORT: UploadProfile(
            UploadPurpose.EXCEL_IMPORT,
            100 * MIB,
            _formats(xlsx=XLSX),
            xlsx_limits=XLSX_LIMITS,
        ),
        UploadPurpose.SYSTEM_SETTINGS_RESTORE: UploadProfile(
            UploadPurpose.SYSTEM_SETTINGS_RESTORE,
            1 * MIB,
            _formats(json=JSON),
        ),
    }
)


def get_upload_profile(purpose: UploadPurpose | str) -> UploadProfile:
    return UPLOAD_PROFILES[UploadPurpose(purpose)]
