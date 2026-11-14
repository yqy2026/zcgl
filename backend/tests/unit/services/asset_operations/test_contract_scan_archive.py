"""Contract scan archives authorize the contract before any file write."""

from types import SimpleNamespace as Row
from unittest.mock import AsyncMock

import pytest

from src.services.asset_operations import archive_document_query_service as module
from src.services.asset_operations.archive_document_query_service import (
    ArchiveDocumentQueryService,
)
from src.services.party_scope_resolver import EffectivePartyScope

pytestmark = pytest.mark.unit

SCOPE = EffectivePartyScope(
    user_id="u", source="unrestricted", scope_mode="unrestricted"
)


def service(documents=None, files=None) -> ArchiveDocumentQueryService:
    return ArchiveDocumentQueryService(
        documents=documents or AsyncMock(), files=files or AsyncMock()
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("writing", [False, True])
@pytest.mark.parametrize("target_type", ["upstream_contract", "terminal_contract"])
async def test_wrong_owner_fails_before_file_write(monkeypatch, target_type, writing):
    parent = AsyncMock()
    monkeypatch.setattr(module.contract_supplement_service, "_parent", parent)
    docs = AsyncMock()
    docs.target_rows.return_value = [
        (Row(id="doc"), Row(owner_type="contract", owner_id="wrong"))
    ]
    files = AsyncMock()
    with pytest.raises(Exception) as error:
        await service(docs, files).contract_scan_rows(
            AsyncMock(), target_type, "contract-1", SCOPE, writing=writing
        )
    assert error.value.status_code == 404
    files._write.assert_not_called()
    kind = "upstream" if target_type == "upstream_contract" else "terminal"
    parent.assert_awaited_once_with(
        parent.call_args.args[0], kind, "contract-1", SCOPE, lock=writing
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("target_type", ["upstream_contract", "terminal_contract"])
async def test_append_registers_under_contract_target(monkeypatch, target_type):
    monkeypatch.setattr(module.contract_supplement_service, "_parent", AsyncMock())
    docs = AsyncMock()
    docs.target_rows.return_value = []
    files = AsyncMock()
    files._write.return_value = Row(
        attachment=Row(
            id="a",
            file_name="scan.pdf",
            file_type="pdf",
            file_size=4,
        ),
        document=Row(
            id="d",
            document_type=target_type,
            target_type=target_type,
            target_id="contract-1",
            document_version=1,
            replaces_document_id=None,
            uploaded_at="2026-11-04T00:00:00",
        ),
        is_current=True,
    )
    db = AsyncMock()
    item = await service(docs, files).append_contract_scan(
        db,
        target_type=target_type,
        target_id="contract-1",
        file=Row(),
        actor_id="actor",
        scope=SCOPE,
    )
    assert item.target_type == target_type
    files._write.assert_awaited_once_with(
        db,
        certificate_id="contract-1",
        attachment_id=None,
        file=files._write.await_args.kwargs["file"],
        user_id="actor",
        archive_target=(target_type, "contract-1", target_type),
    )


@pytest.mark.asyncio
async def test_list_marks_current_versions(monkeypatch):
    monkeypatch.setattr(module.contract_supplement_service, "_parent", AsyncMock())
    current, replaced = (
        Row(
            id="new",
            replaces_document_id="old",
            document_type="upstream_contract",
            target_type="upstream_contract",
            target_id="contract-1",
            document_version=2,
            uploaded_at="2026-11-04T00:00:00",
        ),
        Row(
            id="old",
            replaces_document_id=None,
            document_type="upstream_contract",
            target_type="upstream_contract",
            target_id="contract-1",
            document_version=1,
            uploaded_at="2026-11-03T00:00:00",
        ),
    )
    docs = AsyncMock()
    docs.target_rows.return_value = [
        (
            replaced,
            Row(
                id="a1",
                owner_type="contract",
                owner_id="contract-1",
                file_name="old.pdf",
                file_type="pdf",
                file_size=3,
            ),
        ),
        (
            current,
            Row(
                id="a2",
                owner_type="contract",
                owner_id="contract-1",
                file_name="new.pdf",
                file_type="pdf",
                file_size=4,
            ),
        ),
    ]
    files = AsyncMock()
    result = await service(docs, files).list_contract_scan(
        AsyncMock(),
        target_type="upstream_contract",
        target_id="contract-1",
        scope=SCOPE,
        include_history=False,
    )
    assert [item.id for item in result.items] == ["new"]
    assert result.items[0].is_current is True
    assert result.items[0].document_version == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("target_type", ["upstream_contract", "terminal_contract"])
async def test_replace_dispatches_contract_scan(monkeypatch, target_type):
    document = Row(
        id="doc",
        target_type=target_type,
        target_id="contract-1",
        document_type=target_type,
        attachment_id="attach-1",
    )
    docs = AsyncMock()
    docs.get_document.return_value = document
    appended = Row(id="new")
    scan = AsyncMock(return_value=appended)
    files = AsyncMock()
    query = service(docs, files)
    monkeypatch.setattr(query, "append_contract_scan", scan)
    await query.replace_document(
        AsyncMock(), document_id="doc", file=Row(), actor_id="actor", scope=SCOPE
    )
    scan.assert_awaited_once_with(
        scan.await_args.args[0],
        target_type=target_type,
        target_id="contract-1",
        file=scan.await_args.kwargs["file"],
        actor_id="actor",
        scope=SCOPE,
        attachment_id="attach-1",
    )
    files.replace.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("exists", [False, True])
async def test_download_contract_scan_audits_result(monkeypatch, tmp_path, exists):
    import json
    from unittest.mock import Mock

    from src.core.exception_handler import ResourceNotFoundError

    document = Row(
        id="doc",
        target_type="terminal_contract",
        target_id="contract-1",
        document_type="terminal_contract",
        attachment_id="attach-1",
    )
    attachment = Row(
        id="attach-1",
        owner_type="contract",
        owner_id="contract-1",
        file_name="scan.pdf",
        file_type="pdf",
        storage_key="terminal/scan.pdf",
    )
    target = tmp_path / ("scan.pdf" if exists else "other.pdf")
    if exists:
        target.write_bytes(b"scan")
    resolve = Mock(return_value=target)
    monkeypatch.setattr(module.contract_supplement_service, "_parent", AsyncMock())
    docs = AsyncMock()
    docs.get_document.return_value = document
    docs.target_rows.return_value = [(document, attachment)]
    files = AsyncMock()
    files._resolve_path = resolve
    audit = AsyncMock()
    monkeypatch.setattr(module, "OperationLogCRUD", Mock(return_value=audit))
    db = AsyncMock()
    if exists:
        result = await service(docs, files).prepare_download(
            db, document_id="doc", actor_id="u", scope=SCOPE
        )
        assert result.attachment is attachment
    else:
        with pytest.raises(ResourceNotFoundError):
            await service(docs, files).prepare_download(
                db, document_id="doc", actor_id="u", scope=SCOPE
            )
    call = audit.create_async.await_args
    assert call.kwargs["user_id"] == "u"
    assert call.kwargs["action"] == "download"
    assert call.kwargs["resource_type"] == "terminal_contract"
    assert call.kwargs["resource_id"] == "contract-1"
    assert call.kwargs["response_status"] == (200 if exists else 404)
    assert json.loads(call.kwargs["details"])["result"] == (
        "success" if exists else "not_found"
    )
