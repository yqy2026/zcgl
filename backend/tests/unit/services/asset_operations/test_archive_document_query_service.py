from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.exception_handler import PartyScopeForbiddenError, ResourceNotFoundError
from src.services.asset_operations.archive_document_query_service import (
    ArchiveDocumentQueryService,
)
from src.services.party_scope_resolver import EffectivePartyScope

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


@pytest.mark.parametrize(
    "mode,known,allowed",
    [
        ("owner", True, True),
        ("manager", True, True),
        ("owner", False, False),
        ("unrestricted", False, True),
    ],
)
async def test_archive_scope_is_checked_before_file_listing(mode, known, allowed):
    links = MagicMock(is_known_certificate=AsyncMock(return_value=known))
    certificates = MagicMock(get=AsyncMock(return_value=SimpleNamespace(id="cert")))
    files = MagicMock(list=AsyncMock(return_value=[]))
    service = ArchiveDocumentQueryService(
        links=links, certificates=certificates, files=files
    )
    scope = EffectivePartyScope(
        user_id="actor",
        source="explicit",
        scope_mode=mode,
        owner_party_ids=["owner"],
        manager_party_ids=["manager"],
    )
    if allowed:
        assert (
            await service.list_documents(
                MagicMock(), certificate_id="cert", scope=scope
            )
        ).items == []
    else:
        with pytest.raises(ResourceNotFoundError):
            await service.list_documents(
                MagicMock(), certificate_id="cert", scope=scope
            )
        files.list.assert_not_called()
        certificates.get.assert_not_called()


async def test_missing_scope_never_reads_files():
    files = MagicMock()
    service = ArchiveDocumentQueryService(files=files)
    with pytest.raises(PartyScopeForbiddenError):
        await service.list_documents(
            MagicMock(),
            certificate_id="cert",
            scope=EffectivePartyScope(user_id="a", source="none", scope_mode="none"),
        )
    files.list.assert_not_called()


@pytest.mark.parametrize(
    "mode,owners,managers",
    [("owner", [], ["manager"]), ("manager", ["owner"], []), ("all", [], [])],
)
async def test_wrong_scope_axis_is_forbidden_before_document_lookup(
    mode, owners, managers
):
    documents = MagicMock(get_document=AsyncMock(return_value=None))
    service = ArchiveDocumentQueryService(documents=documents)
    with pytest.raises(PartyScopeForbiddenError):
        await service.prepare_download(
            MagicMock(),
            document_id="missing",
            actor_id="actor",
            scope=EffectivePartyScope(
                user_id="actor",
                source="explicit",
                scope_mode=mode,
                owner_party_ids=owners,
                manager_party_ids=managers,
            ),
        )
    documents.get_document.assert_not_called()


@pytest.mark.parametrize(
    "document",
    [
        None,
        SimpleNamespace(
            target_type="payment_voucher",
            document_type="payment_voucher",
        ),
    ],
)
async def test_missing_or_unsupported_document_does_not_reach_files(document):
    files = MagicMock()
    service = ArchiveDocumentQueryService(
        documents=MagicMock(get_document=AsyncMock(return_value=document)), files=files
    )
    with pytest.raises(ResourceNotFoundError):
        await service.prepare_download(
            MagicMock(),
            document_id="doc",
            actor_id="actor",
            scope=EffectivePartyScope(
                user_id="actor", source="unrestricted", scope_mode="unrestricted"
            ),
        )
    files.prepare_download.assert_not_called()


async def test_list_rejects_attachment_owned_by_another_target():
    files = MagicMock(
        list=AsyncMock(
            return_value=[
                SimpleNamespace(
                    attachment=SimpleNamespace(
                        owner_type="property_certificate", owner_id="other"
                    ),
                    document=SimpleNamespace(id="doc"),
                )
            ]
        )
    )
    service = ArchiveDocumentQueryService(
        files=files,
        certificates=MagicMock(get=AsyncMock(return_value=SimpleNamespace(id="cert"))),
    )
    with pytest.raises(ResourceNotFoundError):
        await service.list_documents(
            MagicMock(),
            certificate_id="cert",
            scope=EffectivePartyScope(
                user_id="actor", source="unrestricted", scope_mode="unrestricted"
            ),
        )


