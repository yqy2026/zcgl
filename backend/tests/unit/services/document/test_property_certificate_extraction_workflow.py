"""Property-certificate extraction workflow tests."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.services.document.candidate_review import (
    CandidateEvidence,
    CandidateReview,
    CandidateReviewService,
    FieldCandidate,
    FieldCandidates,
)
from src.services.document.deepseek_text_enrichment import DeepSeekEnrichmentResult
from src.services.document.page_text_pipeline import OrderedPageTextResult, PageText
from src.services.file_upload.staged_files import StagedFile, StoredFile


@dataclass
class FakeRepository:
    session: dict[str, object] | None = None

    def create(self, **kwargs):
        self.session = {"status": "ready_for_review", **kwargs}
        return self.session

    def transition(self, session_id, expected, replacement):
        assert self.session is not None
        assert self.session["session_id"] == session_id
        assert self.session["status"] == expected
        self.session["status"] = replacement
        return self.session

    def delete_after_status(self, session_id, status):
        assert self.session is not None
        assert self.session["session_id"] == session_id
        assert self.session["status"] == status
        key = self.session["staged_file_key"]
        self.session = None
        return key

    def get(self, session_id):
        if self.session is None or self.session["session_id"] != session_id:
            return None
        return self.session


class FakePipeline:
    def extract_pdf_pages(self, path):
        return OrderedPageTextResult(
            [PageText(page_number=1, text_source="pdf_text", text_lines=[])]
        )

    def extract_image_page(self, path):
        return self.extract_pdf_pages(path)


class FakeEnricher:
    def enrich(self, *args, **kwargs):
        return DeepSeekEnrichmentResult("skipped", "llm_disabled")


class FakeLifecycle:
    storage_root = Path("uploads")

    def __init__(self):
        self.promotions = []
        self.discarded = []

    def promote(self, staged, *, owner_type, owner_id):
        self.promotions.append((staged, owner_type, owner_id))
        return StoredFile(
            stage_id=staged.stage_id,
            purpose=staged.purpose,
            original_filename=staged.original_filename,
            canonical_extension=staged.canonical_extension,
            canonical_mime=staged.canonical_mime,
            size_bytes=staged.size_bytes,
            sha256=staged.sha256,
            storage_key=f"files/{owner_type}/{owner_id}/source.pdf",
            path=Path("uploads") / f"files/{owner_type}/{owner_id}/source.pdf",
        )

    def discard_path(self, path):
        self.discarded.append(path)

    def discard_staged(self, staged):
        self.discarded.append(staged.path)

    def compensate_promotion(self, stored):
        self.discarded.append(stored.path)


class FakeDb:
    def __init__(self):
        self.commits = 0
        self.rollbacks = 0

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1


@pytest.fixture
def staged_file():
    from src.services.file_upload import UploadPurpose

    return StagedFile(
        stage_id="stage-1",
        purpose=UploadPurpose.PROPERTY_CERTIFICATE_EXTRACTION,
        original_filename="certificate.pdf",
        canonical_extension=".pdf",
        canonical_mime="application/pdf",
        size_bytes=12,
        sha256="a" * 64,
        storage_key=".staging/stage-1/source.pdf",
        path=Path("uploads/.staging/stage-1/source.pdf"),
        created_at=datetime.now(),
    )


@pytest.mark.asyncio
async def test_new_confirmation_creates_generic_attachment_after_explicit_review(
    monkeypatch, staged_file
):
    import src.services.document.property_certificate_extraction_workflow as module
    from src.services.document.property_certificate_extraction_workflow import (
        PropertyCertificateExtractionWorkflow,
    )

    repository = FakeRepository()
    lifecycle = FakeLifecycle()
    workflow = PropertyCertificateExtractionWorkflow(
        repository=repository,
        pipeline=FakePipeline(),
        reviewer=CandidateReviewService(),
        enricher=FakeEnricher(),
        lifecycle=lifecycle,
    )
    candidate = FieldCandidate(
        field_key="certificate_number",
        value="CERT-001",
        text_source="pdf_text",
        extractor="rule",
        evidence=(
            CandidateEvidence(page_number=1, text="certificate number", text_source="pdf_text"),
        ),
        confidence_tier="high",
    )
    review = CandidateReview(
        fields={"certificate_number": FieldCandidates((candidate,), False)}
    )
    repository.create(
        session_id="session-1",
        target_type="property_certificate",
        staged_file_key=staged_file.storage_key,
        candidates=workflow._serialize_review(review),
        context={**workflow._session_context(staged_file), "mode": "new", "asset_id": "asset-1"},
        errors=[],
    )

    created = []
    attachments = []

    async def get_by_number(db, certificate_number):
        return None

    async def get_assets(db, *, ids, include_deleted):
        return [SimpleNamespace(id="asset-1")]

    async def assert_parties(db, *, party_ids, operation):
        assert party_ids == ["party-1"]
        assert operation == "property_certificate:create"

    async def create_certificate(db, **kwargs):
        created.append(kwargs)
        return SimpleNamespace(id="certificate-1")

    async def create_attachment(db, *, data, commit=False):
        attachments.append(data)
        return SimpleNamespace(id="attachment-1")

    monkeypatch.setattr(
        module.property_certificate_crud,
        "get_by_certificate_number_async",
        get_by_number,
    )
    monkeypatch.setattr(module.asset_crud, "get_multi_by_ids_async", get_assets)
    monkeypatch.setattr(module.party_service, "assert_parties_approved", assert_parties)
    monkeypatch.setattr(
        module.property_certificate_crud,
        "create_with_owners_async",
        create_certificate,
    )
    monkeypatch.setattr(module.attachment_crud, "create", create_attachment)

    db = FakeDb()
    certificate_id = await workflow.confirm(
        session_id="session-1",
        actions=[
            {
                "field_key": "certificate_number",
                "action": "accept_candidate",
                "candidate_value": "CERT-001",
            }
        ],
        certificate_type="other",
        holder_party_ids=["party-1"],
        attach_staged=True,
        db=db,
        current_user_id="user-1",
    )

    assert certificate_id == "certificate-1"
    assert db.commits == 1
    assert lifecycle.promotions[0][1:] == ("property_certificate", "certificate-1")
    assert created[0]["asset_ids"] == ["asset-1"]
    assert "attachments" not in created[0]
    assert attachments == [
        {
            "owner_type": "property_certificate",
            "owner_id": "certificate-1",
            "file_name": "certificate.pdf",
            "file_type": "pdf",
            "file_size": 12,
            "file_hash": "a" * 64,
            "storage_key": "files/property_certificate/certificate-1/source.pdf",
            "created_by": "user-1",
        }
    ]
    assert repository.session is None


@pytest.mark.asyncio
async def test_duplicate_certificate_number_returns_conflict_and_keeps_session(
    monkeypatch, staged_file
):
    import src.services.document.property_certificate_extraction_workflow as module
    from src.services.document.property_certificate_extraction_workflow import (
        PropertyCertificateConflictError,
        PropertyCertificateExtractionWorkflow,
    )

    repository = FakeRepository()
    workflow = PropertyCertificateExtractionWorkflow(
        repository=repository,
        pipeline=FakePipeline(),
        reviewer=CandidateReviewService(),
        enricher=FakeEnricher(),
        lifecycle=FakeLifecycle(),
    )
    review = CandidateReview(
        fields={
            "certificate_number": FieldCandidates(
                (
                    FieldCandidate(
                        field_key="certificate_number",
                        value="CERT-001",
                        text_source="pdf_text",
                        extractor="rule",
                        evidence=(
                            CandidateEvidence(
                                page_number=1,
                                text="certificate number",
                                text_source="pdf_text",
                            ),
                        ),
                        confidence_tier="high",
                    ),
                ),
                False,
            )
        }
    )
    repository.create(
        session_id="session-1",
        target_type="property_certificate",
        staged_file_key=staged_file.storage_key,
        candidates=workflow._serialize_review(review),
        context={**workflow._session_context(staged_file), "mode": "new", "asset_id": "asset-1"},
        errors=[],
    )

    async def get_by_number(db, certificate_number):
        return SimpleNamespace(id="existing-certificate")

    monkeypatch.setattr(
        module.property_certificate_crud,
        "get_by_certificate_number_async",
        get_by_number,
    )

    with pytest.raises(PropertyCertificateConflictError):
        await workflow.confirm(
            session_id="session-1",
            actions=[
                {
                    "field_key": "certificate_number",
                    "action": "accept_candidate",
                    "candidate_value": "CERT-001",
                }
            ],
            certificate_type="other",
            holder_party_ids=["party-1"],
            attach_staged=True,
            db=FakeDb(),
            current_user_id="user-1",
        )

    assert repository.session is not None
    assert repository.session["status"] == "ready_for_review"
