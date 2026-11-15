"""Versioned certificate files never overwrite history."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.exception_handler import BaseBusinessError
from src.services.property_certificate import attachment_service as module

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


@pytest.fixture
def context(monkeypatch, tmp_path):
    old = SimpleNamespace(id="old", storage_key="old.pdf")
    (tmp_path / "old.pdf").write_bytes(b"old content")
    staged = SimpleNamespace(
        original_filename="new.pdf",
        canonical_extension=".pdf",
        size_bytes=3,
        sha256="a" * 64,
    )
    stored = SimpleNamespace(storage_key="new.pdf")
    lifecycle = MagicMock()
    lifecycle.stage_upload = AsyncMock(return_value=staged)
    lifecycle.promote.return_value = stored
    monkeypatch.setattr(module, "StagedFileService", lambda root: lifecycle)
    repository = SimpleNamespace(
        lock_certificate=AsyncMock(return_value=True),
        get_for_attachment=AsyncMock(return_value=SimpleNamespace(id="doc-old")),
        get_successor=AsyncMock(return_value=None),
        find_by_hash=AsyncMock(return_value=None),
        register=AsyncMock(return_value=SimpleNamespace(id="doc-new")),
    )
    monkeypatch.setattr(module, "archive_document_repository", repository)
    service = module.PropertyCertificateAttachmentService()
    service.uploads_root = tmp_path
    monkeypatch.setattr(service, "_require_certificate", AsyncMock())
    monkeypatch.setattr(service, "_require_attachment", AsyncMock(return_value=old))
    monkeypatch.setattr(
        module.attachment_crud,
        "create",
        AsyncMock(return_value=SimpleNamespace(id="new")),
    )
    deletion = AsyncMock(side_effect=AssertionError("history must not be deleted"))
    monkeypatch.setattr(module.attachment_crud, "delete_for_owner", deletion)
    db = SimpleNamespace(commit=AsyncMock(), rollback=AsyncMock())
    return service, repository, lifecycle, db, tmp_path


async def test_replace_preserves_old_file_and_registers_predecessor(context):
    service, repository, lifecycle, db, path = context
    result = await service.replace(
        db,
        certificate_id="cert",
        attachment_id="old",
        file=MagicMock(),
        user_id="actor",
    )
    assert result.attachment.id == "new"
    assert result.document.id == "doc-new"
    assert result.is_current is True
    assert (path / "old.pdf").read_bytes() == b"old content"
    assert repository.register.await_args.kwargs["replaces_document_id"] == "doc-old"
    db.commit.assert_awaited_once()
    lifecycle.compensate_promotion.assert_not_called()


async def test_failure_compensates_only_new_upload(context):
    service, repository, lifecycle, db, path = context
    repository.register.side_effect = RuntimeError("write failed")
    with pytest.raises(RuntimeError, match="write failed"):
        await service.replace(
            db,
            certificate_id="cert",
            attachment_id="old",
            file=MagicMock(),
            user_id="actor",
        )
    assert (path / "old.pdf").read_bytes() == b"old content"
    lifecycle.compensate_promotion.assert_called_once()
    db.rollback.assert_awaited_once()
    db.commit.assert_not_awaited()


@pytest.mark.parametrize("failure", ["successor", "duplicate"])
async def test_stale_or_duplicate_replacement_never_promotes(context, failure):
    service, repository, lifecycle, db, path = context
    if failure == "successor":
        repository.get_successor.return_value = SimpleNamespace(id="later")
    else:
        repository.find_by_hash.return_value = SimpleNamespace(id="same")
    with pytest.raises(BaseBusinessError) as exc:
        await service.replace(
            db,
            certificate_id="cert",
            attachment_id="old",
            file=MagicMock(),
            user_id="actor",
        )
    assert exc.value.status_code == 409
    lifecycle.promote.assert_not_called()
    lifecycle.discard_staged.assert_called_once()


async def test_delete_rejects_archived_file(context):
    service, repository, lifecycle, db, path = context
    with pytest.raises(BaseBusinessError) as exc:
        await service.delete(db, certificate_id="cert", attachment_id="old")
    assert exc.value.code == "ARCHIVE_HISTORY_PROTECTED"
    assert (path / "old.pdf").exists()
