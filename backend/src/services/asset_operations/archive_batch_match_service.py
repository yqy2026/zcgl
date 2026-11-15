"""Filename-driven pairing suggestions and atomic multi-file archive commits."""

import re
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import UploadFile

from ...core.exception_handler import BaseBusinessError, ResourceNotFoundError
from ...crud.archive_document import (
    ArchiveDocumentRepository,
    archive_document_repository,
)
from ...crud.asset_contract import AssetContractRepository, asset_contract_repository
from ...schemas.archive_batch_match import (
    BatchMatchCandidate,
    BatchMatchCommitRequest,
    BatchMatchCommitResponse,
    BatchMatchPreviewItem,
    BatchMatchPreviewResponse,
)
from ..file_upload import StagedFile, StagedFileService, StoredFile, UploadPurpose
from ..party_scope_resolver import EffectivePartyScope
from ..property_certificate.attachment_service import (
    PropertyCertificateAttachmentService,
    property_certificate_attachment_service,
)
from .archive_document_query_service import archive_document_query_service
from .contract_supplement_service import contract_supplement_service

# Real ledger scans carry numbers like 【元件合字[2025]第018号】 /
# 五羊司合字[2024]112号 / 元件司合字【2021】09号 with bracket-, width- and
# zero-padding variants; one normalized key must fold them together.
_CONTRACT_NUMBER = re.compile(
    r"([一-龥]{2,10}?(?:司合字|合字))[（(【\[〔]\s*(\d{4})\s*[)）】\]〕]\s*第?\s*0*(\d+)\s*号"
)
_KIND_TO_CONTRACT_KIND = {
    "upstream_contract": "upstream",
    "terminal_contract": "terminal",
}


def normalize_contract_number(raw: str) -> str | None:
    """Return the canonical `代字[年]序号号` key embedded in ``raw``, if any."""
    match = _CONTRACT_NUMBER.search(re.sub(r"[\s\u3000]+", "", raw))
    if match is None:
        return None
    prefix, year, number = match.groups()
    return f"{prefix}[{year}]{number.lstrip('0') or '0'}号"


@dataclass
class _StagedEntry:
    staged: StagedFile
    file_name: str


@dataclass
class _PreviewSession:
    actor_id: str
    expires_at: datetime
    entries: dict[str, _StagedEntry] = field(default_factory=dict)


