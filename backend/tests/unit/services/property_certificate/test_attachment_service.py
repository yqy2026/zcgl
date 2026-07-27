"""Tests for generic property-certificate attachment lifecycle guards."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from src.core.exception_handler import BusinessValidationError


@pytest.mark.asyncio
async def test_delete_rejects_the_final_attachment(monkeypatch) -> None:
    from src.services.property_certificate.attachment_service import (
        PropertyCertificateAttachmentService,
    )

    service = PropertyCertificateAttachmentService()

    async def list_attachments(db, *, certificate_id):
        return [SimpleNamespace(id="attachment-1")]

    monkeypatch.setattr(service, "list", list_attachments)

    with pytest.raises(BusinessValidationError, match="final property certificate attachment"):
        await service.delete(
            SimpleNamespace(), certificate_id="certificate-1", attachment_id="attachment-1"
        )


@pytest.mark.asyncio
async def test_replace_never_compensates_after_database_commit(monkeypatch, tmp_path: Path) -> None:
    import src.services.property_certificate.attachment_service as module
    from src.services.file_upload import UploadPurpose
    from src.services.file_upload.staged_files import StagedFile, StoredFile
    from src.services.property_certificate.attachment_service import (
        PropertyCertificateAttachmentService,
    )

    staged = StagedFile(
        stage_id="stage-1",
        purpose=UploadPurpose.PROPERTY_CERTIFICATE_EXTRACTION,
        original_filename="certificate.pdf",
        canonical_extension=".pdf",
        canonical_mime="application/pdf",
        size_bytes=12,
        sha256="a" * 64,
        storage_key=".staging/stage-1/source.pdf",
        path=tmp_path / ".staging" / "stage-1" / "source.pdf",
        created_at=__import__("datetime").datetime.now(),
    )
    stored = StoredFile(
        stage_id=staged.stage_id,
        purpose=staged.purpose,
        original_filename=staged.original_filename,
        canonical_extension=staged.canonical_extension,
        canonical_mime=staged.canonical_mime,
        size_bytes=staged.size_bytes,
        sha256=staged.sha256,
        storage_key="files/property_certificate/certificate-1/stage-1.pdf",
        path=tmp_path / "files" / "property_certificate" / "certificate-1" / "stage-1.pdf",
    )

    class FakeLifecycle:
        def __init__(self, _root):
            pass

        async def stage_upload(self, _file, _purpose):
            return staged

        def promote(self, _staged, *, owner_type, owner_id):
            assert (owner_type, owner_id) == ("property_certificate", "certificate-1")
            return stored

        def compensate_promotion(self, _stored):
            raise AssertionError("must not compensate after commit")

        def discard_staged(self, _staged):
            raise AssertionError("must not discard after commit")

    class FakeDb:
        commits = 0
        rollbacks = 0

        async def commit(self):
            self.commits += 1

        async def rollback(self):
            self.rollbacks += 1

    service = PropertyCertificateAttachmentService()
    old_attachment = SimpleNamespace(storage_key="files/property_certificate/certificate-1/old.pdf")
    restored = []

    async def require_certificate(db, certificate_id):
        return SimpleNamespace(id=certificate_id)

    async def require_attachment(db, certificate_id, attachment_id):
        return old_attachment

    async def delete_attachment(db, **kwargs):
        return old_attachment

    async def create_attachment(db, **kwargs):
        return SimpleNamespace(id="attachment-2")

    monkeypatch.setattr(module, "StagedFileService", FakeLifecycle)
    monkeypatch.setattr(service, "_require_certificate", require_certificate)
    monkeypatch.setattr(service, "_require_attachment", require_attachment)
    monkeypatch.setattr(module.attachment_crud, "delete_for_owner", delete_attachment)
    monkeypatch.setattr(module.attachment_crud, "create", create_attachment)
    monkeypatch.setattr(service, "_move_to_quarantine", lambda _path: tmp_path / "backup")
    monkeypatch.setattr(service, "_discard_quarantine", lambda _backup: (_ for _ in ()).throw(OSError("cleanup failed")))
    monkeypatch.setattr(service, "_restore_quarantine", lambda *args: restored.append(args))

    db = FakeDb()
    with pytest.raises(OSError, match="cleanup failed"):
        await service.replace(
            db,
            certificate_id="certificate-1",
            attachment_id="attachment-1",
            file=SimpleNamespace(),
            user_id="user-1",
        )

    assert db.commits == 1
    assert db.rollbacks == 0
    assert restored == []
