"""Contract tests for purpose-specific upload validation."""

from __future__ import annotations

import json
import zipfile
from dataclasses import replace
from pathlib import Path

import fitz
import pytest
from openpyxl import Workbook
from PIL import Image

from src.services.file_upload import (
    UploadPurpose,
    UploadValidationError,
    get_upload_profile,
    validate_staged_file,
)

MIB = 1024 * 1024


def _write_pdf(path: Path, *, pages: int = 1) -> None:
    document = fitz.open()
    for _ in range(pages):
        document.new_page()
    document.save(path)
    document.close()


def _write_image(path: Path, image_format: str) -> None:
    Image.new("RGB", (8, 6), color="white").save(path, format=image_format)


def _write_xlsx(path: Path) -> None:
    workbook = Workbook()
    workbook.active["A1"] = "asset_code"
    workbook.save(path)
    workbook.close()


def _write_restore_json(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "backup_time": "2026-07-20T12:00:00",
                "backup_user": "admin",
                "system_settings": {
                    "site_name": "土地物业资产管理系统",
                    "site_description": "test",
                    "allow_registration": False,
                    "session_timeout": 120,
                    "password_policy": {
                        "min_length": 8,
                        "require_uppercase": True,
                        "require_lowercase": True,
                        "require_numbers": True,
                        "require_special_chars": False,
                    },
                },
                "backup_type": "full",
                "version": "2.0.0",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


@pytest.mark.unit
def test_upload_profiles_are_fixed_by_business_purpose() -> None:
    expected = {
        UploadPurpose.CONTRACT_EXTRACTION: (50 * MIB, {".pdf"}, 50, None),
        UploadPurpose.PROPERTY_CERTIFICATE_EXTRACTION: (
            20 * MIB,
            {".pdf", ".jpg", ".jpeg", ".png"},
            20,
            50_000_000,
        ),
        UploadPurpose.ASSET_ATTACHMENT: (10 * MIB, {".pdf"}, None, None),
        UploadPurpose.PAYMENT_VOUCHER: (
            20 * MIB,
            {".pdf", ".jpg", ".jpeg", ".png"},
            None,
            50_000_000,
        ),
        UploadPurpose.EXCEL_PREVIEW: (50 * MIB, {".xlsx"}, None, None),
        UploadPurpose.EXCEL_IMPORT: (100 * MIB, {".xlsx"}, None, None),
        UploadPurpose.SYSTEM_SETTINGS_RESTORE: (1 * MIB, {".json"}, None, None),
    }

    for purpose, contract in expected.items():
        profile = get_upload_profile(purpose)
        assert (
            profile.max_bytes,
            set(profile.formats),
            profile.max_pdf_pages,
            profile.max_image_pixels,
        ) == contract

    with pytest.raises(TypeError):
        get_upload_profile(UploadPurpose.ASSET_ATTACHMENT).formats[".png"] = (  # type: ignore[index]
            "image/png",
            "png",
        )


@pytest.mark.unit
@pytest.mark.parametrize(
    ("purpose", "filename", "mime", "writer", "canonical_mime"),
    [
        (
            UploadPurpose.CONTRACT_EXTRACTION,
            "contract.pdf",
            "application/pdf",
            lambda path: _write_pdf(path),
            "application/pdf",
        ),
        (
            UploadPurpose.PROPERTY_CERTIFICATE_EXTRACTION,
            "certificate.png",
            "image/png",
            lambda path: _write_image(path, "PNG"),
            "image/png",
        ),
        (
            UploadPurpose.ASSET_ATTACHMENT,
            "asset.pdf",
            "application/pdf",
            lambda path: _write_pdf(path),
            "application/pdf",
        ),
        (
            UploadPurpose.PAYMENT_VOUCHER,
            "voucher.jpeg",
            "image/jpeg",
            lambda path: _write_image(path, "JPEG"),
            "image/jpeg",
        ),
        (
            UploadPurpose.EXCEL_PREVIEW,
            "preview.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            _write_xlsx,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ),
        (
            UploadPurpose.EXCEL_IMPORT,
            "import.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            _write_xlsx,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ),
        (
            UploadPurpose.SYSTEM_SETTINGS_RESTORE,
            "settings.json",
            "application/json",
            _write_restore_json,
            "application/json",
        ),
    ],
)
def test_each_profile_accepts_its_valid_format(
    tmp_path: Path,
    purpose: UploadPurpose,
    filename: str,
    mime: str,
    writer: object,
    canonical_mime: str,
) -> None:
    path = tmp_path / filename
    writer(path)  # type: ignore[operator]

    result = validate_staged_file(
        purpose=purpose,
        path=path,
        original_filename=filename,
        declared_mime=mime,
    )

    assert result.canonical_mime == canonical_mime
    assert result.size_bytes == path.stat().st_size
    assert len(result.sha256) == 64


@pytest.mark.unit
@pytest.mark.parametrize(
    "filename",
    ["invoice.exe.pdf", "invoice.pdf.jpg", "../invoice.pdf", r"..\invoice.pdf"],
)
def test_filename_is_rejected_before_content_is_trusted(
    tmp_path: Path, filename: str
) -> None:
    path = tmp_path / "payload.pdf"
    _write_pdf(path)

    with pytest.raises(UploadValidationError) as exc_info:
        validate_staged_file(
            purpose=UploadPurpose.CONTRACT_EXTRACTION,
            path=path,
            original_filename=filename,
            declared_mime="application/pdf",
        )

    assert exc_info.value.details["upload_error_code"] == "filename_invalid"


@pytest.mark.unit
@pytest.mark.parametrize("filename", ["lease:final.pdf", "lease?.pdf", "lease*.pdf"])
def test_filename_validation_rejects_cross_platform_invalid_characters(
    tmp_path: Path, filename: str
) -> None:
    path = tmp_path / "source.pdf"
    _write_pdf(path)

    with pytest.raises(UploadValidationError) as exc_info:
        validate_staged_file(
            purpose=UploadPurpose.CONTRACT_EXTRACTION,
            path=path,
            original_filename=filename,
            declared_mime="application/pdf",
        )

    assert exc_info.value.details["upload_error_code"] == "filename_invalid"


@pytest.mark.unit
def test_mime_mismatch_and_signature_disguise_have_stable_errors(
    tmp_path: Path,
) -> None:
    path = tmp_path / "contract.pdf"
    path.write_bytes(b"not a pdf")

    with pytest.raises(UploadValidationError) as mime_error:
        validate_staged_file(
            purpose=UploadPurpose.CONTRACT_EXTRACTION,
            path=path,
            original_filename=path.name,
            declared_mime="image/png",
        )
    assert mime_error.value.details["upload_error_code"] == "mime_mismatch"

    with pytest.raises(UploadValidationError) as signature_error:
        validate_staged_file(
            purpose=UploadPurpose.CONTRACT_EXTRACTION,
            path=path,
            original_filename=path.name,
            declared_mime="application/pdf",
        )
    assert signature_error.value.details["upload_error_code"] == "signature_mismatch"


@pytest.mark.unit
def test_contract_pdf_accepts_a_normal_24_page_document(tmp_path: Path) -> None:
    path = tmp_path / "normal-contract.pdf"
    _write_pdf(path, pages=24)

    validated = validate_staged_file(
        purpose=UploadPurpose.CONTRACT_EXTRACTION,
        path=path,
        original_filename=path.name,
        declared_mime="application/pdf",
    )

    assert validated.purpose is UploadPurpose.CONTRACT_EXTRACTION

@pytest.mark.unit
def test_pdf_rejects_encryption_page_limit_and_truncation(tmp_path: Path) -> None:
    encrypted = tmp_path / "encrypted.pdf"
    document = fitz.open()
    document.new_page()
    document.save(
        encrypted,
        encryption=fitz.PDF_ENCRYPT_AES_256,
        owner_pw="owner",
        user_pw="reader",
    )
    document.close()

    with pytest.raises(UploadValidationError) as encrypted_error:
        validate_staged_file(
            purpose=UploadPurpose.CONTRACT_EXTRACTION,
            path=encrypted,
            original_filename=encrypted.name,
            declared_mime="application/pdf",
        )
    assert encrypted_error.value.details["upload_error_code"] == "pdf_encrypted"

    too_many_pages = tmp_path / "too-many.pdf"
    _write_pdf(too_many_pages, pages=51)
    with pytest.raises(UploadValidationError) as page_error:
        validate_staged_file(
            purpose=UploadPurpose.CONTRACT_EXTRACTION,
            path=too_many_pages,
            original_filename=too_many_pages.name,
            declared_mime="application/pdf",
        )
    assert page_error.value.details["upload_error_code"] == "pdf_page_limit"

    truncated = tmp_path / "truncated.pdf"
    truncated.write_bytes(b"%PDF-1.7\n1 0 obj")
    with pytest.raises(UploadValidationError) as truncated_error:
        validate_staged_file(
            purpose=UploadPurpose.CONTRACT_EXTRACTION,
            path=truncated,
            original_filename=truncated.name,
            declared_mime="application/pdf",
        )
    assert truncated_error.value.details["upload_error_code"] == "pdf_invalid"


@pytest.mark.unit
@pytest.mark.parametrize(
    ("is_repaired", "page_count", "error_code"),
    [(True, 1, "pdf_repaired"), (False, 0, "pdf_zero_pages")],
)
def test_pdf_rejects_repaired_and_zero_page_documents(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    is_repaired: bool,
    page_count: int,
    error_code: str,
) -> None:
    class DocumentStub:
        needs_pass = False
        is_encrypted = False

        def __init__(self) -> None:
            self.is_repaired = is_repaired
            self.page_count = page_count

        def load_page(self, _page_number: int) -> object:
            return object()

        def close(self) -> None:
            return None

    path = tmp_path / "document.pdf"
    path.write_bytes(b"%PDF-1.7\n")
    monkeypatch.setattr(
        "src.services.file_upload.validation.fitz.open", lambda _path: DocumentStub()
    )

    with pytest.raises(UploadValidationError) as exc_info:
        validate_staged_file(
            purpose=UploadPurpose.CONTRACT_EXTRACTION,
            path=path,
            original_filename=path.name,
            declared_mime="application/pdf",
        )

    assert exc_info.value.details["upload_error_code"] == error_code


@pytest.mark.unit
def test_image_verify_load_and_pixel_limit_are_enforced(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    truncated = tmp_path / "truncated.png"
    truncated.write_bytes(b"\x89PNG\r\n\x1a\ntruncated")
    with pytest.raises(UploadValidationError) as invalid_error:
        validate_staged_file(
            purpose=UploadPurpose.PROPERTY_CERTIFICATE_EXTRACTION,
            path=truncated,
            original_filename=truncated.name,
            declared_mime="image/png",
        )
    assert invalid_error.value.details["upload_error_code"] == "image_invalid"

    image = tmp_path / "large.png"
    _write_image(image, "PNG")
    profile = replace(
        get_upload_profile(UploadPurpose.PROPERTY_CERTIFICATE_EXTRACTION),
        max_image_pixels=10,
    )
    monkeypatch.setattr(
        "src.services.file_upload.validation.get_upload_profile",
        lambda _purpose: profile,
    )
    with pytest.raises(UploadValidationError) as pixel_error:
        validate_staged_file(
            purpose=UploadPurpose.PROPERTY_CERTIFICATE_EXTRACTION,
            path=image,
            original_filename=image.name,
            declared_mime="image/png",
        )
    assert pixel_error.value.details["upload_error_code"] == "image_pixel_limit"


def _write_zip(path: Path, members: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in members.items():
            archive.writestr(name, content)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("members", "error_code"),
    [
        (
            {
                "../escape.xml": b"<x/>",
                "[Content_Types].xml": b"<Types/>",
                "_rels/.rels": b"<Relationships/>",
                "xl/workbook.xml": b"<workbook/>",
            },
            "xlsx_path_unsafe",
        ),
        (
            {
                "[Content_Types].xml": b"<Types/>",
                "_rels/.rels": b"<Relationships/>",
                "xl/workbook.xml": b"<workbook/>",
                "xl/vbaProject.bin": b"macro",
            },
            "xlsx_macro_forbidden",
        ),
        (
            {
                "[Content_Types].xml": b"<Types/>",
                "_rels/.rels": b"<Relationships/>",
            },
            "xlsx_required_member_missing",
        ),
        (
            {
                "[Content_Types].xml": b"<!DOCTYPE x [<!ENTITY e SYSTEM 'file:///etc/passwd'>]><Types>&e;</Types>",
                "_rels/.rels": b"<Relationships/>",
                "xl/workbook.xml": b"<workbook/>",
            },
            "xlsx_xml_unsafe",
        ),
    ],
)
def test_xlsx_rejects_unsafe_archive_shapes(
    tmp_path: Path, members: dict[str, bytes], error_code: str
) -> None:
    path = tmp_path / "unsafe.xlsx"
    _write_zip(path, members)

    with pytest.raises(UploadValidationError) as exc_info:
        validate_staged_file(
            purpose=UploadPurpose.EXCEL_IMPORT,
            path=path,
            original_filename=path.name,
            declared_mime=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
        )

    assert exc_info.value.details["upload_error_code"] == error_code


@pytest.mark.unit
def test_xlsx_rejects_compression_bombs_before_openpyxl(tmp_path: Path) -> None:
    path = tmp_path / "bomb.xlsx"
    _write_zip(
        path,
        {
            "[Content_Types].xml": b"<Types/>",
            "_rels/.rels": b"<Relationships/>",
            "xl/workbook.xml": b"<workbook/>",
            "xl/sharedStrings.xml": b"0" * (2 * MIB),
        },
    )

    with pytest.raises(UploadValidationError) as exc_info:
        validate_staged_file(
            purpose=UploadPurpose.EXCEL_PREVIEW,
            path=path,
            original_filename=path.name,
            declared_mime=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
        )

    assert exc_info.value.details["upload_error_code"] == "xlsx_resource_limit"


@pytest.mark.unit
def test_xlsx_rejects_encryption_and_duplicate_members(tmp_path: Path) -> None:
    encrypted = tmp_path / "encrypted.xlsx"
    encrypted.write_bytes(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1encrypted")
    with pytest.raises(UploadValidationError) as encrypted_error:
        validate_staged_file(
            purpose=UploadPurpose.EXCEL_IMPORT,
            path=encrypted,
            original_filename=encrypted.name,
            declared_mime=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
        )
    assert encrypted_error.value.details["upload_error_code"] == "xlsx_encrypted"

    duplicate = tmp_path / "duplicate.xlsx"
    with zipfile.ZipFile(duplicate, "w") as archive:
        archive.writestr("[Content_Types].xml", b"<Types/>")
        archive.writestr("[Content_Types].xml", b"<Types/>")
        archive.writestr("_rels/.rels", b"<Relationships/>")
        archive.writestr("xl/workbook.xml", b"<workbook/>")
    with pytest.raises(UploadValidationError) as duplicate_error:
        validate_staged_file(
            purpose=UploadPurpose.EXCEL_IMPORT,
            path=duplicate,
            original_filename=duplicate.name,
            declared_mime=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
        )
    assert duplicate_error.value.details["upload_error_code"] == (
        "xlsx_duplicate_member"
    )

    macro_declared = tmp_path / "macro-declared.xlsx"
    _write_zip(
        macro_declared,
        {
            "[Content_Types].xml": (
                b'<Types><Override ContentType="application/vnd.ms-excel.sheet.'
                b'macroEnabled.main+xml"/></Types>'
            ),
            "_rels/.rels": b"<Relationships/>",
            "xl/workbook.xml": b"<workbook/>",
        },
    )
    with pytest.raises(UploadValidationError) as macro_error:
        validate_staged_file(
            purpose=UploadPurpose.EXCEL_IMPORT,
            path=macro_declared,
            original_filename=macro_declared.name,
            declared_mime=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
        )
    assert macro_error.value.details["upload_error_code"] == "xlsx_macro_forbidden"


@pytest.mark.unit
def test_json_requires_strict_utf8_top_level_object_and_exact_schema(
    tmp_path: Path,
) -> None:
    cases = [
        (b'{"value":"\xff"}', "json_invalid_utf8"),
        (b"[]", "json_schema_invalid"),
        (b'{"version":"2.0.0"}', "json_schema_invalid"),
    ]
    for index, (content, error_code) in enumerate(cases):
        path = tmp_path / f"invalid-{index}.json"
        path.write_bytes(content)
        with pytest.raises(UploadValidationError) as exc_info:
            validate_staged_file(
                purpose=UploadPurpose.SYSTEM_SETTINGS_RESTORE,
                path=path,
                original_filename=path.name,
                declared_mime="application/json",
            )
        assert exc_info.value.details["upload_error_code"] == error_code
