"""Stamped files register archive versions exposed by the unified entry."""

from types import SimpleNamespace as Row
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.schemas.management_fee_commands import ManagementFeeStampRequest
from src.services.asset_operations import archive_document_query_service as query_module
from src.services.asset_operations import management_fee_stamp_service as module
from src.services.party_scope_resolver import EffectivePartyScope

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


@pytest.fixture
def bind_setup(monkeypatch):
    row = Row(
        id="st",
        owner_party_id="owner",
        version=2,
        status=None,
        stamped_document_id="old",
    )
    attachment = Row(
        id="doc",
        owner_type="management_fee_statement",
        owner_id="st",
        created_by="actor",
        created_at="2026-11-04T00:00:00",
    )
    monkeypatch.setattr(
        module.management_fee_query_service,
        "detail",
        AsyncMock(return_value=Row(statement=row, projection=Row(fee_amount="400.00"))),
    )
    monkeypatch.setattr(
        module.management_fee_statement_repository, "lock_owner", AsyncMock()
    )
    monkeypatch.setattr(
        module.management_fee_statement_repository,
        "get_statement",
        AsyncMock(return_value=row),
    )
    monkeypatch.setattr(
        module.attachment_crud, "get_for_owner", AsyncMock(return_value=attachment)
    )
    monkeypatch.setattr(module.business_change_repository, "add", AsyncMock())
    register = AsyncMock(
        return_value=Row(id="arch-1", document_version=1, replaces_document_id=None)
    )
    monkeypatch.setattr(
        module.archive_document_repository, "register_target", register
    )
    db = MagicMock(flush=AsyncMock(), commit=AsyncMock(), rollback=AsyncMock())
    return row, attachment, db, register, dict(
        statement_id="st",
        request=ManagementFeeStampRequest(document_id="doc", expected_version=2),
        actor_id="actor",
        scope=EffectivePartyScope(
            user_id="actor",
            source="explicit",
            scope_mode="owner",
            owner_party_ids=["owner"],
        ),
    )


async def test_bind_registers_archive_version_chained_to_current(
    bind_setup, monkeypatch
):
    _, attachment, db, register, kwargs = bind_setup
    monkeypatch.setattr(
        module.archive_document_repository,
        "target_rows",
        AsyncMock(
            return_value=[
                (Row(id="arch-0", document_version=1, attachment_id="older"), None)
            ]
        ),
    )
    await module.management_fee_stamp_service.bind_document(db, **kwargs)
    register.assert_awaited_once_with(
        db,
        target_type="management_fee_statement",
        target_id="st",
        document_type="management_fee_statement",
        attachment=attachment,
        replaces_document_id="arch-0",
    )


async def test_first_bind_registers_without_predecessor(bind_setup, monkeypatch):
    _, _, db, register, kwargs = bind_setup
    monkeypatch.setattr(
        module.archive_document_repository,
        "target_rows",
        AsyncMock(return_value=[]),
    )
    await module.management_fee_stamp_service.bind_document(db, **kwargs)
    assert register.await_args.kwargs["replaces_document_id"] is None


async def test_rebinding_same_attachment_does_not_register_twice(bind_setup):
    row, _, db, register, kwargs = bind_setup
    row.stamped_document_id = "doc"
    await module.management_fee_stamp_service.bind_document(db, **kwargs)
    register.assert_not_awaited()


@pytest.fixture
def query_setup(monkeypatch):
    statement = Row(id="st", owner_party_id="owner", version=3, status=None)
    scope = EffectivePartyScope(
        user_id="actor", source="explicit", scope_mode="owner", owner_party_ids=["owner"]
    )
    rows = [
        (
            Row(
                id="d2",
                document_version=2,
                replaces_document_id="d1",
                document_type="management_fee_statement",
                target_type="management_fee_statement",
                target_id="st",
                attachment_id="a2",
                uploaded_at="2026-11-04T01:00:00",
            ),
            Row(
                id="a2",
                owner_type="management_fee_statement",
                owner_id="st",
                file_name="stamp2.png",
                file_type="png",
                file_size=3,
            ),
        ),
        (
            Row(
                id="d1",
                document_version=1,
                replaces_document_id=None,
                document_type="management_fee_statement",
                target_type="management_fee_statement",
                target_id="st",
                attachment_id="a1",
                uploaded_at="2026-11-04T00:00:00",
            ),
            Row(
                id="a1",
                owner_type="management_fee_statement",
                owner_id="st",
                file_name="stamp1.png",
                file_type="png",
                file_size=3,
            ),
        ),
    ]
    monkeypatch.setattr(
        query_module.management_fee_query_service,
        "detail",
        AsyncMock(return_value=Row(statement=statement)),
    )
    target_rows = AsyncMock(return_value=rows)
    monkeypatch.setattr(
        query_module.archive_document_query_service.documents, "target_rows", target_rows
    )
    db = MagicMock()
    return db, scope, rows, target_rows


