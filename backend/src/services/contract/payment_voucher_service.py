"""Payment-flow voucher storage and download audit service."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import UploadFile

from src.core.exception_handler import (
    BusinessValidationError,
    InvalidRequestError,
    ResourceNotFoundError,
)
from src.crud.attachment import attachment_crud
from src.crud.operation_log import OperationLogCRUD
from src.crud.query_builder import PartyFilter
from src.models.attachment import Attachment
from src.services.contract.payment_flow_service import payment_flow_service
from src.services.file_upload import StagedFileService, StoredFile, UploadPurpose

operation_log_crud = OperationLogCRUD()


@dataclass(frozen=True)
class VoucherDownload:
    attachment: Attachment
    path: Path


class PaymentVoucherService:
    """Authorize voucher access and make every download queryable."""

    uploads_root = Path("uploads")

    async def upload_voucher(
        self,
        db: AsyncSession,
        *,
        flow_id: str,
        file: UploadFile,
        user_id: str,
        party_filter: PartyFilter | None = None,
    ) -> Attachment:
        flow = await payment_flow_service.get_flow_in_scope(
            db,
            flow_id=flow_id,
            current_user_id=user_id,
            party_filter=party_filter,
            for_update=True,
        )
        status = str(getattr(getattr(flow, "status", None), "value", flow.status))
        if status != "active":
            raise BusinessValidationError(
                "only active payment flows can receive voucher attachments"
            )

        lifecycle = StagedFileService(self.uploads_root)
        staged = await lifecycle.stage_upload(file, UploadPurpose.PAYMENT_VOUCHER)
        attachment_id = str(uuid.uuid4())
        stored: StoredFile | None = None
        previous_attachment_ids = [
            str(value) for value in flow.voucher_attachment_ids or []
        ]
        try:
            stored = lifecycle.promote(
                staged,
                owner_type="payment_flow",
                owner_id=flow_id,
            )
            attachment = await attachment_crud.create(
                db,
                data={
                    "id": attachment_id,
                    "owner_type": "payment_flow",
                    "owner_id": flow_id,
                    "file_name": staged.original_filename,
                    "file_type": staged.canonical_extension.lstrip("."),
                    "file_size": staged.size_bytes,
                    "file_hash": staged.sha256,
                    "storage_key": stored.storage_key,
                    "created_by": user_id,
                },
                commit=False,
            )
            flow.voucher_attachment_ids = [
                *previous_attachment_ids,
                attachment_id,
            ]
            flow.updated_at = datetime.now(UTC).replace(tzinfo=None)
            await db.flush()
            await db.commit()
            return attachment
        except BaseException as operation_error:
            flow.voucher_attachment_ids = previous_attachment_ids
            cleanup_error: BaseException | None = None
            try:
                if stored is None:
                    lifecycle.discard_staged(staged)
                else:
                    lifecycle.compensate_promotion(stored)
            except BaseException as exc:
                cleanup_error = exc

            rollback_error: BaseException | None = None
            try:
                await db.rollback()
            except BaseException as exc:
                rollback_error = exc

            if cleanup_error is not None:
                raise cleanup_error from operation_error
            if rollback_error is not None:
                raise rollback_error from operation_error
            raise

    async def prepare_download(
        self,
        db: AsyncSession,
        *,
        flow_id: str,
        attachment_id: str,
        user_id: str,
        party_filter: PartyFilter | None = None,
    ) -> VoucherDownload:
        flow = await payment_flow_service.get_flow_in_scope(
            db,
            flow_id=flow_id,
            current_user_id=user_id,
            party_filter=party_filter,
        )
        linked_ids = {str(value) for value in flow.voucher_attachment_ids or []}
        if attachment_id not in linked_ids:
            await self._record_download(
                db,
                user_id=user_id,
                flow_id=flow_id,
                attachment_id=attachment_id,
                file_name=None,
                result="not_found",
                response_status=404,
            )
            raise ResourceNotFoundError("Attachment", attachment_id)

        attachment = await attachment_crud.get_for_owner(
            db,
            attachment_id=attachment_id,
            owner_type="payment_flow",
            owner_id=flow_id,
        )
        if attachment is None:
            await self._record_download(
                db,
                user_id=user_id,
                flow_id=flow_id,
                attachment_id=attachment_id,
                file_name=None,
                result="not_found",
                response_status=404,
            )
            raise ResourceNotFoundError("Attachment", attachment_id)

        path = self._resolve_storage_path(attachment.storage_key)
        if not path.is_file():
            await self._record_download(
                db,
                user_id=user_id,
                flow_id=flow_id,
                attachment_id=attachment_id,
                file_name=attachment.file_name,
                result="not_found",
                response_status=404,
            )
            raise ResourceNotFoundError("Attachment", attachment_id)

        await self._record_download(
            db,
            user_id=user_id,
            flow_id=flow_id,
            attachment_id=attachment_id,
            file_name=attachment.file_name,
            result="success",
            response_status=200,
        )
        return VoucherDownload(attachment=attachment, path=path)

    async def list_download_audits(
        self,
        db: AsyncSession,
        *,
        flow_id: str,
        current_user_id: str,
        party_filter: PartyFilter | None = None,
    ) -> list[dict[str, Any]]:
        await payment_flow_service.get_flow_in_scope(
            db,
            flow_id=flow_id,
            current_user_id=current_user_id,
            party_filter=party_filter,
        )
        logs = await operation_log_crud.list_resource_actions_async(
            db,
            resource_type="payment_flow_voucher",
            resource_id=flow_id,
            action="download",
        )
        audits: list[dict[str, Any]] = []
        for log in logs:
            details = json.loads(log.details or "{}")
            audits.append(
                {
                    "log_id": str(log.id),
                    "user_id": str(log.user_id),
                    "flow_id": flow_id,
                    "attachment_id": str(details["attachment_id"]),
                    "file_name": details.get("file_name"),
                    "downloaded_at": log.created_at,
                    "result": str(details["result"]),
                }
            )
        return audits

    def _resolve_storage_path(self, storage_key: str) -> Path:
        root = self.uploads_root.resolve()
        path = (root / storage_key).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise InvalidRequestError("非法附件存储路径") from exc
        return path

    async def _record_download(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        flow_id: str,
        attachment_id: str,
        file_name: str | None,
        result: str,
        response_status: int,
    ) -> None:
        await operation_log_crud.create_async(
            db,
            user_id=user_id,
            action="download",
            action_name="下载收付流水凭证",
            module="ledger",
            module_name="经营台账",
            resource_type="payment_flow_voucher",
            resource_id=flow_id,
            resource_name=file_name,
            response_status=response_status,
            details=json.dumps(
                {
                    "attachment_id": attachment_id,
                    "file_name": file_name,
                    "result": result,
                },
                ensure_ascii=False,
            ),
        )


payment_voucher_service = PaymentVoucherService()
