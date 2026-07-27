"""Bounded staging, atomic promotion, and fail-loud cleanup."""

from __future__ import annotations

import hashlib
import logging
import os
import re
import shutil
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import status
from starlette.datastructures import UploadFile

from src.core.exception_handler import BaseBusinessError

from .profiles import UploadPurpose, get_upload_profile
from .validation import (
    UploadValidationError,
    validate_staged_file,
    validate_upload_filename,
)

logger = logging.getLogger(__name__)
_SAFE_STORAGE_SEGMENT = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


class StagedFileLifecycleError(BaseBusinessError):
    def __init__(
        self, error_code: str, message: str, *, path: Path | None = None
    ) -> None:
        super().__init__(
            message,
            code="STAGED_FILE_LIFECYCLE_ERROR",
            details={"lifecycle_error_code": error_code},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@dataclass(frozen=True)
class StagedFile:
    stage_id: str
    purpose: UploadPurpose
    original_filename: str
    canonical_extension: str
    canonical_mime: str
    size_bytes: int
    sha256: str
    storage_key: str
    path: Path
    created_at: datetime


@dataclass(frozen=True)
class StoredFile:
    stage_id: str
    purpose: UploadPurpose
    original_filename: str
    canonical_extension: str
    canonical_mime: str
    size_bytes: int
    sha256: str
    storage_key: str
    path: Path


class StagedFileService:
    def __init__(
        self, storage_root: Path, *, read_chunk_size: int = 1024 * 1024
    ) -> None:
        if read_chunk_size <= 0:
            raise ValueError("read_chunk_size must be positive")
        self.storage_root = storage_root.resolve()
        self.staging_root = self.storage_root / ".staging"
        self.final_root = self.storage_root / "files"
        self.read_chunk_size = read_chunk_size

    async def stage_upload(
        self, upload: UploadFile, purpose: UploadPurpose | str
    ) -> StagedFile:
        profile = get_upload_profile(purpose)
        filename = upload.filename or ""
        validate_upload_filename(filename, profile.purpose)

        stage_id = uuid.uuid4().hex
        stage_directory = self.staging_root / stage_id
        temporary_path = stage_directory / "payload.bin"
        stage_directory.mkdir(parents=True, exist_ok=False)
        digest = hashlib.sha256()
        size_bytes = 0
        try:
            await upload.seek(0)
            with temporary_path.open("xb") as destination:
                remaining = profile.max_bytes + 1
                while remaining > 0:
                    requested = min(self.read_chunk_size, remaining)
                    chunk = await upload.read(requested)
                    if not chunk:
                        break
                    destination.write(chunk)
                    digest.update(chunk)
                    size_bytes += len(chunk)
                    remaining -= len(chunk)
                    if size_bytes > profile.max_bytes:
                        raise UploadValidationError(
                            "file_too_large",
                            profile.purpose,
                            "upload exceeds its fixed size limit",
                            size_bytes=size_bytes,
                            max_bytes=profile.max_bytes,
                        )

            validated = validate_staged_file(
                purpose=profile.purpose,
                path=temporary_path,
                original_filename=filename,
                declared_mime=upload.content_type,
            )
            if (
                size_bytes != validated.size_bytes
                or digest.hexdigest() != validated.sha256
            ):
                raise StagedFileLifecycleError(
                    "staged_file_changed",
                    "staged file changed during validation",
                    path=temporary_path,
                )
            final_stage_path = stage_directory / (
                "source" + validated.canonical_extension
            )
            os.replace(temporary_path, final_stage_path)
            storage_key = final_stage_path.relative_to(self.storage_root).as_posix()
            return StagedFile(
                stage_id=stage_id,
                purpose=profile.purpose,
                original_filename=filename,
                canonical_extension=validated.canonical_extension,
                canonical_mime=validated.canonical_mime,
                size_bytes=size_bytes,
                sha256=validated.sha256,
                storage_key=storage_key,
                path=final_stage_path,
                created_at=datetime.now(UTC),
            )
        except BaseException as exc:
            try:
                self._remove_stage_directory(stage_directory)
            except StagedFileLifecycleError as cleanup_error:
                raise cleanup_error from exc
            raise

    def promote(
        self, staged: StagedFile, *, owner_type: str, owner_id: str
    ) -> StoredFile:
        self._validate_storage_segment(owner_type)
        self._validate_storage_segment(owner_id)
        storage_key = (
            Path("files")
            / owner_type
            / owner_id
            / f"{staged.stage_id}{staged.canonical_extension}"
        ).as_posix()
        return self._promote_to_storage_key(staged, storage_key)

    def promote_named(
        self,
        staged: StagedFile,
        *,
        owner_type: str,
        owner_id: str,
        storage_filename: str,
    ) -> StoredFile:
        self._validate_storage_segment(owner_type)
        self._validate_storage_segment(owner_id)
        validate_upload_filename(storage_filename, staged.purpose)
        if Path(storage_filename).suffix.lower() != staged.canonical_extension:
            raise StagedFileLifecycleError(
                "storage_filename_invalid",
                "storage filename extension does not match staged content",
            )
        storage_key = (
            Path("files") / owner_type / owner_id / storage_filename
        ).as_posix()
        return self._promote_to_storage_key(staged, storage_key)

    def _promote_to_storage_key(
        self, staged: StagedFile, storage_key: str
    ) -> StoredFile:
        destination = self._resolve_storage_key(storage_key)
        stored = StoredFile(
            stage_id=staged.stage_id,
            purpose=staged.purpose,
            original_filename=staged.original_filename,
            canonical_extension=staged.canonical_extension,
            canonical_mime=staged.canonical_mime,
            size_bytes=staged.size_bytes,
            sha256=staged.sha256,
            storage_key=storage_key,
            path=destination,
        )

        if destination.is_file():
            if not self._matches(destination, stored):
                raise StagedFileLifecycleError(
                    "destination_conflict",
                    "generated storage destination contains different content",
                    path=destination,
                )
            self._remove_stage_directory(staged.path.parent)
            return stored
        if not staged.path.is_file():
            raise StagedFileLifecycleError(
                "staged_file_missing", "staged file is missing", path=staged.path
            )

        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.replace(staged.path, destination)
        except OSError as exc:
            logger.exception(
                "failed to atomically promote staged file",
                extra={"path": str(staged.path)},
            )
            raise StagedFileLifecycleError(
                "promotion_failed",
                "failed to atomically promote staged file",
                path=staged.path,
            ) from exc
        try:
            self._remove_stage_directory(staged.path.parent)
        except StagedFileLifecycleError as cleanup_error:
            try:
                self.compensate_promotion(stored)
            except StagedFileLifecycleError as compensation_error:
                raise compensation_error from cleanup_error
            raise
        return stored

    async def promote_and_commit(
        self,
        staged: StagedFile,
        *,
        owner_type: str,
        owner_id: str,
        commit: Callable[[], Awaitable[None]],
    ) -> StoredFile:
        stored = self.promote(staged, owner_type=owner_type, owner_id=owner_id)
        try:
            await commit()
        except Exception as exc:
            try:
                self.compensate_promotion(stored)
            except StagedFileLifecycleError as cleanup_error:
                raise cleanup_error from exc
            raise
        return stored

    def discard_staged(self, staged: StagedFile) -> None:
        self._remove_stage_directory(staged.path.parent)

    def discard_path(self, path: Path) -> None:
        resolved_path = path.resolve()
        try:
            relative_path = resolved_path.relative_to(self.staging_root)
        except ValueError as exc:
            raise StagedFileLifecycleError(
                "staged_path_invalid", "staged path is outside the staging root"
            ) from exc
        if len(relative_path.parts) != 2:
            raise StagedFileLifecycleError(
                "staged_path_invalid", "staged path has an invalid structure"
            )
        stage_id = relative_path.parts[0]
        if _SAFE_STORAGE_SEGMENT.fullmatch(stage_id) is None:
            raise StagedFileLifecycleError(
                "staged_path_invalid", "staged path has an invalid stage identifier"
            )
        self._remove_stage_directory(self.staging_root / stage_id)

    def compensate_promotion(self, stored: StoredFile) -> None:
        try:
            stored.path.unlink(missing_ok=True)
            self._remove_empty_parents(stored.path.parent, self.final_root)
        except OSError as exc:
            logger.exception(
                "failed to clean stored file", extra={"path": str(stored.path)}
            )
            raise StagedFileLifecycleError(
                "cleanup_failed", "failed to clean stored file", path=stored.path
            ) from exc

    def sweep_expired(self, *, ttl_seconds: int, now: datetime | None = None) -> int:
        if not self.staging_root.exists():
            return 0
        cutoff = (now or datetime.now(UTC)) - timedelta(seconds=ttl_seconds)
        removed = 0
        for stage_directory in list(self.staging_root.iterdir()):
            if not stage_directory.is_dir():
                continue
            modified_at = datetime.fromtimestamp(
                stage_directory.stat().st_mtime, tz=UTC
            )
            if modified_at > cutoff:
                continue
            self._remove_stage_directory(stage_directory)
            removed += 1
        self._remove_empty_parents(self.staging_root, self.storage_root)
        return removed

    def _remove_stage_directory(self, stage_directory: Path) -> None:
        if not stage_directory.exists():
            return
        try:
            shutil.rmtree(stage_directory)
            self._remove_empty_parents(stage_directory.parent, self.storage_root)
        except OSError as exc:
            logger.exception(
                "failed to clean staged file", extra={"path": str(stage_directory)}
            )
            raise StagedFileLifecycleError(
                "cleanup_failed",
                "failed to clean staged file",
                path=stage_directory,
            ) from exc

    @staticmethod
    def _remove_empty_parents(path: Path, stop: Path) -> None:
        current = path
        while current != stop and current.exists():
            try:
                current.rmdir()
            except OSError:
                break
            current = current.parent

    def _resolve_storage_key(self, storage_key: str) -> Path:
        path = (self.storage_root / storage_key).resolve()
        try:
            path.relative_to(self.storage_root)
        except ValueError as exc:
            raise StagedFileLifecycleError(
                "storage_path_invalid", "generated storage path is invalid"
            ) from exc
        return path

    @staticmethod
    def _validate_storage_segment(value: str) -> None:
        if _SAFE_STORAGE_SEGMENT.fullmatch(value) is None:
            raise StagedFileLifecycleError(
                "storage_owner_invalid", "storage owner segment is invalid"
            )

    @staticmethod
    def _matches(path: Path, stored: StoredFile) -> bool:
        if path.stat().st_size != stored.size_bytes:
            return False
        digest = hashlib.sha256()
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest() == stored.sha256
