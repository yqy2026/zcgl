"""Current v5 unit scope gates archive reads and immutable version writes."""

import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from zoneinfo import ZoneInfo

import fitz
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import UploadFile

from ...core.exception_handler import (
    BaseBusinessError,
    PartyScopeForbiddenError,
    ResourceNotFoundError,
)
from ...crud.archive_document import (
    ArchiveDocumentRepository,
    archive_document_repository,
)
from ...crud.asset_contract import asset_contract_repository
from ...crud.asset_unit_certificate import (
    AssetUnitCertificateRepository,
    asset_unit_certificate_repository,
)
from ...crud.contract_supplement import contract_supplement_repository
from ...crud.operation_log import OperationLogCRUD
from ...crud.property_certificate import (
    CRUDPropertyCertificate,
    property_certificate_crud,
)
from ...models.archive_document import ArchiveDocument
from ...models.asset_contract import ContractLifecycleEvent
from ...models.attachment import Attachment
from ...models.contract_supplement import ContractSupplement
from ...schemas.archive_document import (
    ArchiveDocumentItem,
    ArchiveDocumentListResponse,
    HandoverTarget,
    HandoverTargets,
)
from ..party_scope_resolver import EffectivePartyScope
from ..property_certificate.attachment_service import (
    PropertyCertificateAttachmentDownload,
    PropertyCertificateAttachmentService,
    PropertyCertificateAttachmentVersion,
    property_certificate_attachment_service,
)
from .contract_supplement_service import contract_supplement_service
from .handover_archive_service import unavailable_reason
from .management_fee_query_service import management_fee_query_service

CONTENT_TYPES = {
    "pdf": "application/pdf",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
}

_CONTRACT_SCAN_TARGETS = frozenset({"upstream_contract", "terminal_contract"})


