"""Lifecycle tests for bounded staging and atomic file promotion."""

from __future__ import annotations

import asyncio
import os
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path
from unittest.mock import AsyncMock, patch

import fitz
import pytest
from starlette.datastructures import UploadFile

from src.services.file_upload import (
    StagedFileLifecycleError,
    StagedFileService,
    UploadPurpose,
    UploadValidationError,
    get_upload_profile,
)


def _pdf_bytes() -> bytes:
    document = fitz.open()
    document.new_page()
    content = document.tobytes()
    document.close()
    return content


class TrackingUpload(UploadFile):
    def __init__(self, content: bytes, filename: str, content_type: str) -> None:
        super().__init__(
            BytesIO(content),
            filename=filename,
            headers={"content-type": content_type},
        )
        self.requested_sizes: list[int] = []

    async def read(self, size: int = -1) -> bytes:
        self.requested_sizes.append(size)
        return await super().read(size)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_invalid_filename_fails_before_read(tmp_path: Path) -> None:
    upload = TrackingUpload(_pdf_bytes(), "contract.exe.pdf", "application/pdf")
    service = StagedFileService(tmp_path)

    with pytest.raises(UploadValidationError) as exc_info:
        await service.stage_upload(upload, UploadPurpose.CONTRACT_EXTRACTION)

    assert exc_info.value.details["upload_error_code"] == "filename_invalid"
    assert upload.requested_sizes == []
    assert list(tmp_path.rglob("*")) == []


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("purpose", "filename", "mime"),
    [
        (UploadPurpose.CONTRACT_EXTRACTION, "contract.pdf", "application/pdf"),
        (
            UploadPurpose.PROPERTY_CERTIFICATE_EXTRACTION,
            "certificate.png",
            "image/png",
        ),
        (UploadPurpose.ASSET_ATTACHMENT, "asset.pdf", "application/pdf"),
        (UploadPurpose.PAYMENT_VOUCHER, "voucher.jpg", "image/jpeg"),
        (
            UploadPurpose.EXCEL_PREVIEW,
            "preview.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ),
        (
            UploadPurpose.EXCEL_IMPORT,
            "import.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ),
        (
            UploadPurpose.SYSTEM_SETTINGS_RESTORE,
            "settings.json",
            "application/json",
        ),
    ],
)
async def test_bounded_read_stops_at_profile_limit_plus_one(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    purpose: UploadPurpose,
    filename: str,
    mime: str,
) -> None:
    profile = replace(get_upload_profile(purpose), max_bytes=16)
    monkeypatch.setattr(
        "src.services.file_upload.staged_files.get_upload_profile",
        lambda _purpose: profile,
    )
    upload = TrackingUpload(b"x" * 64, filename, mime)
    service = StagedFileService(tmp_path, read_chunk_size=8)

    with pytest.raises(UploadValidationError) as exc_info:
        await service.stage_upload(upload, purpose)

    assert exc_info.value.details["upload_error_code"] == "file_too_large"
    assert sum(upload.requested_sizes) == 17
    assert max(upload.requested_sizes) <= 8
    assert not (tmp_path / ".staging").exists()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_success_generates_hash_mime_and_untrusted_path_independently(
    tmp_path: Path,
) -> None:
    content = _pdf_bytes()
    upload = TrackingUpload(content, "lease.pdf", "application/pdf")
    service = StagedFileService(tmp_path)

    staged = await service.stage_upload(upload, UploadPurpose.CONTRACT_EXTRACTION)

    assert staged.original_filename == "lease.pdf"
    assert staged.canonical_mime == "application/pdf"
    assert len(staged.sha256) == 64
    assert staged.storage_key.startswith(".staging/")
    assert "lease" not in staged.storage_key
    assert staged.path.read_bytes() == content


@pytest.mark.unit
@pytest.mark.asyncio
async def test_promotion_is_atomic_server_owned_and_idempotent(tmp_path: Path) -> None:
    service = StagedFileService(tmp_path)
    staged = await service.stage_upload(
        TrackingUpload(_pdf_bytes(), "lease.pdf", "application/pdf"),
        UploadPurpose.CONTRACT_EXTRACTION,
    )

    stored = service.promote(staged, owner_type="contract", owner_id="contract-123")
    repeated = service.promote(staged, owner_type="contract", owner_id="contract-123")

    assert stored == repeated
    assert stored.storage_key.startswith("files/contract/contract-123/")
    assert stored.path.is_file()
    assert not staged.path.exists()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_named_promotion_keeps_server_selected_asset_filename(
    tmp_path: Path,
) -> None:
    service = StagedFileService(tmp_path)
    content = _pdf_bytes()
    staged = await service.stage_upload(
        TrackingUpload(content, "lease.pdf", "application/pdf"),
        UploadPurpose.ASSET_ATTACHMENT,
    )

    stored = service.promote_named(
        staged,
        owner_type="asset_attachment",
        owner_id="asset-123",
        storage_filename="lease.pdf",
    )

    assert stored.storage_key == "files/asset_attachment/asset-123/lease.pdf"
    assert stored.path.read_bytes() == content
    assert not staged.path.parent.exists()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_discard_path_removes_background_upload_stage_directory(
    tmp_path: Path,
) -> None:
    service = StagedFileService(tmp_path)
    staged = await service.stage_upload(
        TrackingUpload(_pdf_bytes(), "lease.pdf", "application/pdf"),
        UploadPurpose.CONTRACT_EXTRACTION,
    )

    service.discard_path(staged.path)

    assert not staged.path.parent.exists()
    assert not service.staging_root.exists()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_commit_failure_removes_promoted_file(tmp_path: Path) -> None:
    service = StagedFileService(tmp_path)
    staged = await service.stage_upload(
        TrackingUpload(_pdf_bytes(), "lease.pdf", "application/pdf"),
        UploadPurpose.CONTRACT_EXTRACTION,
    )

    async def fail_commit() -> None:
        raise RuntimeError("database commit failed")

    with pytest.raises(RuntimeError, match="database commit failed"):
        await service.promote_and_commit(
            staged,
            owner_type="contract",
            owner_id="contract-123",
            commit=fail_commit,
        )

    assert list((tmp_path / "files").rglob("*.pdf")) == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cleanup_failure_is_logged_and_fails_current_operation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = StagedFileService(tmp_path)
    staged = await service.stage_upload(
        TrackingUpload(_pdf_bytes(), "lease.pdf", "application/pdf"),
        UploadPurpose.CONTRACT_EXTRACTION,
    )
    stored = service.promote(staged, owner_type="contract", owner_id="contract-123")

    def fail_unlink(_path: Path, *, missing_ok: bool = False) -> None:
        raise PermissionError("locked")

    monkeypatch.setattr(Path, "unlink", fail_unlink)
    with patch(
        "src.services.file_upload.staged_files.logger.exception"
    ) as log_exception:
        with pytest.raises(StagedFileLifecycleError) as exc_info:
            service.compensate_promotion(stored)

    assert exc_info.value.details["lifecycle_error_code"] == "cleanup_failed"
    log_exception.assert_called_once_with(
        "failed to clean stored file", extra={"path": str(stored.path)}
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_expiry_sweep_is_idempotent(tmp_path: Path) -> None:
    service = StagedFileService(tmp_path)
    staged = await service.stage_upload(
        TrackingUpload(_pdf_bytes(), "lease.pdf", "application/pdf"),
        UploadPurpose.CONTRACT_EXTRACTION,
    )
    old = (datetime.now(UTC) - timedelta(hours=2)).timestamp()
    os.utime(staged.path.parent, (old, old))

    assert service.sweep_expired(ttl_seconds=3600) == 1
    assert service.sweep_expired(ttl_seconds=3600) == 0
    assert not staged.path.exists()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cancelled_read_discards_partial_stage(tmp_path: Path) -> None:
    upload = TrackingUpload(_pdf_bytes(), "lease.pdf", "application/pdf")
    upload.read = AsyncMock(side_effect=asyncio.CancelledError())
    service = StagedFileService(tmp_path)

    with pytest.raises(asyncio.CancelledError):
        await service.stage_upload(upload, UploadPurpose.CONTRACT_EXTRACTION)

    assert list(tmp_path.rglob("*")) == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_promotion_cleanup_failure_removes_moved_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = StagedFileService(tmp_path)
    staged = await service.stage_upload(
        TrackingUpload(_pdf_bytes(), "lease.pdf", "application/pdf"),
        UploadPurpose.CONTRACT_EXTRACTION,
    )

    def fail_stage_cleanup(_path: Path) -> None:
        raise StagedFileLifecycleError("cleanup_failed", "stage directory is locked")

    monkeypatch.setattr(service, "_remove_stage_directory", fail_stage_cleanup)

    with pytest.raises(StagedFileLifecycleError, match="stage directory is locked"):
        service.promote(staged, owner_type="contract", owner_id="contract-123")

    assert list((tmp_path / "files").rglob("*.pdf")) == []
