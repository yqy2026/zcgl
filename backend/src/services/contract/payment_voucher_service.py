"""Payment-flow voucher storage and download audit service."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

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
from src.utils import file_security

operation_log_crud = OperationLogCRUD()

_VOUCHER_FILE_RULES: dict[str, tuple[str, tuple[bytes, ...], str]] = {
    ".pdf": ("application/pdf", (b"%PDF-",), "PDF"),
    ".jpg": ("image/jpeg", (b"\xff\xd8\xff",), "JPEG"),
    ".jpeg": ("image/jpeg", (b"\xff\xd8\xff",), "JPEG"),
    ".png": ("image/png", (b"\x89PNG\r\n\x1a\n",), "PNG"),
}


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
        file_name: str,
        content_type: str | None,
        content: bytes,
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
        validation = file_security.validate_upload_file(
            file_name,
            content_type,
            len(content),
            allowed_extensions=[".pdf", ".jpg", ".jpeg", ".png"],
            max_size=20 * 1024 * 1024,
        )
        if not validation["valid"]:
            errors = validation.get("errors") or ["附件校验失败"]
            raise BusinessValidationError("; ".join(str(error) for error in errors))

        safe_name = str(validation.get("safe_filename") or file_name)
        self._validate_file_signature(
            file_name=safe_name,
            content_type=content_type,
            content=content,
        )
        attachment_id = str(uuid.uuid4())
        file_type = Path(safe_name).suffix.lower().lstrip(".")
        storage_key = (
            Path("payment_flows") / flow_id / attachment_id / safe_name
        ).as_posix()
        path = self._resolve_storage_path(storage_key)
        try:
            path.parent.mkdir(parents=True, exist_ok=False)
            path.write_bytes(content)
            attachment = await attachment_crud.create(
                db,
                data={
                    "id": attachment_id,
                    "owner_type": "payment_flow",
                    "owner_id": flow_id,
                    "file_name": safe_name,
                    "file_type": file_type,
                    "file_size": len(content),
                    "file_hash": hashlib.sha256(content).hexdigest(),
                    "storage_key": storage_key,
                    "created_by": user_id,
                },
                commit=False,
            )
            flow.voucher_attachment_ids = [
                *(str(value) for value in flow.voucher_attachment_ids or []),
                attachment_id,
            ]
            flow.updated_at = datetime.now(UTC).replace(tzinfo=None)
            await db.flush()
            await db.commit()
            return attachment
        except Exception:
            await db.rollback()
            if path.is_file():
                path.unlink()
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

    @staticmethod
    def _validate_file_signature(
        *,
        file_name: str,
        content_type: str | None,
        content: bytes,
    ) -> None:
        extension = Path(file_name).suffix.lower()
        rule = _VOUCHER_FILE_RULES.get(extension)
        if rule is None:
            raise BusinessValidationError("unsupported payment flow voucher file type")
        expected_mime, signatures, label = rule
        if content_type != expected_mime:
            raise BusinessValidationError(
                f"voucher MIME type does not match its {label} file type"
            )
        if not any(content.startswith(signature) for signature in signatures):
            raise BusinessValidationError(
                f"voucher content does not match its {label} file type"
            )

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
