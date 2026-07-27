"""Generic attachment lifecycle for property certificates."""

from __future__ import annotations

import json
import logging
import os
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import UploadFile

from src.core.exception_handler import BusinessValidationError, ResourceNotFoundError
from src.crud.attachment import attachment_crud
from src.crud.operation_log import OperationLogCRUD
from src.crud.property_certificate import property_certificate_crud
from src.models.attachment import Attachment
from src.models.property_certificate import PropertyCertificate
from src.services.file_upload import (
    StagedFile,
    StagedFileService,
    StoredFile,
    UploadPurpose,
)

logger = logging.getLogger(__name__)
operation_log_crud = OperationLogCRUD()
_OWNER_TYPE = "property_certificate"


@dataclass(frozen=True)
class PropertyCertificateAttachmentDownload:
    attachment: Attachment
    path: Path


class PropertyCertificateAttachmentService:
    """Manage only generic attachments owned by a property certificate."""

    uploads_root = Path("temp_uploads")

    async def list(self, db: AsyncSession, *, certificate_id: str) -> list[Attachment]:
        await self._require_certificate(db, certificate_id)
        return await attachment_crud.list_for_owner(
            db, owner_type=_OWNER_TYPE, owner_id=certificate_id
        )

    async def append(
        self,
        db: AsyncSession,
        *,
        certificate_id: str,
        file: UploadFile,
        user_id: str,
    ) -> Attachment:
        await self._require_certificate(db, certificate_id)
        lifecycle = StagedFileService(self.uploads_root)
        staged = await lifecycle.stage_upload(
            file, UploadPurpose.PROPERTY_CERTIFICATE_EXTRACTION
        )
        stored: StoredFile | None = None
        try:
            stored = lifecycle.promote(
                staged, owner_type=_OWNER_TYPE, owner_id=certificate_id
            )
            attachment = await attachment_crud.create(
                db,
                data=self._attachment_data(
                    certificate_id=certificate_id,
                    staged=staged,
                    stored=stored,
                    user_id=user_id,
                ),
                commit=False,
            )
            await db.commit()
            return attachment
        except BaseException as operation_error:
            cleanup_error: BaseException | None = None
            try:
                if stored is None:
                    lifecycle.discard_staged(staged)
                else:
                    lifecycle.compensate_promotion(stored)
            except BaseException as exc:
                cleanup_error = exc
            try:
                await db.rollback()
            except BaseException as rollback_error:
                if cleanup_error is None:
                    cleanup_error = rollback_error
            if cleanup_error is not None:
                raise cleanup_error from operation_error
            raise

    async def replace(
        self,
        db: AsyncSession,
        *,
        certificate_id: str,
        attachment_id: str,
        file: UploadFile,
        user_id: str,
    ) -> Attachment:
        await self._require_certificate(db, certificate_id)
        old = await self._require_attachment(db, certificate_id, attachment_id)
        lifecycle = StagedFileService(self.uploads_root)
        staged = await lifecycle.stage_upload(
            file, UploadPurpose.PROPERTY_CERTIFICATE_EXTRACTION
        )
        stored: StoredFile | None = None
        backup: Path | None = None
        committed = False
        try:
            stored = lifecycle.promote(
                staged, owner_type=_OWNER_TYPE, owner_id=certificate_id
            )
            backup = self._move_to_quarantine(self._resolve_path(old.storage_key))
            removed = await attachment_crud.delete_for_owner(
                db,
                attachment_id=attachment_id,
                owner_type=_OWNER_TYPE,
                owner_id=certificate_id,
            )
            if removed is None:
                raise ResourceNotFoundError("Attachment", attachment_id)
            replacement = await attachment_crud.create(
                db,
                data=self._attachment_data(
                    certificate_id=certificate_id,
                    staged=staged,
                    stored=stored,
                    user_id=user_id,
                ),
                commit=False,
            )
            await db.commit()
            committed = True
            self._discard_quarantine(backup)
            return replacement
        except BaseException as operation_error:
            if committed:
                logger.error(
                    "property certificate attachment replacement final cleanup failed"
                )
                raise
            cleanup_error: BaseException | None = None
            try:
                if stored is None:
                    lifecycle.discard_staged(staged)
                else:
                    lifecycle.compensate_promotion(stored)
                if backup is not None:
                    self._restore_quarantine(
                        backup, self._resolve_path(old.storage_key)
                    )
            except BaseException as exc:
                cleanup_error = exc
            try:
                await db.rollback()
            except BaseException as rollback_error:
                if cleanup_error is None:
                    cleanup_error = rollback_error
            if cleanup_error is not None:
                logger.error(
                    "property certificate attachment replacement cleanup failed"
                )
                raise cleanup_error from operation_error
            raise

    async def delete(
        self,
        db: AsyncSession,
        *,
        certificate_id: str,
        attachment_id: str,
    ) -> None:
        attachments = await self.list(db, certificate_id=certificate_id)
        if len(attachments) <= 1:
            raise BusinessValidationError(
                "the final property certificate attachment cannot be deleted"
            )
        attachment = await self._require_attachment(db, certificate_id, attachment_id)
        original = self._resolve_path(attachment.storage_key)
        backup = self._move_to_quarantine(original)
        committed = False
        try:
            removed = await attachment_crud.delete_for_owner(
                db,
                attachment_id=attachment_id,
                owner_type=_OWNER_TYPE,
                owner_id=certificate_id,
            )
            if removed is None:
                raise ResourceNotFoundError("Attachment", attachment_id)
            await db.commit()
            committed = True
            self._discard_quarantine(backup)
        except BaseException as operation_error:
            if committed:
                logger.error(
                    "property certificate attachment deletion final cleanup failed"
                )
                raise
            cleanup_error: BaseException | None = None
            try:
                self._restore_quarantine(backup, original)
            except BaseException as exc:
                cleanup_error = exc
            try:
                await db.rollback()
            except BaseException as rollback_error:
                if cleanup_error is None:
                    cleanup_error = rollback_error
            if cleanup_error is not None:
                logger.error("property certificate attachment deletion cleanup failed")
                raise cleanup_error from operation_error
            raise

    async def prepare_download(
        self,
        db: AsyncSession,
        *,
        certificate_id: str,
        attachment_id: str,
        user_id: str,
    ) -> PropertyCertificateAttachmentDownload:
        await self._require_certificate(db, certificate_id)
        attachment = await self._require_attachment(db, certificate_id, attachment_id)
        path = self._resolve_path(attachment.storage_key)
        if not path.is_file():
            await self._record_download(
                db,
                user_id=user_id,
                certificate_id=certificate_id,
                attachment_id=attachment_id,
                result="not_found",
                response_status=404,
            )
            raise ResourceNotFoundError("Attachment", attachment_id)
        await self._record_download(
            db,
            user_id=user_id,
            certificate_id=certificate_id,
            attachment_id=attachment_id,
            result="success",
            response_status=200,
        )
        return PropertyCertificateAttachmentDownload(attachment=attachment, path=path)

    async def _require_certificate(
        self, db: AsyncSession, certificate_id: str
    ) -> PropertyCertificate:
        certificate = await property_certificate_crud.get(db, certificate_id)
        if certificate is None:
            raise ResourceNotFoundError("PropertyCertificate", certificate_id)
        return certificate

    async def _require_attachment(
        self, db: AsyncSession, certificate_id: str, attachment_id: str
    ) -> Attachment:
        attachment = await attachment_crud.get_for_owner(
            db,
            attachment_id=attachment_id,
            owner_type=_OWNER_TYPE,
            owner_id=certificate_id,
        )
        if attachment is None:
            raise ResourceNotFoundError("Attachment", attachment_id)
        return attachment

    @staticmethod
    def _attachment_data(
        *, certificate_id: str, staged: StagedFile, stored: StoredFile, user_id: str
    ) -> dict[str, object]:
        return {
            "owner_type": _OWNER_TYPE,
            "owner_id": certificate_id,
            "file_name": staged.original_filename,
            "file_type": staged.canonical_extension.lstrip("."),
            "file_size": staged.size_bytes,
            "file_hash": staged.sha256,
            "storage_key": stored.storage_key,
            "created_by": user_id,
        }

    def _resolve_path(self, storage_key: str) -> Path:
        root = self.uploads_root.resolve()
        path = (root / storage_key).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise BusinessValidationError("invalid attachment storage key") from exc
        return path

    def _move_to_quarantine(self, source: Path) -> Path:
        if not source.is_file():
            raise ResourceNotFoundError("Attachment", source.name)
        quarantine = (
            self.uploads_root.resolve()
            / ".staging"
            / f"delete-{uuid.uuid4().hex}"
            / "payload"
        )
        quarantine.parent.mkdir(parents=True, exist_ok=False)
        os.replace(source, quarantine)
        return quarantine

    @staticmethod
    def _restore_quarantine(backup: Path, destination: Path) -> None:
        if backup.is_file():
            destination.parent.mkdir(parents=True, exist_ok=True)
            os.replace(backup, destination)
            backup.parent.rmdir()

    @staticmethod
    def _discard_quarantine(backup: Path) -> None:
        shutil.rmtree(backup.parent)

    async def _record_download(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        certificate_id: str,
        attachment_id: str,
        result: str,
        response_status: int,
    ) -> None:
        await operation_log_crud.create_async(
            db,
            user_id=user_id,
            action="download",
            action_name="property certificate attachment download",
            module="property_certificate",
            module_name="property_certificate",
            resource_type="property_certificate_attachment",
            resource_id=certificate_id,
            response_status=response_status,
            details=json.dumps(
                {"attachment_id": attachment_id, "result": result},
                ensure_ascii=True,
            ),
        )


property_certificate_attachment_service = PropertyCertificateAttachmentService()
