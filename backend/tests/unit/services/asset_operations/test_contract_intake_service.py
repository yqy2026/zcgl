"""Temporary signed-contract intake sessions guard the only create entrypoint."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.core.exception_handler import ResourceNotFoundError
from src.models.attachment import Attachment
from src.schemas.asset_operations import (
    UpstreamContractConfirmRequest,
    UpstreamContractResponse,
)
from src.services.asset_operations.contract_intake_service import (
    ContractIntakeSessionService,
)
from src.services.document.extraction_sessions import ExtractionSessionStateError
from src.services.file_upload import StagedFile, StoredFile, UploadPurpose
from src.services.party_scope_resolver import EffectivePartyScope

NOW = datetime(2026, 10, 24, 4, 0, tzinfo=UTC)
SCOPE = EffectivePartyScope(
    user_id="actor-1",
    source="explicit",
    scope_mode="owner",
    owner_party_ids=["owner-1"],
)


class _SessionRepository:
    def __init__(self) -> None:
        self.sessions: dict[str, dict[str, object]] = {}

    def create(self, **kwargs):
        session = {
            **kwargs,
            "status": "ready_for_review",
            "errors": list(kwargs.get("errors") or []),
        }
        self.sessions[str(kwargs["session_id"])] = session
        return session

    def get(self, session_id: str):
        session = self.sessions.get(session_id)
        return None if session is None else dict(session)

    def transition(self, session_id: str, expected_status: str, next_status: str):
        session = self.sessions.get(session_id)
        if session is None:
            raise ExtractionSessionStateError("session_not_found")
        if session["status"] != expected_status:
            raise ExtractionSessionStateError("session_state_conflict")
        session["status"] = next_status
        return dict(session)


class _Lifecycle:
    storage_root = Path("uploads")

    def __init__(self) -> None:
        self.compensated: list[StoredFile] = []

    async def stage_upload(self, _file, _purpose):
        return StagedFile(
            stage_id="stage-1",
            purpose=UploadPurpose.CONTRACT_EXTRACTION,
            original_filename="signed.pdf",
            canonical_extension=".pdf",
            canonical_mime="application/pdf",
            size_bytes=10,
            sha256="a" * 64,
            storage_key=".staging/stage-1/source.pdf",
            path=Path("uploads/.staging/stage-1/source.pdf"),
            created_at=NOW,
        )

    def promote(self, staged: StagedFile, *, owner_type: str, owner_id: str):
        assert owner_type == "contract"
        return StoredFile(
            stage_id=staged.stage_id,
            purpose=staged.purpose,
            original_filename=staged.original_filename,
            canonical_extension=staged.canonical_extension,
            canonical_mime=staged.canonical_mime,
            size_bytes=staged.size_bytes,
            sha256=staged.sha256,
            storage_key=f"files/contract/{owner_id}/stage-1.pdf",
            path=Path(f"uploads/files/contract/{owner_id}/stage-1.pdf"),
        )

    def compensate_promotion(self, stored: StoredFile) -> None:
        self.compensated.append(stored)

    def discard_staged(self, _staged: StagedFile) -> None:
        raise AssertionError("promoted file should be compensated instead")


class _AttachmentCRUD:
    def __init__(self) -> None:
        self.attachment: Attachment | None = None
        self.deleted = False

    async def create(self, _db, *, data, commit=False):
        assert commit is False
        self.attachment = Attachment(**data)
        return self.attachment

    async def delete_for_owner(
        self, _db, *, attachment_id: str, owner_type: str, owner_id: str
    ):
        if (
            self.attachment is None
            or self.attachment.id != attachment_id
            or self.attachment.owner_type != owner_type
            or self.attachment.owner_id != owner_id
        ):
            return None
        self.deleted = True
        return self.attachment


class _DB:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


def _response() -> UpstreamContractResponse:
    return UpstreamContractResponse.model_validate(
        {
            "id": "upstream-1",
            "contract_number": "UP-001",
            "contract_type": "lease",
            "name": "承租合同",
            "owner_party_id": "owner-1",
            "operator_party_id": "operator-1",
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "payment_cycle": "monthly",
            "deposit_amount": "0",
            "scan_document_id": "document-1",
            "asset_unit_ids": ["unit-1"],
            "rent_schedules": [],
            "version": 1,
            "created_at": NOW,
            "updated_at": NOW,
            "status": "expiring",
            "warnings": [],
        }
    )


def _service(*, command=None):
    sessions = _SessionRepository()
    lifecycle = _Lifecycle()
    attachments = _AttachmentCRUD()
    command = command or SimpleNamespace(
        create_upstream=AsyncMock(return_value=_response()),
        create_terminal=AsyncMock(),
    )
    ids = iter(["session-1", "document-1"])
    service = ContractIntakeSessionService(
        repository=sessions,
        lifecycle=lifecycle,
        attachment_crud=attachments,
        command_service=command,
        clock=lambda: NOW,
        id_factory=lambda: next(ids),
    )
    return service, sessions, lifecycle, attachments, command


@pytest.mark.asyncio
async def test_create_session_persists_scan_and_returns_reviewable_session() -> None:
    service, sessions, _lifecycle, attachments, _command = _service()
    db = _DB()

    response = await service.create(
        db,
        file=SimpleNamespace(filename="signed.pdf"),
        contract_type="upstream_lease",
        actor_id="actor-1",
    )

    assert response.id == "session-1"
    assert response.document_id == "document-1"
    assert response.status == "ready_for_review"
    assert response.warnings[0].code == "EXTRACTION_UNAVAILABLE"
    assert attachments.attachment is not None
    assert attachments.attachment.owner_id == "session-1"
    assert sessions.sessions["session-1"]["context"]["actor_id"] == "actor-1"
    assert db.commits == 1


@pytest.mark.asyncio
async def test_session_is_hidden_from_another_actor() -> None:
    service, _sessions, _lifecycle, _attachments, _command = _service()
    await service.create(
        _DB(),
        file=SimpleNamespace(filename="signed.pdf"),
        contract_type="upstream_lease",
        actor_id="actor-1",
    )

    with pytest.raises(ResourceNotFoundError):
        service.get(session_id="session-1", actor_id="actor-2")


@pytest.mark.asyncio
async def test_confirm_upstream_injects_session_type_and_document_then_confirms() -> None:
    service, sessions, _lifecycle, _attachments, command = _service()
    db = _DB()
    await service.create(
        db,
        file=SimpleNamespace(filename="signed.pdf"),
        contract_type="upstream_lease",
        actor_id="actor-1",
    )
    request = UpstreamContractConfirmRequest.model_validate(
        {
            "contract_number": "UP-001",
            "name": "承租合同",
            "owner_party_id": "owner-1",
            "operator_party_id": "operator-1",
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "payment_cycle": "monthly",
            "asset_unit_ids": ["unit-1"],
        }
    )

    response = await service.confirm_upstream(
        db,
        session_id="session-1",
        request=request,
        actor_id="actor-1",
        scope=SCOPE,
        idempotency_key="request-1",
    )

    assert response.id == "upstream-1"
    assert sessions.sessions["session-1"]["status"] == "confirmed"
    create_request = command.create_upstream.await_args.kwargs["request"]
    assert create_request.contract_type == "lease"
    assert create_request.scan_document_id == "document-1"
    assert command.create_upstream.await_args.kwargs["idempotency_key"] == "request-1"
    assert command.create_upstream.await_args.kwargs["attachment_owner_id"] == (
        "session-1"
    )


@pytest.mark.asyncio
async def test_failed_confirmation_returns_session_to_reviewable_state() -> None:
    command = SimpleNamespace(
        create_upstream=AsyncMock(side_effect=RuntimeError("write failed")),
        create_terminal=AsyncMock(),
    )
    service, sessions, _lifecycle, _attachments, _command = _service(command=command)
    await service.create(
        _DB(),
        file=SimpleNamespace(filename="signed.pdf"),
        contract_type="upstream_lease",
        actor_id="actor-1",
    )

    with pytest.raises(RuntimeError, match="write failed"):
        await service.confirm_upstream(
            _DB(),
            session_id="session-1",
            request=UpstreamContractConfirmRequest.model_validate(
                {
                    "contract_number": "UP-001",
                    "name": "承租合同",
                    "owner_party_id": "owner-1",
                    "operator_party_id": "operator-1",
                    "start_date": "2026-01-01",
                    "end_date": "2026-12-31",
                    "payment_cycle": "monthly",
                    "asset_unit_ids": ["unit-1"],
                }
            ),
            actor_id="actor-1",
            scope=SCOPE,
            idempotency_key="request-1",
        )

    assert sessions.sessions["session-1"]["status"] == "ready_for_review"


@pytest.mark.asyncio
async def test_cancel_removes_unconfirmed_attachment_and_file() -> None:
    service, sessions, lifecycle, attachments, _command = _service()
    db = _DB()
    await service.create(
        db,
        file=SimpleNamespace(filename="signed.pdf"),
        contract_type="terminal",
        actor_id="actor-1",
    )

    response = await service.cancel(db, session_id="session-1", actor_id="actor-1")

    assert response.status == "cancelled"
    assert sessions.sessions["session-1"]["status"] == "cancelled"
    assert attachments.deleted is True
    assert len(lifecycle.compensated) == 1
