"""Stamp uploads authorize before staging and compensate only new files."""

from io import BytesIO
from types import SimpleNamespace as Row
from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.datastructures import UploadFile

from src.services.asset_operations import management_fee_upload_service as module
from src.services.file_upload import UploadValidationError
from src.services.party_scope_resolver import EffectivePartyScope

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


@pytest.fixture
def setup(monkeypatch, tmp_path):
    statement = Row(id="st", status=None, version=2)
    monkeypatch.setattr(
        module.management_fee_query_service,
        "detail",
        AsyncMock(return_value=Row(statement=statement)),
    )
    lifecycle = MagicMock(
        stage_upload=AsyncMock(
            return_value=Row(
                original_filename="stamp.pdf",
                canonical_extension=".pdf",
                size_bytes=10,
                sha256="hash",
            )
        )
    )
    lifecycle.promote.return_value = Row(storage_key="files/new.pdf")
    monkeypatch.setattr(module, "StagedFileService", MagicMock(return_value=lifecycle))
    monkeypatch.setattr(
        module.attachment_crud, "create", AsyncMock(return_value=Row(id="doc"))
    )
    monkeypatch.setattr(
        module.management_fee_stamp_service,
        "bind_document",
        AsyncMock(return_value=Row(document_id="doc")),
    )
    db = MagicMock(rollback=AsyncMock())
    scope = EffectivePartyScope(
        user_id="actor",
        source="explicit",
        scope_mode="owner",
        owner_party_ids=["owner"],
    )
    args = dict(
        statement_id="st", file=Row(), expected_version=2, actor_id="actor", scope=scope
    )
    return (
        module.ManagementFeeUploadService(uploads_root=tmp_path),
        db,
        lifecycle,
        statement,
        args,
    )


async def test_success_preserves_old_attachment_and_commits_via_binding(setup):
    service, db, lifecycle, statement, args = setup
    result = await service.upload(db, **args)
    assert result.document_id == "doc"
    data = module.attachment_crud.create.await_args.kwargs["data"]
    assert data["owner_type"] == "management_fee_statement"
    assert data["owner_id"] == "st"
    assert data["file_hash"] == "hash"
    assert module.attachment_crud.create.await_args.kwargs["commit"] is False
    lifecycle.compensate_promotion.assert_not_called()
    lifecycle.discard_staged.assert_not_called()
    db.commit.assert_not_called()


async def test_binding_failure_compensates_new_promotion_and_rolls_back(setup):
    service, db, lifecycle, statement, args = setup
    module.management_fee_stamp_service.bind_document.side_effect = RuntimeError(
        "bind failed"
    )
    with pytest.raises(RuntimeError, match="bind failed"):
        await service.upload(db, **args)
    lifecycle.compensate_promotion.assert_called_once_with(
        lifecycle.promote.return_value
    )
    db.rollback.assert_awaited_once()


@pytest.mark.parametrize("status", ["confirmed", "superseded"])
async def test_locked_statement_rejected_before_file_staging(setup, status):
    service, db, lifecycle, statement, args = setup
    statement.status = status
    with pytest.raises(Exception) as caught:
        await service.upload(db, **args)
    assert caught.value.code == "MANAGEMENT_FEE_STATEMENT_LOCKED"
    lifecycle.stage_upload.assert_not_awaited()


async def test_foreign_actor_rejected_before_file_staging(setup):
    service, db, lifecycle, statement, args = setup
    args["actor_id"] = "intruder"
    with pytest.raises(Exception):
        await service.upload(db, **args)
    lifecycle.stage_upload.assert_not_awaited()


async def test_promotion_failure_discards_only_new_staged_file(setup):
    service, db, lifecycle, statement, args = setup
    lifecycle.promote.side_effect = RuntimeError("promotion failed")
    with pytest.raises(RuntimeError, match="promotion failed"):
        await service.upload(db, **args)
    lifecycle.discard_staged.assert_called_once_with(
        lifecycle.stage_upload.return_value
    )
    lifecycle.compensate_promotion.assert_not_called()


async def test_cleanup_failure_is_not_swallowed_and_rollback_still_runs(setup):
    service, db, lifecycle, statement, args = setup
    module.management_fee_stamp_service.bind_document.side_effect = RuntimeError(
        "bind failed"
    )
    lifecycle.compensate_promotion.side_effect = RuntimeError("cleanup failed")
    with pytest.raises(RuntimeError, match="cleanup failed") as caught:
        await service.upload(db, **args)
    assert str(caught.value.__cause__) == "bind failed"
    db.rollback.assert_awaited_once()


async def test_real_upload_profile_rejects_unsupported_file_before_metadata(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(
        module.management_fee_query_service,
        "detail",
        AsyncMock(return_value=Row(statement=Row(id="st", status=None, version=1))),
    )
    create = AsyncMock()
    monkeypatch.setattr(module.attachment_crud, "create", create)
    db = MagicMock(rollback=AsyncMock())
    scope = EffectivePartyScope(
        user_id="actor",
        source="explicit",
        scope_mode="owner",
        owner_party_ids=["owner"],
    )
    service = module.ManagementFeeUploadService(uploads_root=tmp_path)
    with pytest.raises(UploadValidationError) as caught:
        await service.upload(
            db,
            statement_id="st",
            file=UploadFile(filename="stamp.txt", file=BytesIO(b"not a stamp")),
            expected_version=1,
            actor_id="actor",
            scope=scope,
        )
    assert caught.value.details["profile"] == "management_fee_stamp"
    create.assert_not_awaited()
    assert not list(tmp_path.rglob("*"))
    db.rollback.assert_awaited_once()