async def test_list_statement_marks_current_and_filters_history(query_setup):
    db, scope, rows, _ = query_setup
    response = await query_module.archive_document_query_service.list_statement(
        db, target_id="st", scope=scope, include_history=False
    )
    assert [item.id for item in response.items] == ["d2"]
    assert response.items[0].is_current is True
    full = await query_module.archive_document_query_service.list_statement(
        db, target_id="st", scope=scope, include_history=True
    )
    assert {item.id for item in full.items} == {"d1", "d2"}
    current = {item.id: item.is_current for item in full.items}
    assert current == {"d1": False, "d2": True}


async def test_list_statement_rejects_misowned_attachments(query_setup, monkeypatch):
    db, scope, rows, target_rows = query_setup
    rows[0][1].owner_id = "other-statement"
    with pytest.raises(query_module.ResourceNotFoundError):
        await query_module.archive_document_query_service.list_statement(
            db, target_id="st", scope=scope
        )
    target_rows.assert_awaited_once()


async def test_list_statement_hides_invisible_statements(query_setup, monkeypatch):
    db, scope, _, _ = query_setup
    monkeypatch.setattr(
        query_module.management_fee_query_service,
        "detail",
        AsyncMock(side_effect=query_module.ResourceNotFoundError(
            "ManagementFeeStatement", "st"
        )),
    )
    with pytest.raises(query_module.ResourceNotFoundError):
        await query_module.archive_document_query_service.list_statement(
            db, target_id="st", scope=scope
        )


async def test_statement_download_serves_through_statement_scope(monkeypatch):
    from types import SimpleNamespace as Row

    service = query_module.archive_document_query_service
    monkeypatch.setattr(
        service.documents,
        "get_document",
        AsyncMock(
            return_value=Row(
                id="d1",
                target_type="management_fee_statement",
                target_id="st",
                document_type="management_fee_statement",
                attachment_id="a1",
            )
        ),
    )
    attachment = Row(id="a1", owner_type="management_fee_statement", owner_id="st")
    monkeypatch.setattr(
        service,
        "statement_rows",
        AsyncMock(return_value=[(Row(id="d1", document_version=1), attachment)]),
    )
    served = AsyncMock()
    monkeypatch.setattr(service, "_serve_download", served)
    db = MagicMock()
    scope = EffectivePartyScope(
        user_id="actor", source="explicit", scope_mode="owner", owner_party_ids=["owner"]
    )
    await service.prepare_download(
        db, document_id="d1", actor_id="actor", scope=scope
    )
    served.assert_awaited_once_with(
        db,
        document_id="d1",
        attachment=attachment,
        actor_id="actor",
        resource_type="management_fee_statement",
        resource_id="st",
    )


async def test_rebinding_archived_attachment_is_rejected(bind_setup, monkeypatch):
    row, attachment, db, register, kwargs = bind_setup
    archived = Row(id="arch-old", document_version=1, attachment_id="doc")
    monkeypatch.setattr(
        module.archive_document_repository,
        "target_rows",
        AsyncMock(return_value=[(archived, attachment)]),
    )
    with pytest.raises(Exception) as caught:
        await module.management_fee_stamp_service.bind_document(db, **kwargs)
    assert caught.value.code == "ARCHIVE_DUPLICATE_CONTENT"
    register.assert_not_awaited()
    db.commit.assert_not_awaited()
