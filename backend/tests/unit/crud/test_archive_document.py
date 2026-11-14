"""Archive writes participate in the caller's transaction."""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.crud.archive_document import ArchiveDocumentRepository

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


async def test_register_allocates_version_and_preserves_upload_audit():
    result = MagicMock()
    result.scalar_one.return_value = 3
    db = MagicMock(
        execute=AsyncMock(return_value=result), flush=AsyncMock(), commit=AsyncMock()
    )
    attachment = SimpleNamespace(
        id="file", created_by="actor", created_at=datetime(2026, 11, 2)
    )
    document = await ArchiveDocumentRepository().register(
        db,
        certificate_id="cert",
        attachment=attachment,
        replaces_document_id="previous",
    )
    assert document.document_version == 4
    assert document.attachment_id == "file"
    assert document.uploaded_by == "actor"
    assert document.uploaded_at == attachment.created_at
    assert document.replaces_document_id == "previous"
    db.flush.assert_awaited_once()
    db.commit.assert_not_awaited()


@pytest.mark.parametrize("include_history", [False, True])
async def test_list_filters_current_versions_without_removing_history(include_history):
    result = MagicMock()
    result.all.return_value = []
    db = MagicMock(execute=AsyncMock(return_value=result))
    assert (
        await ArchiveDocumentRepository().list_for_certificate(
            db, certificate_id="cert", include_history=include_history
        )
        == []
    )
    sql = str(
        db.execute.await_args.args[0].compile(compile_kwargs={"literal_binds": True})
    )
    assert "target_id = 'cert'" in sql
    assert "attachments.id = archive_documents.attachment_id" in sql
    assert ("NOT (EXISTS" in sql) is (not include_history)


async def test_target_lock_uses_for_update_and_missing_target_is_false():
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db = MagicMock(execute=AsyncMock(return_value=result))
    assert not await ArchiveDocumentRepository().lock_certificate(
        db, certificate_id="missing"
    )
    sql = str(
        db.execute.await_args.args[0].compile(compile_kwargs={"literal_binds": True})
    )
    assert "FOR UPDATE" in sql
    assert "property_certificates.id = 'missing'" in sql