@pytest.mark.parametrize("method", ["append_document", "replace_document"])
async def test_writes_reject_invalid_scope_before_files(method):
    files = MagicMock(
        append=AsyncMock(), replace=AsyncMock(), lock_for_write=AsyncMock()
    )
    service = ArchiveDocumentQueryService(files=files)
    kwargs = (
        {"certificate_id": "cert"}
        if method == "append_document"
        else {"document_id": "doc"}
    )
    with pytest.raises(PartyScopeForbiddenError):
        await getattr(service, method)(
            MagicMock(),
            **kwargs,
            file=MagicMock(),
            actor_id="a",
            scope=EffectivePartyScope(user_id="a", source="none", scope_mode="none"),
        )
    files.append.assert_not_called()
    files.replace.assert_not_called()
    files.lock_for_write.assert_not_called()


@pytest.mark.parametrize("method", ["append_document", "replace_document"])
async def test_out_of_scope_write_never_stages_or_locks(method):
    files = MagicMock(
        append=AsyncMock(), replace=AsyncMock(), lock_for_write=AsyncMock()
    )
    service = ArchiveDocumentQueryService(
        files=files,
        links=MagicMock(is_known_certificate=AsyncMock(return_value=False)),
        documents=MagicMock(
            get_document=AsyncMock(
                return_value=SimpleNamespace(
                    target_type="property_certificate",
                    document_type="property_certificate",
                    target_id="cert",
                )
            )
        ),
    )
    kwargs = (
        {"certificate_id": "cert"}
        if method == "append_document"
        else {"document_id": "doc"}
    )
    with pytest.raises(ResourceNotFoundError):
        await getattr(service, method)(
            MagicMock(),
            **kwargs,
            file=MagicMock(),
            actor_id="a",
            scope=EffectivePartyScope(
                user_id="a",
                source="explicit",
                scope_mode="owner",
                owner_party_ids=["p"],
            ),
        )
    files.append.assert_not_called()
    files.replace.assert_not_called()
    files.lock_for_write.assert_not_called()


async def test_scope_is_rechecked_after_certificate_lock_before_upload():
    links = MagicMock(is_known_certificate=AsyncMock(side_effect=[True, False]))
    files = MagicMock(append=AsyncMock(), lock_for_write=AsyncMock())
    service = ArchiveDocumentQueryService(
        files=files,
        links=links,
        certificates=MagicMock(get=AsyncMock(return_value=SimpleNamespace(id="cert"))),
    )
    with pytest.raises(ResourceNotFoundError):
        await service.append_document(
            MagicMock(),
            certificate_id="cert",
            file=MagicMock(),
            actor_id="a",
            scope=EffectivePartyScope(
                user_id="a",
                source="explicit",
                scope_mode="owner",
                owner_party_ids=["p"],
            ),
        )
    files.lock_for_write.assert_awaited_once()
    files.append.assert_not_called()


@pytest.mark.parametrize(
    "document",
    [
        None,
        SimpleNamespace(
            target_type="management_fee_statement",
            document_type="management_fee_statement",
        ),
    ],
)
async def test_missing_or_unsupported_replacement_never_locks(document):
    files = MagicMock(lock_for_write=AsyncMock(), replace=AsyncMock())
    service = ArchiveDocumentQueryService(
        files=files, documents=MagicMock(get_document=AsyncMock(return_value=document))
    )
    with pytest.raises(ResourceNotFoundError):
        await service.replace_document(
            MagicMock(),
            document_id="doc",
            actor_id="a",
            file=MagicMock(),
            scope=EffectivePartyScope(
                user_id="a", source="unrestricted", scope_mode="unrestricted"
            ),
        )
    files.lock_for_write.assert_not_called()
    files.replace.assert_not_called()
