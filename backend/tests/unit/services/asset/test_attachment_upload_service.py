"""Profile-backed asset attachment upload tests."""

from io import BytesIO
from pathlib import Path

import fitz
import pytest
from starlette.datastructures import UploadFile

from src.services.asset.attachment_upload_service import AssetAttachmentUploadService
from src.services.file_upload import staged_files


def _pdf_bytes() -> bytes:
    document = fitz.open()
    document.new_page()
    content = document.tobytes()
    document.close()
    return content


def _upload(content: bytes, filename: str) -> UploadFile:
    return UploadFile(
        BytesIO(content),
        filename=filename,
        headers={"content-type": "application/pdf"},
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_upload_many_preserves_per_item_results_and_download_name(
    tmp_path: Path,
) -> None:
    service = AssetAttachmentUploadService(tmp_path)

    result = await service.upload_many(
        asset_id="asset-123",
        files=[
            _upload(_pdf_bytes(), "lease.pdf"),
            _upload(b"%PDF-1.7\nbroken", "damaged.pdf"),
        ],
    )

    assert result.success == ["lease.pdf"]
    assert len(result.failed) == 1
    assert service.resolve_path("asset-123", "lease.pdf").is_file()
    assert list((tmp_path / ".staging").rglob("*")) == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_upload_many_rejects_double_extension_without_leaving_stage(
    tmp_path: Path,
) -> None:
    service = AssetAttachmentUploadService(tmp_path)

    result = await service.upload_many(
        asset_id="asset-123",
        files=[_upload(_pdf_bytes(), "lease.exe.pdf")],
    )

    assert result.success == []
    assert len(result.failed) == 1
    assert list(tmp_path.rglob("*.pdf")) == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_upload_many_compensates_when_final_storage_move_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = AssetAttachmentUploadService(tmp_path)
    real_replace = staged_files.os.replace

    def fail_final_move(source: Path, destination: Path) -> None:
        if "files" in Path(destination).parts:
            raise OSError("storage unavailable")
        real_replace(source, destination)

    monkeypatch.setattr(staged_files.os, "replace", fail_final_move)

    result = await service.upload_many(
        asset_id="asset-123",
        files=[_upload(_pdf_bytes(), "lease.pdf")],
    )

    assert result.success == []
    assert len(result.failed) == 1
    assert list(tmp_path.rglob("*.pdf")) == []
    assert list((tmp_path / ".staging").rglob("*")) == []