class ArchiveDocumentQueryService:
    async def handover_targets(
        self,
        db: AsyncSession,
        *,
        kind: str,
        contract_id: str,
        scope: EffectivePartyScope,
    ) -> HandoverTargets:
        await contract_supplement_service._parent(db, kind, contract_id, scope)
        events = await asset_contract_repository.list_lifecycle_events(
            db, contract_kind=kind, contract_id=contract_id
        )
        today = self.clock().astimezone(ZoneInfo("Asia/Shanghai")).date()
        return HandoverTargets(
            items=[
                HandoverTarget(
                    event_id=e.id,
                    event_type="terminated"
                    if e.event_type == "terminated"
                    else "exited",
                    effective_date=e.effective_date,
                    handover_status=e.handover_status,
                    can_write=(reason := unavailable_reason(e, events, today)) is None,
                    unavailable_reason=reason,
                )
                for e in events
                if e.event_type in {"terminated", "exited"}
            ]
        )

    async def handover_rows(
        self,
        db: AsyncSession,
        identity: str,
        scope: EffectivePartyScope,
        *,
        writing: bool = False,
    ) -> tuple[ContractLifecycleEvent, list[tuple[ArchiveDocument, Attachment]]]:
        self._require_scope(scope)
        event = await asset_contract_repository.get_lifecycle_event_by_id(
            db, event_id=identity
        )
        if event is None or event.event_type not in {"terminated", "exited"}:
            raise ResourceNotFoundError("ContractLifecycleEvent", identity)
        await contract_supplement_service._parent(
            db, event.contract_kind, event.contract_id, scope, lock=writing
        )
        events = await asset_contract_repository.list_lifecycle_events(
            db, contract_kind=event.contract_kind, contract_id=event.contract_id
        )
        event = next((e for e in events if e.id == identity), None)
        if event is None:
            raise ResourceNotFoundError("ContractLifecycleEvent", identity)
        reason = unavailable_reason(
            event, events, self.clock().astimezone(ZoneInfo("Asia/Shanghai")).date()
        )
        if writing and reason is not None:
            raise BaseBusinessError(
                "交接事件目前不可维护档案", code=reason, status_code=409
            )
        rows = await self.documents.target_rows(
            db,
            target_type="contract_lifecycle_event",
            target_id=identity,
            document_type="handover",
        )
        if any(
            a.owner_type != "contract" or a.owner_id != event.contract_id
            for _, a in rows
        ):
            raise ResourceNotFoundError("ArchiveDocument", identity)
        return event, rows

    async def append_handover(
        self,
        db: AsyncSession,
        *,
        target_id: str,
        file: UploadFile,
        actor_id: str,
        scope: EffectivePartyScope,
        attachment_id: str | None = None,
    ) -> ArchiveDocumentItem:
        event, _ = await self.handover_rows(db, target_id, scope, writing=True)
        return self._item(
            await self.files._write(
                db,
                certificate_id=event.contract_id,
                attachment_id=attachment_id,
                file=file,
                user_id=actor_id,
                archive_target=("contract_lifecycle_event", event.id, "handover"),
            )
        )

    async def list_handover(
        self,
        db: AsyncSession,
        *,
        target_id: str,
        scope: EffectivePartyScope,
        include_history: bool = True,
    ) -> ArchiveDocumentListResponse:
        _, rows = await self.handover_rows(db, target_id, scope)
        replaced = {d.replaces_document_id for d, _ in rows}
        return ArchiveDocumentListResponse(
            items=[
                self._item(
                    PropertyCertificateAttachmentVersion(a, d, d.id not in replaced)
                )
                for d, a in rows
                if include_history or d.id not in replaced
            ]
        )

    async def supplement_rows(
        self,
        db: AsyncSession,
        identity: str,
        scope: EffectivePartyScope,
        *,
        writing: bool = False,
    ) -> tuple[ContractSupplement, list[tuple[ArchiveDocument, Attachment]]]:
        self._require_scope(scope)
        row = await contract_supplement_repository.get(db, identity)
        if row is None:
            raise ResourceNotFoundError("ContractSupplement", identity)
        await contract_supplement_service._parent(
            db, row.contract_kind, row.contract_id, scope, lock=writing
        )
        if writing:
            row = await contract_supplement_repository.get(db, identity, lock=True)
            if row is None:
                raise ResourceNotFoundError("ContractSupplement", identity)
            if row.withdrawn_at is not None:
                raise BaseBusinessError(
                    "Registration withdrawn",
                    code="SUPPLEMENT_WITHDRAWN",
                    status_code=409,
                )
        rows = await self.documents.target_rows(
            db,
            target_type="contract_supplement",
            target_id=identity,
            document_type="supplement",
        )
        if any(
            a.owner_type != "contract" or a.owner_id != row.contract_id for _, a in rows
        ):
            raise ResourceNotFoundError("ArchiveDocument", identity)
        return row, rows

    async def append_supplement(
        self,
        db: AsyncSession,
        *,
        target_id: str,
        file: UploadFile,
        actor_id: str,
        scope: EffectivePartyScope,
        attachment_id: str | None = None,
    ) -> ArchiveDocumentItem:
        row, _ = await self.supplement_rows(db, target_id, scope, writing=True)
        return self._item(
            await self.files._write(
                db,
                certificate_id=row.contract_id,
                attachment_id=attachment_id,
                file=file,
                user_id=actor_id,
                archive_target=("contract_supplement", row.id, "supplement"),
            )
        )

    async def list_supplement(
        self,
        db: AsyncSession,
        *,
        target_id: str,
        scope: EffectivePartyScope,
        include_history: bool = True,
    ) -> ArchiveDocumentListResponse:
        _, rows = await self.supplement_rows(db, target_id, scope)
        replaced = {d.replaces_document_id for d, _ in rows}
        return ArchiveDocumentListResponse(
            items=[
                self._item(
                    PropertyCertificateAttachmentVersion(a, d, d.id not in replaced)
                )
                for d, a in rows
                if include_history or d.id not in replaced
            ]
        )

    async def contract_scan_rows(
        self,
        db: AsyncSession,
        target_type: str,
        identity: str,
        scope: EffectivePartyScope,
        *,
        writing: bool = False,
    ) -> list[tuple[ArchiveDocument, Attachment]]:
        """The contract itself is the archive target; authorize it before files."""
        self._require_scope(scope)
        kind = "upstream" if target_type == "upstream_contract" else "terminal"
        await contract_supplement_service._parent(
            db, kind, identity, scope, lock=writing
        )
        rows = await self.documents.target_rows(
            db,
            target_type=target_type,
            target_id=identity,
            document_type=target_type,
        )
        if any(a.owner_type != "contract" or a.owner_id != identity for _, a in rows):
            raise ResourceNotFoundError("ArchiveDocument", identity)
        return rows

    async def append_contract_scan(
        self,
        db: AsyncSession,
        *,
        target_type: str,
        target_id: str,
        file: UploadFile,
        actor_id: str,
        scope: EffectivePartyScope,
        attachment_id: str | None = None,
    ) -> ArchiveDocumentItem:
        await self.contract_scan_rows(db, target_type, target_id, scope, writing=True)
        return self._item(
            await self.files._write(
                db,
                certificate_id=target_id,
                attachment_id=attachment_id,
                file=file,
                user_id=actor_id,
                archive_target=(target_type, target_id, target_type),
            )
        )

    async def list_contract_scan(
        self,
        db: AsyncSession,
        *,
        target_type: str,
        target_id: str,
        scope: EffectivePartyScope,
        include_history: bool = True,
    ) -> ArchiveDocumentListResponse:
        rows = await self.contract_scan_rows(db, target_type, target_id, scope)
        replaced = {d.replaces_document_id for d, _ in rows}
        return ArchiveDocumentListResponse(
            items=[
                self._item(
                    PropertyCertificateAttachmentVersion(a, d, d.id not in replaced)
                )
                for d, a in rows
                if include_history or d.id not in replaced
            ]
        )

    async def statement_rows(
        self,
        db: AsyncSession,
        identity: str,
        scope: EffectivePartyScope,
    ) -> list[tuple[ArchiveDocument, Attachment]]:
        """Statement stamps are read-only here; binding stays on the fee command."""
        self._require_scope(scope)
        # detail() owns the whole-statement boundary: owner party or a manager
        # covering every agreement; partial coverage hides the statement (404).
        await management_fee_query_service.detail(
            db, statement_id=identity, scope=scope
        )
        rows = await self.documents.target_rows(
            db,
            target_type="management_fee_statement",
            target_id=identity,
            document_type="management_fee_statement",
        )
        if any(
            a.owner_type != "management_fee_statement" or a.owner_id != identity
            for _, a in rows
        ):
            raise ResourceNotFoundError("ArchiveDocument", identity)
        return rows

    async def list_statement(
        self,
        db: AsyncSession,
        *,
        target_id: str,
        scope: EffectivePartyScope,
        include_history: bool = True,
    ) -> ArchiveDocumentListResponse:
        rows = await self.statement_rows(db, target_id, scope)
        replaced = {d.replaces_document_id for d, _ in rows}
        return ArchiveDocumentListResponse(
            items=[
                self._item(
                    PropertyCertificateAttachmentVersion(a, d, d.id not in replaced)
                )
                for d, a in rows
                if include_history or d.id not in replaced
            ]
        )

    @staticmethod
    def _item(version: PropertyCertificateAttachmentVersion) -> ArchiveDocumentItem:
        file, document = version.attachment, version.document
        return ArchiveDocumentItem.model_validate(
            dict(
                document_type=document.document_type,
                target_type=document.target_type,
                id=document.id,
                attachment_id=file.id,
                target_id=document.target_id,
                file_name=file.file_name,
                content_type=CONTENT_TYPES[file.file_type],
                file_size=file.file_size,
                document_version=document.document_version,
                replaces_document_id=document.replaces_document_id,
                uploaded_at=document.uploaded_at,
                is_current=version.is_current,
            )
        )

    async def append_document(
        self,
        db: AsyncSession,
        *,
        certificate_id: str,
        file: UploadFile,
        actor_id: str,
        scope: EffectivePartyScope,
    ) -> ArchiveDocumentItem:
        await self._authorize(db, certificate_id, scope)
        await self.files.lock_for_write(db, certificate_id)
        await self._authorize(db, certificate_id, scope)
        return self._item(
            await self.files.append(
                db, certificate_id=certificate_id, file=file, user_id=actor_id
            )
        )

    async def replace_document(
        self,
        db: AsyncSession,
        *,
        document_id: str,
        file: UploadFile,
        actor_id: str,
        scope: EffectivePartyScope,
    ) -> ArchiveDocumentItem:
        self._require_scope(scope)
        document = await self.documents.get_document(db, document_id=document_id)
        if (
            document is not None
            and document.target_type == "contract_lifecycle_event"
            and document.document_type == "handover"
        ):
            return await self.append_handover(
                db,
                target_id=document.target_id,
                file=file,
                actor_id=actor_id,
                scope=scope,
                attachment_id=document.attachment_id,
            )
        if (
            document is not None
            and document.target_type == "contract_supplement"
            and document.document_type == "supplement"
        ):
            return await self.append_supplement(
                db,
                target_id=document.target_id,
                file=file,
                actor_id=actor_id,
                scope=scope,
                attachment_id=document.attachment_id,
            )
        if (
            document is not None
            and document.target_type in _CONTRACT_SCAN_TARGETS
            and document.document_type == document.target_type
        ):
            return await self.append_contract_scan(
                db,
                target_type=document.target_type,
                target_id=document.target_id,
                file=file,
                actor_id=actor_id,
                scope=scope,
                attachment_id=document.attachment_id,
            )

        if (
            document is None
            or document.target_type != "property_certificate"
            or document.document_type != "property_certificate"
        ):
            raise ResourceNotFoundError("ArchiveDocument", document_id)
        await self._authorize(db, document.target_id, scope)
        await self.files.lock_for_write(db, document.target_id)
        await self._authorize(db, document.target_id, scope)
        return self._item(
            await self.files.replace(
                db,
                certificate_id=document.target_id,
                attachment_id=document.attachment_id,
                file=file,
                user_id=actor_id,
            )
        )

    def __init__(
        self,
        *,
        links: AssetUnitCertificateRepository = asset_unit_certificate_repository,
        certificates: CRUDPropertyCertificate = property_certificate_crud,
        files: PropertyCertificateAttachmentService = property_certificate_attachment_service,
        documents: ArchiveDocumentRepository = archive_document_repository,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.links = links
        self.certificates = certificates
        self.files = files
        self.documents = documents
        self.clock = clock

    @staticmethod
    def _require_scope(scope: EffectivePartyScope) -> None:
        if scope.scope_mode != "unrestricted":
            valid_axis = (
                scope.scope_mode == "owner"
                and len(scope.owner_party_ids) > 0
                or scope.scope_mode == "manager"
                and len(scope.manager_party_ids) > 0
                or scope.scope_mode == "all"
                and len(scope.effective_party_ids) > 0
            )
            if scope.error_code is not None or not valid_axis:
                raise PartyScopeForbiddenError(
                    code=scope.error_code or "PARTY_SCOPE_MISSING"
                )

    async def _authorize(
        self, db: AsyncSession, certificate_id: str, scope: EffectivePartyScope
    ) -> None:
        self._require_scope(scope)
        if scope.scope_mode != "unrestricted":
            if not await self.links.is_known_certificate(
                db,
                certificate_id=certificate_id,
                scope=scope,
                as_of=self.clock().astimezone(ZoneInfo("Asia/Shanghai")).date(),
            ):
                raise ResourceNotFoundError("PropertyCertificate", certificate_id)
        if await self.certificates.get(db, certificate_id) is None:
            raise ResourceNotFoundError("PropertyCertificate", certificate_id)

    async def list_documents(
        self,
        db: AsyncSession,
        *,
        certificate_id: str,
        scope: EffectivePartyScope,
        include_history: bool = True,
    ) -> ArchiveDocumentListResponse:
        await self._authorize(db, certificate_id, scope)
        versions = await self.files.list(
            db, certificate_id=certificate_id, include_history=include_history
        )
        items = []
        for version in versions:
            file, document = version.attachment, version.document
            if (
                file.owner_type != "property_certificate"
                or file.owner_id != certificate_id
            ):
                raise ResourceNotFoundError("ArchiveDocument", document.id)
            items.append(self._item(version))
        return ArchiveDocumentListResponse(items=items)

    async def _serve_download(
        self,
        db: AsyncSession,
        *,
        document_id: str,
        attachment: Attachment,
        actor_id: str,
        resource_type: str,
        resource_id: str,
        audit_action: str = "download",
        audit_action_name: str = "contract archive download",
    ) -> PropertyCertificateAttachmentDownload:
        """Audit and serve a contract-side archive file by its current storage."""
        path = self.files._resolve_path(attachment.storage_key)
        exists = path.is_file()
        await OperationLogCRUD().create_async(
            db,
            user_id=actor_id,
            action=audit_action,
            action_name=audit_action_name,
            module="asset_ops",
            module_name="asset_ops",
            resource_type=resource_type,
            resource_id=resource_id,
            response_status=200 if exists else 404,
            details=json.dumps(
                {
                    "document_id": document_id,
                    "attachment_id": attachment.id,
                    "result": "success" if exists else "not_found",
                }
            ),
        )
        if not exists:
            raise ResourceNotFoundError("Attachment", attachment.id)
        return PropertyCertificateAttachmentDownload(attachment=attachment, path=path)

    async def prepare_download(
        self,
        db: AsyncSession,
        *,
        document_id: str,
        actor_id: str,
        scope: EffectivePartyScope,
        audit_action: str = "download",
        audit_action_name: str = "contract archive download",
    ) -> PropertyCertificateAttachmentDownload:
        self._require_scope(scope)
        document = await self.documents.get_document(db, document_id=document_id)
        if document is not None and (document.target_type, document.document_type) in {
            ("contract_supplement", "supplement"),
            ("contract_lifecycle_event", "handover"),
        }:
            row, rows = await (
                self.handover_rows(db, document.target_id, scope)
                if document.target_type == "contract_lifecycle_event"
                else self.supplement_rows(db, document.target_id, scope)
            )
            attachment = next(
                (
                    a
                    for d, a in rows
                    if d.id == document_id
                    and a.owner_type == "contract"
                    and a.owner_id == row.contract_id
                ),
                None,
            )
            if attachment is None:
                raise ResourceNotFoundError("ArchiveDocument", document_id)
            return await self._serve_download(
                db,
                document_id=document_id,
                attachment=attachment,
                actor_id=actor_id,
                resource_type=document.target_type,
                resource_id=row.id,
                audit_action=audit_action,
                audit_action_name=audit_action_name,
            )
        if (
            document is not None
            and document.target_type in _CONTRACT_SCAN_TARGETS
            and document.document_type == document.target_type
        ):
            rows = await self.contract_scan_rows(
                db, document.target_type, document.target_id, scope
            )
            attachment = next(
                (
                    a
                    for d, a in rows
                    if d.id == document_id
                    and a.owner_type == "contract"
                    and a.owner_id == document.target_id
                ),
                None,
            )
            if attachment is None:
                raise ResourceNotFoundError("ArchiveDocument", document_id)
            return await self._serve_download(
                db,
                document_id=document_id,
                attachment=attachment,
                actor_id=actor_id,
                resource_type=document.target_type,
                resource_id=document.target_id,
                audit_action=audit_action,
                audit_action_name=audit_action_name,
            )
        if (
            document is not None
            and document.target_type == "management_fee_statement"
            and document.document_type == "management_fee_statement"
        ):
            rows = await self.statement_rows(db, document.target_id, scope)
            attachment = next(
                (
                    a
                    for d, a in rows
                    if d.id == document_id
                    and a.owner_type == "management_fee_statement"
                    and a.owner_id == document.target_id
                ),
                None,
            )
            if attachment is None:
                raise ResourceNotFoundError("ArchiveDocument", document_id)
            return await self._serve_download(
                db,
                document_id=document_id,
                attachment=attachment,
                actor_id=actor_id,
                resource_type="management_fee_statement",
                resource_id=document.target_id,
                audit_action=audit_action,
                audit_action_name=audit_action_name,
            )

        if (
            document is None
            or document.target_type != "property_certificate"
            or document.document_type != "property_certificate"
        ):
            raise ResourceNotFoundError("ArchiveDocument", document_id)
        await self._authorize(db, document.target_id, scope)
        return await self.files.prepare_download(
            db,
            certificate_id=document.target_id,
            attachment_id=document.attachment_id,
            user_id=actor_id,
            audit_action=audit_action,
            audit_action_name=audit_action_name,
        )

    async def prepare_thumbnail(
        self,
        db: AsyncSession,
        *,
        document_id: str,
        actor_id: str,
        scope: EffectivePartyScope,
    ) -> PropertyCertificateAttachmentDownload:
        """Resolve a thumbnail read through the download access chain.

        Same authorization as a download, but audited as a read so panel
        renders do not masquerade as content downloads.
        """
        return await self.prepare_download(
            db,
            document_id=document_id,
            actor_id=actor_id,
            scope=scope,
            audit_action="read",
            audit_action_name="contract archive thumbnail",
        )


archive_document_query_service = ArchiveDocumentQueryService()


def render_pdf_first_page(path: Path, *, max_width: int = 320) -> bytes:
    """Render the first PDF page as a PNG thumbnail bounded by max_width."""
    with fitz.open(path) as document:
        page = document.load_page(0)
        scale = min(1.0, max_width / page.rect.width)
        matrix = fitz.Matrix(scale, scale)
        pixmap = page.get_pixmap(matrix=matrix)
        return cast(bytes, pixmap.tobytes("png"))