class ArchiveBatchMatchService:
    """Preview suggests; nothing binds until a commit names every target."""

    def __init__(
        self,
        *,
        uploads_root: Path | None = None,
        contracts: AssetContractRepository = asset_contract_repository,
        documents: ArchiveDocumentRepository = archive_document_repository,
        files: PropertyCertificateAttachmentService = property_certificate_attachment_service,
        ttl: timedelta = timedelta(minutes=30),
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        # Staging, promotion and compensation must share one storage tree;
        # follow the attachment service root unless a test overrides it.
        self.uploads_root = (
            uploads_root if uploads_root is not None else files.uploads_root
        )
        self.contracts = contracts
        self.documents = documents
        self.files = files
        self.ttl = ttl
        self.clock = clock
        self._sessions: dict[str, _PreviewSession] = {}

    @staticmethod
    def _require_scope(scope: EffectivePartyScope) -> None:
        archive_document_query_service._require_scope(scope)

    def _purge_expired(self, lifecycle: StagedFileService) -> None:
        now = self.clock()
        for token, session in list(self._sessions.items()):
            if session.expires_at <= now:
                for entry in session.entries.values():
                    lifecycle.discard_staged(entry.staged)
                del self._sessions[token]

    async def preview(
        self,
        db: AsyncSession,
        *,
        files: Sequence[UploadFile],
        actor_id: str,
        scope: EffectivePartyScope,
    ) -> BatchMatchPreviewResponse:
        self._require_scope(scope)
        if len(files) > 50:
            raise BaseBusinessError(
                "单次最多配对 50 份文件", code="BATCH_TOO_MANY_FILES", status_code=422
            )
        lifecycle = StagedFileService(self.uploads_root)
        self._purge_expired(lifecycle)
        session = _PreviewSession(actor_id=actor_id, expires_at=self.clock() + self.ttl)
        items: list[BatchMatchPreviewItem] = []
        try:
            for file in files:
                staged = await lifecycle.stage_upload(
                    file, UploadPurpose.PROPERTY_CERTIFICATE_EXTRACTION
                )
                staging_id = str(uuid.uuid4())
                session.entries[staging_id] = _StagedEntry(
                    staged=staged, file_name=file.filename or ""
                )
            index = await self._number_index(db, scope)
            for staging_id, entry in session.entries.items():
                key = normalize_contract_number(entry.file_name)
                hits = index.get(key, []) if key is not None else []
                detected = None
                ambiguous: list[BatchMatchCandidate] = []
                already = False
                if len(hits) == 1:
                    detected = self._candidate(hits[0])
                    already = bool(
                        await self.documents.target_rows(
                            db,
                            target_type=detected.target_type,
                            target_id=detected.target_id,
                            document_type=detected.target_type,
                        )
                    )
                elif len(hits) > 1:
                    ambiguous = [self._candidate(hit) for hit in hits]
                items.append(
                    BatchMatchPreviewItem(
                        staging_id=staging_id,
                        file_name=entry.file_name,
                        file_size=entry.staged.size_bytes,
                        detected=detected,
                        ambiguous=ambiguous,
                        already_archived=already,
                    )
                )
        except BaseException:
            for entry in session.entries.values():
                lifecycle.discard_staged(entry.staged)
            raise
        token = str(uuid.uuid4())
        self._sessions[token] = session
        return BatchMatchPreviewResponse(
            preview_token=token,
            expires_at=session.expires_at,
            items=items,
        )

    async def _number_index(
        self, db: AsyncSession, scope: EffectivePartyScope
    ) -> dict[str, list[tuple[str, str, str, str]]]:
        index: dict[str, list[tuple[str, str, str, str]]] = {}
        for hit in await self.contracts.contract_numbers_in_scope(db, scope=scope):
            key = normalize_contract_number(hit[2])
            if key is not None:
                index.setdefault(key, []).append(hit)
        return index

    @staticmethod
    def _candidate(hit: tuple[str, str, str, str]) -> BatchMatchCandidate:
        kind, target_id, number, name = hit
        return BatchMatchCandidate(
            target_type=kind,  # type: ignore[arg-type]
            target_id=target_id,
            label=f"{number} {name}".strip(),
        )

    async def commit(
        self,
        db: AsyncSession,
        *,
        request: BatchMatchCommitRequest,
        actor_id: str,
        scope: EffectivePartyScope,
    ) -> BatchMatchCommitResponse:
        self._require_scope(scope)
        lifecycle = StagedFileService(self.uploads_root)
        # No opportunistic purge here: an expired-but-present session must
        # surface BATCH_PREVIEW_EXPIRED, not a generic miss.
        session = self._sessions.get(request.preview_token)
        if session is None or session.actor_id != actor_id:
            raise ResourceNotFoundError("BatchMatchPreview", request.preview_token)
        if session.expires_at <= self.clock():
            for entry in session.entries.values():
                lifecycle.discard_staged(entry.staged)
            del self._sessions[request.preview_token]
            raise BaseBusinessError(
                "预览已过期，请重新上传",
                code="BATCH_PREVIEW_EXPIRED",
                status_code=409,
            )
        targets: dict[tuple[str, str], str] = {}
        for match in request.matches:
            if match.staging_id not in session.entries:
                raise ResourceNotFoundError("BatchMatchStaging", match.staging_id)
            key = (match.target_type, match.target_id)
            if key in targets:
                raise BaseBusinessError(
                    "同一目标在本次提交中出现多次",
                    code="ARCHIVE_BATCH_DUPLICATE_TARGET",
                    status_code=409,
                )
            targets[key] = match.staging_id
        # Stable lock order keeps concurrent batches from deadlocking.
        ordered = sorted(request.matches, key=lambda m: (m.target_type, m.target_id))
        for match in ordered:
            await contract_supplement_service._parent(
                db,
                _KIND_TO_CONTRACT_KIND[match.target_type],
                match.target_id,
                scope,
                lock=True,
            )
        for match in ordered:
            rows = await self.documents.target_rows(
                db,
                target_type=match.target_type,
                target_id=match.target_id,
                document_type=match.target_type,
            )
            if any(
                attachment.owner_type != "contract"
                or attachment.owner_id != match.target_id
                for _, attachment in rows
            ):
                # Mis-owned archive rows stay loud instead of silently passing.
                raise ResourceNotFoundError("ArchiveDocument", match.target_id)
            if rows:
                raise BaseBusinessError(
                    "目标已有现行档案，请改用替换",
                    code="ARCHIVE_TARGET_ALREADY_HAS_FILE",
                    status_code=409,
                )
        promotions: list[tuple[StagedFile, StoredFile]] = []
        items = []
        try:
            for match in ordered:
                current_entry = session.entries.get(match.staging_id)
                if current_entry is None:
                    # A concurrent commit consumed this staging file already.
                    raise ResourceNotFoundError("BatchMatchStaging", match.staging_id)
                entry = current_entry
                version, _ = await self.files._write_staged(
                    db,
                    staged=entry.staged,
                    owner_id=match.target_id,
                    user_id=actor_id,
                    archive_target=(
                        match.target_type,
                        match.target_id,
                        match.target_type,
                    ),
                    promotions=promotions,
                )
                items.append(archive_document_query_service._item(version))
            await db.commit()
        except BaseException as operation_error:
            cleanup_error: BaseException | None = None
            try:
                for _, stored in promotions:
                    lifecycle.compensate_promotion(stored)
            except BaseException as exc:
                cleanup_error = exc
            # The whole preview is spent: promoted files are compensated away
            # and untouched ones must not survive as half-usable staging, so a
            # retry gets a clean miss instead of lifecycle 500s.
            for entry in session.entries.values():
                try:
                    lifecycle.discard_staged(entry.staged)
                except BaseException as exc:
                    if cleanup_error is None:
                        cleanup_error = exc
            self._sessions.pop(request.preview_token, None)
            try:
                await db.rollback()
            except BaseException as exc:
                if cleanup_error is None:
                    cleanup_error = exc
            if cleanup_error is not None:
                raise cleanup_error from operation_error
            raise
        for match in ordered:
            session.entries.pop(match.staging_id, None)
        if not session.entries:
            self._sessions.pop(request.preview_token, None)
        return BatchMatchCommitResponse(items=items)


archive_batch_match_service = ArchiveBatchMatchService()
