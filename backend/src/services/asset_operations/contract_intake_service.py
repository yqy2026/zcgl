"""Temporary upload/review sessions for confirmed signed-contract creation."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal, Protocol, cast
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import UploadFile

from ...core.exception_handler import ResourceConflictError, ResourceNotFoundError
from ...crud.attachment import attachment_crud as default_attachment_crud
from ...schemas.asset_operations import (
    ContractIntakeSessionResponse,
    ContractWarning,
    TerminalContractConfirmRequest,
    TerminalContractCreate,
    TerminalContractResponse,
    UpstreamContractConfirmRequest,
    UpstreamContractCreate,
    UpstreamContractResponse,
)
from ..document.extraction_sessions import (
    SESSION_TTL_SECONDS,
    ExtractionSessionRepository,
    ExtractionSessionStateError,
)
from ..file_upload import StagedFile, StagedFileService, StoredFile, UploadPurpose
from ..party_scope_resolver import EffectivePartyScope
from .contract_command_service import (
    asset_contract_command_service as default_command_service,
)

ContractIntakeType = Literal[
    "upstream_lease",
    "management_agreement",
    "terminal",
]


class IntakeSessionRepository(Protocol):
    def create(
        self,
        *,
        session_id: str,
        target_type: str,
        staged_file_key: str,
        candidates: Mapping[str, object],
        context: Mapping[str, str] | None = None,
        errors: list[str] | None = None,
    ) -> dict[str, object]: ...

    def get(self, session_id: str) -> dict[str, object] | None: ...

    def transition(
        self, session_id: str, expected_status: str, next_status: str
    ) -> dict[str, object]: ...


class IntakeAttachmentCRUD(Protocol):
    async def create(
        self,
        db: AsyncSession,
        *,
        data: dict[str, object],
        commit: bool = False,
    ) -> object: ...

    async def delete_for_owner(
        self,
        db: AsyncSession,
        *,
        attachment_id: str,
        owner_type: str,
        owner_id: str,
    ) -> object | None: ...


class IntakeFileLifecycle(Protocol):
    storage_root: Path

    async def stage_upload(
        self, upload: UploadFile, purpose: UploadPurpose | str
    ) -> StagedFile: ...

    def promote(
        self, staged: StagedFile, *, owner_type: str, owner_id: str
    ) -> StoredFile: ...

    def compensate_promotion(self, stored: StoredFile) -> None: ...

    def discard_staged(self, staged: StagedFile) -> None: ...


class ContractCommandWriter(Protocol):
    async def create_upstream(
        self,
        db: AsyncSession,
        *,
        request: UpstreamContractCreate,
        actor_id: str,
        scope: EffectivePartyScope,
        idempotency_key: str,
        attachment_owner_id: str,
    ) -> UpstreamContractResponse: ...

    async def create_terminal(
        self,
        db: AsyncSession,
        *,
        request: TerminalContractCreate,
        actor_id: str,
        scope: EffectivePartyScope,
        idempotency_key: str,
        attachment_owner_id: str,
    ) -> TerminalContractResponse: ...


def _utcnow() -> datetime:
    return datetime.now(UTC)


class ContractIntakeSessionService:
    """Keep scan and extraction candidates temporary until human confirmation."""

    def __init__(
        self,
        *,
        repository: IntakeSessionRepository,
        lifecycle: IntakeFileLifecycle,
        attachment_crud: IntakeAttachmentCRUD | None = None,
        command_service: ContractCommandWriter | None = None,
        clock: Callable[[], datetime] = _utcnow,
        id_factory: Callable[[], str] = lambda: str(uuid4()),
    ) -> None:
        self.repository = repository
        self.lifecycle = lifecycle
        self.attachment_crud = attachment_crud or default_attachment_crud
        self.command_service = command_service or default_command_service
        self.clock = clock
        self.id_factory = id_factory

    async def create(
        self,
        db: AsyncSession,
        *,
        file: UploadFile,
        contract_type: ContractIntakeType,
        actor_id: str,
    ) -> ContractIntakeSessionResponse:
        session_id = self.id_factory()
        document_id = self.id_factory()
        staged = await self.lifecycle.stage_upload(
            file, UploadPurpose.CONTRACT_EXTRACTION
        )
        stored: StoredFile | None = None
        session_created = False
        try:
            stored = self.lifecycle.promote(
                staged, owner_type="contract", owner_id=session_id
            )
            await self.attachment_crud.create(
                db,
                data={
                    "id": document_id,
                    "owner_type": "contract",
                    "owner_id": session_id,
                    "file_name": staged.original_filename,
                    "file_type": staged.canonical_extension.lstrip("."),
                    "file_size": staged.size_bytes,
                    "file_hash": staged.sha256,
                    "storage_key": stored.storage_key,
                    "created_by": actor_id,
                },
                commit=False,
            )
            expires_at = self.clock() + timedelta(seconds=SESSION_TTL_SECONDS)
            session = self.repository.create(
                session_id=session_id,
                target_type="contract_intake",
                staged_file_key=stored.storage_key,
                candidates={},
                context={
                    "actor_id": actor_id,
                    "contract_type": contract_type,
                    "document_id": document_id,
                    "expires_at": expires_at.isoformat(),
                    "stage_id": stored.stage_id,
                    "original_filename": stored.original_filename,
                    "canonical_extension": stored.canonical_extension,
                    "canonical_mime": stored.canonical_mime,
                    "size_bytes": str(stored.size_bytes),
                    "sha256": stored.sha256,
                },
                errors=["extraction_unavailable"],
            )
            session_created = True
            await db.commit()
            return self._public(session)
        except BaseException as operation_error:
            cleanup_error: BaseException | None = None
            try:
                if stored is None:
                    self.lifecycle.discard_staged(staged)
                else:
                    self.lifecycle.compensate_promotion(stored)
            except BaseException as exc:
                cleanup_error = exc
            try:
                await db.rollback()
            except BaseException as exc:
                if cleanup_error is None:
                    cleanup_error = exc
            if session_created:
                try:
                    self.repository.transition(
                        session_id, "ready_for_review", "failed"
                    )
                except ExtractionSessionStateError:
                    pass
            if cleanup_error is not None:
                raise cleanup_error from operation_error
            raise

    def get(
        self, *, session_id: str, actor_id: str
    ) -> ContractIntakeSessionResponse:
        return self._public(self._require_owned(session_id, actor_id))

    async def confirm_upstream(
        self,
        db: AsyncSession,
        *,
        session_id: str,
        request: UpstreamContractConfirmRequest,
        actor_id: str,
        scope: EffectivePartyScope,
        idempotency_key: str,
    ) -> UpstreamContractResponse:
        session = self._require_owned(session_id, actor_id)
        context = self._context(session)
        intake_type = context["contract_type"]
        if intake_type not in {"upstream_lease", "management_agreement"}:
            raise ResourceConflictError(
                "合同录入会话类型与上游确认端点不一致",
                resource_type="ContractIntakeSession",
            )
        contract_type = (
            "lease" if intake_type == "upstream_lease" else "management_agreement"
        )
        create_request = UpstreamContractCreate.model_validate(
            {
                **request.model_dump(mode="json"),
                "contract_type": contract_type,
                "scan_document_id": context["document_id"],
            }
        )
        status = str(session["status"])
        transitioned = self._enter_confirmation(session_id, status)
        try:
            response = await self.command_service.create_upstream(
                db,
                request=create_request,
                actor_id=actor_id,
                scope=scope,
                idempotency_key=idempotency_key,
                attachment_owner_id=session_id,
            )
        except BaseException:
            if transitioned:
                self.repository.transition(
                    session_id, "confirming", "ready_for_review"
                )
            raise
        self._finish_confirmation(session_id, status)
        return response

    async def confirm_terminal(
        self,
        db: AsyncSession,
        *,
        session_id: str,
        request: TerminalContractConfirmRequest,
        actor_id: str,
        scope: EffectivePartyScope,
        idempotency_key: str,
    ) -> TerminalContractResponse:
        session = self._require_owned(session_id, actor_id)
        context = self._context(session)
        if context["contract_type"] != "terminal":
            raise ResourceConflictError(
                "合同录入会话类型与终端确认端点不一致",
                resource_type="ContractIntakeSession",
            )
        create_request = TerminalContractCreate.model_validate(
            {
                **request.model_dump(mode="json"),
                "scan_document_id": context["document_id"],
            }
        )
        status = str(session["status"])
        transitioned = self._enter_confirmation(session_id, status)
        try:
            response = await self.command_service.create_terminal(
                db,
                request=create_request,
                actor_id=actor_id,
                scope=scope,
                idempotency_key=idempotency_key,
                attachment_owner_id=session_id,
            )
        except BaseException:
            if transitioned:
                self.repository.transition(
                    session_id, "confirming", "ready_for_review"
                )
            raise
        self._finish_confirmation(session_id, status)
        return response

    async def cancel(
        self,
        db: AsyncSession,
        *,
        session_id: str,
        actor_id: str,
    ) -> ContractIntakeSessionResponse:
        session = self._require_owned(session_id, actor_id)
        status = str(session["status"])
        if status == "cancelled":
            return self._public(session)
        if status not in {"ready_for_review", "cancelling"}:
            raise ResourceConflictError(
                "当前合同录入会话不可取消",
                resource_type="ContractIntakeSession",
                details={"status": status},
            )
        transitioned = False
        if status == "ready_for_review":
            session = self.repository.transition(
                session_id, "ready_for_review", "cancelling"
            )
            transitioned = True
        context = self._context(session)
        try:
            await self.attachment_crud.delete_for_owner(
                db,
                attachment_id=context["document_id"],
                owner_type="contract",
                owner_id=session_id,
            )
            await db.commit()
        except BaseException:
            await db.rollback()
            if transitioned:
                self.repository.transition(
                    session_id, "cancelling", "ready_for_review"
                )
            raise
        self.lifecycle.compensate_promotion(self._stored_file(session))
        cancelled = self.repository.transition(session_id, "cancelling", "cancelled")
        return self._public(cancelled)

    def _require_owned(self, session_id: str, actor_id: str) -> dict[str, object]:
        session = self.repository.get(session_id)
        if session is None or session.get("target_type") != "contract_intake":
            raise ResourceNotFoundError("ContractIntakeSession", session_id)
        context = self._context(session)
        if context.get("actor_id") != actor_id:
            raise ResourceNotFoundError("ContractIntakeSession", session_id)
        return session

    def _enter_confirmation(self, session_id: str, status: str) -> bool:
        if status == "ready_for_review":
            self.repository.transition(session_id, "ready_for_review", "confirming")
            return True
        if status in {"confirming", "confirmed"}:
            return False
        raise ResourceConflictError(
            "当前合同录入会话不可确认",
            resource_type="ContractIntakeSession",
            details={"status": status},
        )

    def _finish_confirmation(self, session_id: str, starting_status: str) -> None:
        if starting_status == "confirmed":
            return
        try:
            self.repository.transition(session_id, "confirming", "confirmed")
        except ExtractionSessionStateError:
            current = self.repository.get(session_id)
            if current is None or current.get("status") != "confirmed":
                raise

    def _public(self, session: Mapping[str, object]) -> ContractIntakeSessionResponse:
        context = self._context(session)
        warnings = []
        errors = session.get("errors")
        if isinstance(errors, list) and "extraction_unavailable" in errors:
            warnings.append(
                ContractWarning(
                    code="EXTRACTION_UNAVAILABLE",
                    severity="warning",
                    message="自动提取当前不可用，可继续手工核对并确认",
                )
            )
        candidates = session.get("candidates")
        return ContractIntakeSessionResponse.model_validate(
            {
                "id": session["session_id"],
                "document_id": context["document_id"],
                "contract_type": context["contract_type"],
                "status": session["status"],
                "candidate_fields": candidates if isinstance(candidates, dict) else {},
                "warnings": warnings,
                "expires_at": context["expires_at"],
            }
        )

    @staticmethod
    def _context(session: Mapping[str, object]) -> dict[str, str]:
        context = session.get("context")
        if not isinstance(context, Mapping) or not all(
            isinstance(key, str) and isinstance(value, str)
            for key, value in context.items()
        ):
            raise ExtractionSessionStateError("session_context_invalid")
        return cast(dict[str, str], dict(context))

    def _stored_file(self, session: Mapping[str, object]) -> StoredFile:
        context = self._context(session)
        storage_key = str(session["staged_file_key"])
        return StoredFile(
            stage_id=context["stage_id"],
            purpose=UploadPurpose.CONTRACT_EXTRACTION,
            original_filename=context["original_filename"],
            canonical_extension=context["canonical_extension"],
            canonical_mime=context["canonical_mime"],
            size_bytes=int(context["size_bytes"]),
            sha256=context["sha256"],
            storage_key=storage_key,
            path=(self.lifecycle.storage_root / storage_key).resolve(),
        )


def build_contract_intake_session_service(
    *, repository: ExtractionSessionRepository
) -> ContractIntakeSessionService:
    return ContractIntakeSessionService(
        repository=repository,
        lifecycle=StagedFileService(Path("uploads")),
        attachment_crud=default_attachment_crud,
        command_service=default_command_service,
    )


__all__ = [
    "ContractIntakeSessionService",
    "build_contract_intake_session_service",
]
