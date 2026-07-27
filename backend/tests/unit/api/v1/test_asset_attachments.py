"""Asset attachment API delegation and download regressions."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import UploadFile

from src.core.exception_handler import InvalidRequestError, ResourceNotFoundError
from src.services.asset.attachment_upload_service import AssetAttachmentUploadResult

pytestmark = pytest.mark.api


@pytest.mark.asyncio
async def test_upload_checks_asset_before_delegating_or_reading(mock_db) -> None:
    from src.api.v1.assets.asset_attachments import upload_asset_attachments

    upload = MagicMock(spec=UploadFile)
    upload.filename = "lease.pdf"
    upload.read = AsyncMock()
    with (
        patch(
            "src.api.v1.assets.asset_attachments.asset_crud.get_async",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "src.api.v1.assets.asset_attachments.asset_attachment_upload_service.upload_many",
            new=AsyncMock(),
        ) as mock_upload_many,
    ):
        with pytest.raises(ResourceNotFoundError):
            await upload_asset_attachments(
                asset_id="asset-123",
                files=[upload],
                db=mock_db,
                current_user=SimpleNamespace(id="user-1"),
            )

    upload.read.assert_not_awaited()
    mock_upload_many.assert_not_awaited()


@pytest.mark.asyncio
async def test_upload_preserves_per_item_response_shape(mock_db) -> None:
    from src.api.v1.assets.asset_attachments import upload_asset_attachments

    result = AssetAttachmentUploadResult(success=["lease.pdf"], failed=["damaged PDF"])
    upload = MagicMock(spec=UploadFile)
    with (
        patch(
            "src.api.v1.assets.asset_attachments.asset_crud.get_async",
            new=AsyncMock(return_value=SimpleNamespace(id="asset-123")),
        ),
        patch(
            "src.api.v1.assets.asset_attachments.asset_attachment_upload_service.upload_many",
            new=AsyncMock(return_value=result),
        ) as mock_upload_many,
    ):
        response = await upload_asset_attachments(
            asset_id="asset-123",
            files=[upload],
            db=mock_db,
            current_user=SimpleNamespace(id="user-1"),
        )

    assert response == {
        "success": ["lease.pdf"],
        "failed": ["damaged PDF"],
        "message": "成功上传 1 个文件，失败 1 个文件",
    }
    assert mock_upload_many.await_args.kwargs["asset_id"] == "asset-123"


@pytest.mark.asyncio
async def test_list_attachments_filters_non_pdf_files(mock_db, tmp_path: Path) -> None:
    from src.api.v1.assets.asset_attachments import get_asset_attachments

    (tmp_path / "lease.pdf").write_bytes(b"pdf")
    (tmp_path / "notes.txt").write_text("text", encoding="utf-8")
    with (
        patch(
            "src.api.v1.assets.asset_attachments.asset_crud.get_async",
            new=AsyncMock(return_value=SimpleNamespace(id="asset-123")),
        ),
        patch(
            "src.api.v1.assets.asset_attachments.asset_attachment_upload_service.resolve_directory",
            return_value=tmp_path,
        ),
    ):
        result = await get_asset_attachments(
            asset_id="asset-123",
            db=mock_db,
            current_user=SimpleNamespace(id="user-1"),
        )

    assert [item["name"] for item in result] == ["lease.pdf"]
    assert result[0]["url"].endswith("/asset-123/attachments/lease.pdf")


@pytest.mark.asyncio
async def test_download_returns_existing_pdf(mock_db, tmp_path: Path) -> None:
    from src.api.v1.assets.asset_attachments import download_asset_attachment

    path = tmp_path / "lease.pdf"
    path.write_bytes(b"pdf")
    with (
        patch(
            "src.api.v1.assets.asset_attachments.asset_crud.get_async",
            new=AsyncMock(return_value=SimpleNamespace(id="asset-123")),
        ),
        patch(
            "src.api.v1.assets.asset_attachments._resolve_attachment_path",
            return_value=path,
        ),
    ):
        response = await download_asset_attachment(
            asset_id="asset-123",
            filename="lease.pdf",
            db=mock_db,
            current_user=SimpleNamespace(id="user-1"),
        )

    assert Path(response.path) == path
    assert response.media_type == "application/pdf"


@pytest.mark.asyncio
async def test_download_rejects_non_pdf_before_path_resolution(mock_db) -> None:
    from src.api.v1.assets.asset_attachments import download_asset_attachment

    with patch(
        "src.api.v1.assets.asset_attachments.asset_crud.get_async",
        new=AsyncMock(return_value=SimpleNamespace(id="asset-123")),
    ):
        with pytest.raises(InvalidRequestError):
            await download_asset_attachment(
                asset_id="asset-123",
                filename="notes.txt",
                db=mock_db,
                current_user=SimpleNamespace(id="user-1"),
            )


@pytest.mark.asyncio
async def test_delete_removes_resolved_attachment(mock_db, tmp_path: Path) -> None:
    from src.api.v1.assets.asset_attachments import delete_asset_attachment

    path = tmp_path / "lease.pdf"
    path.write_bytes(b"pdf")
    with (
        patch(
            "src.api.v1.assets.asset_attachments.asset_crud.get_async",
            new=AsyncMock(return_value=SimpleNamespace(id="asset-123")),
        ),
        patch(
            "src.api.v1.assets.asset_attachments._resolve_attachment_path",
            return_value=path,
        ),
    ):
        response = await delete_asset_attachment(
            asset_id="asset-123",
            attachment_id="lease.pdf",
            db=mock_db,
            current_user=SimpleNamespace(id="user-1"),
        )

    assert response == {"message": "附件删除成功"}
    assert not path.exists()
