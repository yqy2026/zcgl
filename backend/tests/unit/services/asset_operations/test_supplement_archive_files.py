from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.services.asset_operations import archive_document_query_service as module
from src.services.asset_operations.archive_document_query_service import (
    ArchiveDocumentQueryService,
)
from src.services.party_scope_resolver import EffectivePartyScope

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
@pytest.mark.parametrize("writing", [False, True])
async def test_wrong_owner_fails_before_file_write(monkeypatch, writing):
    row = SimpleNamespace(
        contract_kind="upstream", contract_id="parent", withdrawn_at=None
    )
    monkeypatch.setattr(
        module.contract_supplement_repository, "get", AsyncMock(return_value=row)
    )
    monkeypatch.setattr(module.contract_supplement_service, "_parent", AsyncMock())
    docs = AsyncMock()
    docs.target_rows.return_value = [
        (
            SimpleNamespace(id="doc"),
            SimpleNamespace(owner_type="contract", owner_id="wrong"),
        )
    ]
    files = AsyncMock()
    service = ArchiveDocumentQueryService(documents=docs, files=files)
    scope = EffectivePartyScope(
        user_id="u", source="unrestricted", scope_mode="unrestricted"
    )
    with pytest.raises(Exception) as error:
        await service.supplement_rows(AsyncMock(), "supp", scope, writing=writing)
    assert error.value.status_code == 404
    files._write.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("exists", [False, True])
async def test_authorized_download_audits_file_result(monkeypatch, tmp_path, exists):
    import json
    from unittest.mock import Mock

    from src.core.exception_handler import ResourceNotFoundError

    document = SimpleNamespace(
        id="doc",
        target_type="contract_supplement",
        target_id="supp",
        document_type="supplement",
    )
    attachment = SimpleNamespace(
        id="file", owner_type="contract", owner_id="parent", storage_key="file.png"
    )
    row = SimpleNamespace(id="supp", contract_id="parent")
    docs = AsyncMock()
    docs.get_document.return_value = document
    path = tmp_path / "file.png"
    if exists:
        path.write_bytes(b"scan")
    files = Mock()
    files._resolve_path.return_value = path
    service = ArchiveDocumentQueryService(documents=docs, files=files)
    monkeypatch.setattr(
        service,
        "supplement_rows",
        AsyncMock(return_value=(row, [(document, attachment)])),
    )
    audit = AsyncMock()
    monkeypatch.setattr(module, "OperationLogCRUD", lambda: audit)
    scope = EffectivePartyScope(
        user_id="u", source="unrestricted", scope_mode="unrestricted"
    )
    if exists:
        result = await service.prepare_download(
            AsyncMock(), document_id="doc", actor_id="u", scope=scope
        )
        assert result.path == path
    else:
        with pytest.raises(ResourceNotFoundError):
            await service.prepare_download(
                AsyncMock(), document_id="doc", actor_id="u", scope=scope
            )
    audit.create_async.assert_awaited_once()
    args = audit.create_async.await_args.kwargs
    assert args["response_status"] == (200 if exists else 404)
    assert json.loads(args["details"])["result"] == (
        "success" if exists else "not_found"
    )
