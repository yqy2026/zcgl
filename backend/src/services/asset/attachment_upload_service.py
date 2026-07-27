"""Asset attachment upload lifecycle."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from starlette.datastructures import UploadFile

from src.core.exception_handler import InvalidRequestError
from src.services.file_upload import (
    StagedFile,
    StagedFileLifecycleError,
    StagedFileService,
    UploadPurpose,
    UploadValidationError,
)
from src.utils.file_security import secure_filename

_SAFE_ASSET_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


@dataclass(frozen=True)
class AssetAttachmentUploadResult:
    success: list[str]
    failed: list[str]

    @property
    def message(self) -> str:
        if self.success and self.failed:
            return (
                f"成功上传 {len(self.success)} 个文件，失败 {len(self.failed)} 个文件"
            )
        if self.success:
            return f"成功上传 {len(self.success)} 个文件"
        return "上传失败"


class AssetAttachmentUploadService:
    def __init__(self, uploads_root: Path = Path("uploads")) -> None:
        self.uploads_root = uploads_root.resolve()
        self.lifecycle = StagedFileService(self.uploads_root)

    async def upload_many(
        self, *, asset_id: str, files: Sequence[UploadFile]
    ) -> AssetAttachmentUploadResult:
        self.resolve_directory(asset_id)
        success: list[str] = []
        failed: list[str] = []
        for upload in files:
            if not upload.filename:
                failed.append("文件名不能为空")
                continue

            staged: StagedFile | None = None
            try:
                staged = await self.lifecycle.stage_upload(
                    upload, UploadPurpose.ASSET_ATTACHMENT
                )
                stored = self.lifecycle.promote_named(
                    staged,
                    owner_type="asset_attachment",
                    owner_id=asset_id,
                    storage_filename=secure_filename(staged.original_filename),
                )
                success.append(stored.path.name)
            except UploadValidationError as exc:
                failed.append(exc.message)
            except StagedFileLifecycleError as exc:
                self._discard_if_present(staged)
                if exc.details.get("lifecycle_error_code") == "cleanup_failed":
                    raise
                failed.append(exc.message)
            except Exception as exc:
                self._discard_if_present(staged)
                failed.append(str(exc))

        return AssetAttachmentUploadResult(success=success, failed=failed)

    def resolve_directory(self, asset_id: str) -> Path:
        if _SAFE_ASSET_ID.fullmatch(asset_id) is None:
            raise InvalidRequestError("非法资产附件路径")
        return self.uploads_root / "files" / "asset_attachment" / asset_id

    def resolve_path(self, asset_id: str, filename: str) -> Path:
        if secure_filename(filename) != filename or not filename.lower().endswith(
            ".pdf"
        ):
            raise InvalidRequestError("非法文件路径")
        directory = self.resolve_directory(asset_id)
        path = (directory / filename).resolve()
        try:
            path.relative_to(directory.resolve())
        except ValueError as exc:
            raise InvalidRequestError("非法文件路径") from exc
        return path

    def _discard_if_present(self, staged: StagedFile | None) -> None:
        if staged is not None and staged.path.parent.exists():
            self.lifecycle.discard_staged(staged)


asset_attachment_upload_service = AssetAttachmentUploadService()
