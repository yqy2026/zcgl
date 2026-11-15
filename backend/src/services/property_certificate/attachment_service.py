"""Generic attachment lifecycle for property certificates."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import UploadFile

from src.core.exception_handler import (
    BaseBusinessError,
    BusinessValidationError,
    ResourceNotFoundError,
)
from src.crud.archive_document import archive_document_repository
from src.crud.attachment import attachment_crud
from src.crud.operation_log import OperationLogCRUD
from src.crud.property_certificate import property_certificate_crud
from src.models.archive_document import ArchiveDocument
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


_Promotions = list[tuple[StagedFile, StoredFile]]


@dataclass(frozen=True)
class PropertyCertificateAttachmentDownload:
    attachment: Attachment
    path: Path


@dataclass(frozen=True)
class PropertyCertificateAttachmentVersion:
    attachment: Attachment
    document: ArchiveDocument
    is_current: bool


class PropertyCertificateAttachmentService:
    """Append immutable certificate files and archive replacement links."""

    uploads_root = Path("temp_uploads")

    async def lock_for_write(self, db: AsyncSession, certificate_id: str) -> None:
        if not await archive_document_repository.lock_certificate(
            db, certificate_id=certificate_id
        ):
            raise ResourceNotFoundError("PropertyCertificate", certificate_id)

    async def assert_content_unique(
        self, db: AsyncSession, certificate_id: str, content_hash: str
    ) -> None:
        if (
            await archive_document_repository.find_by_hash(
                db, certificate_id=certificate_id, content_hash=content_hash
            )
            is not None
        ):
            raise BaseBusinessError(
                "该产权证已归档相同内容的文件",
                code="ARCHIVE_DUPLICATE_CONTENT",
                status_code=409,
            )

    async def list(
        self, db: AsyncSession, *, certificate_id: str, include_history: bool = False
    ) -> list[PropertyCertificateAttachmentVersion]:
        await self._require_certificate(db, certificate_id)
        rows = await archive_document_repository.list_for_certificate(
            db, certificate_id=certificate_id, include_history=include_history
        )
        replaced_ids = {
            document.replaces_document_id
            for document, _ in rows
            if document.replaces_document_id is not None
        }
        result = []
        for document, attachment in rows:
            result.append(
                PropertyCertificateAttachmentVersion(
                    attachment, document, document.id not in replaced_ids
                )
            )
        return result

    async def append(
        self, db: AsyncSession, *, certificate_id: str, file: UploadFile, user_id: str
    ) -> PropertyCertificateAttachmentVersion:
        return await self._write(
            db,
            certificate_id=certificate_id,
            attachment_id=None,
            file=file,
            user_id=user_id,
        )

    async def replace(
        self,
        db: AsyncSession,
        *,
        certificate_id: str,
        attachment_id: str,
        file: UploadFile,
        user_id: str,
    ) -> PropertyCertificateAttachmentVersion:
        return await self._write(
            db,
            certificate_id=certificate_id,
            attachment_id=attachment_id,
            file=file,
            user_id=user_id,
        )

    async def _write_staged(
        self,
        db: AsyncSession,
        *,
        staged: StagedFile,
        owner_id: str,
        user_id: str,
        attachment_id: str | None = None,
        archive_target: tuple[str, str, str] | None = None,
        promotions: _Promotions | None = None,
    ) -> tuple[PropertyCertificateAttachmentVersion, StoredFile]:
        """Register one staged file as attachment + archive version without committing.

        The caller owns the transaction, the staged file and the cleanup: each
        successful promotion is appended to ``promotions`` so a later failure
        can compensate it instead of discarding the untouched staged file.
        """
        lifecycle = StagedFileService(self.uploads_root)
        if archive_target is None:
            await self.lock_for_write(db, owner_id)
        target_rows = (
            []
            if archive_target is None
            else await archive_document_repository.target_rows(
                db,
                target_type=archive_target[0],
                target_id=archive_target[1],
                document_type=archive_target[2],
            )
        )
        predecessor = None
        if attachment_id is not None:
            predecessor = (
                next((d for d, a in target_rows if a.id == attachment_id), None)
                if archive_target is not None
                else await archive_document_repository.get_for_attachment(
                    db, certificate_id=owner_id, attachment_id=attachment_id
                )
            )
            if predecessor is None:
                raise ResourceNotFoundError("ArchiveDocument", attachment_id)
            if (
                await archive_document_repository.get_successor(
                    db, document_id=predecessor.id
                )
                is not None
            ):
                raise BaseBusinessError(
                    "该文件已有后续版本，请刷新后重试",
                    code="ARCHIVE_VERSION_STALE",
                    status_code=409,
                )
        if archive_target is None:
            await self.assert_content_unique(db, owner_id, staged.sha256)
        elif any(a.file_hash == staged.sha256 for _, a in target_rows):
            raise BaseBusinessError(
                "Already archived",
                code="ARCHIVE_DUPLICATE_CONTENT",
                status_code=409,
            )
        stored = lifecycle.promote(
            staged,
            owner_type=_OWNER_TYPE if archive_target is None else "contract",
            owner_id=owner_id,
        )
        if promotions is not None:
            promotions.append((staged, stored))
        attachment = await attachment_crud.create(
            db,
            data={
                **self._attachment_data(
                    certificate_id=owner_id,
                    staged=staged,
                    stored=stored,
                    user_id=user_id,
                ),
                "owner_type": _OWNER_TYPE if archive_target is None else "contract",
            },
            commit=False,
        )
        document = (
            await archive_document_repository.register_target(
                db,
                target_type=archive_target[0],
                target_id=archive_target[1],
                document_type=archive_target[2],
                attachment=attachment,
                replaces_document_id=predecessor.id
                if predecessor is not None
                else None,
            )
            if archive_target is not None
            else await archive_document_repository.register(
                db,
                certificate_id=owner_id,
                attachment=attachment,
                replaces_document_id=predecessor.id
                if predecessor is not None
                else None,
            )
        )
        return PropertyCertificateAttachmentVersion(attachment, document, True), stored

    async def _write(
        self,
        db: AsyncSession,
        *,
        certificate_id: str,
        attachment_id: str | None,
        file: UploadFile,
        user_id: str,
        archive_target: tuple[str, str, str] | None = None,
    ) -> PropertyCertificateAttachmentVersion:
        lifecycle = StagedFileService(self.uploads_root)
        staged = await lifecycle.stage_upload(
            file, UploadPurpose.PROPERTY_CERTIFICATE_EXTRACTION
        )
        promotions: list[tuple[StagedFile, StoredFile]] = []
        try:
            result, _ = await self._write_staged(
                db,
                staged=staged,
                owner_id=certificate_id,
                user_id=user_id,
                attachment_id=attachment_id,
                archive_target=archive_target,
                promotions=promotions,
            )
            await db.commit()
            return result
        except BaseException as operation_error:
            cleanup_error: BaseException | None = None
            try:
                if promotions:
                    for _, stored in promotions:
                        lifecycle.compensate_promotion(stored)
                else:
                    lifecycle.discard_staged(staged)
            except BaseException as exc:
                cleanup_error = exc
            try:
                await db.rollback()
            except BaseException as exc:
                if cleanup_error is None:
                    cleanup_error = exc
            if cleanup_error is not None:
                raise cleanup_error from operation_error
            raise

    async def delete(
        self, db: AsyncSession, *, certificate_id: str, attachment_id: str
    ) -> None:
        await self.lock_for_write(db, certificate_id)
        document = await archive_document_repository.get_for_attachment(
            db, certificate_id=certificate_id, attachment_id=attachment_id
        )
        if document is None:
            raise ResourceNotFoundError("ArchiveDocument", attachment_id)
        raise BaseBusinessError(
            "已归档文件需保留历史，不允许删除",
            code="ARCHIVE_HISTORY_PROTECTED",
            status_code=409,
        )

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
        document = await archive_document_repository.get_for_attachment(
            db, certificate_id=certificate_id, attachment_id=attachment_id
        )
        if document is None:
            raise ResourceNotFoundError("ArchiveDocument", attachment_id)
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
