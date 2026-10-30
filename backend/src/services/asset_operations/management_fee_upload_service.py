"""Stage a validated stamped file and bind its metadata in one DB transaction."""

from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import UploadFile

from ...crud.attachment import attachment_crud
from ...schemas.management_fee_commands import (
    ManagementFeeStampRequest,
    ManagementFeeStampResponse,
)
from ..file_upload import StagedFile, StagedFileService, StoredFile, UploadPurpose
from ..party_scope_resolver import EffectivePartyScope
from .management_fee_query_service import management_fee_query_service
from .management_fee_stamp_service import management_fee_stamp_service
from .rent_command_support import check_version, require_scope
from .rent_errors import rent_error


class ManagementFeeUploadService:
    def __init__(self, *, uploads_root: Path = Path("temp_uploads")):
        self.uploads_root = uploads_root

    async def upload(
        self,
        db: AsyncSession,
        *,
        statement_id: str,
        file: UploadFile,
        expected_version: int,
        actor_id: str,
        scope: EffectivePartyScope,
    ) -> ManagementFeeStampResponse:
        require_scope(scope, actor_id)
        lifecycle = StagedFileService(self.uploads_root)
        staged: StagedFile | None = None
        stored: StoredFile | None = None
        try:
            detail = await management_fee_query_service.detail(
                db, statement_id=statement_id, scope=scope
            )
            if detail.statement.status is not None:
                raise rent_error(
                    "MANAGEMENT_FEE_STATEMENT_LOCKED", "已确认或已更正的对账单不可修改"
                )
            check_version(statement_id, detail.statement.version, expected_version)
            staged = await lifecycle.stage_upload(
                file, UploadPurpose.MANAGEMENT_FEE_STAMP
            )
            stored = lifecycle.promote(
                staged, owner_type="management_fee_statement", owner_id=statement_id
            )
            attachment = await attachment_crud.create(
                db,
                data={
                    "owner_type": "management_fee_statement",
                    "owner_id": statement_id,
                    "file_name": staged.original_filename,
                    "file_type": staged.canonical_extension.lstrip("."),
                    "file_size": staged.size_bytes,
                    "file_hash": staged.sha256,
                    "storage_key": stored.storage_key,
                    "created_by": actor_id,
                },
                commit=False,
            )
            # Binding rechecks permission/version under owner+statement locks and
            # commits metadata, pointer and audit together. No cleanup follows
            # a successful commit; replaced attachments remain historical facts.
            return await management_fee_stamp_service.bind_document(
                db,
                statement_id=statement_id,
                request=ManagementFeeStampRequest(
                    document_id=attachment.id, expected_version=expected_version
                ),
                actor_id=actor_id,
                scope=scope,
            )
        except BaseException as operation_error:
            cleanup_error: BaseException | None = None
            try:
                if stored is not None:
                    lifecycle.compensate_promotion(stored)
                elif staged is not None:
                    lifecycle.discard_staged(staged)
            except BaseException as error:
                cleanup_error = error
            try:
                await db.rollback()
            except BaseException as rollback_error:
                if cleanup_error is None:
                    cleanup_error = rollback_error
            if cleanup_error is not None:
                raise cleanup_error from operation_error
            raise


management_fee_upload_service = ManagementFeeUploadService()
