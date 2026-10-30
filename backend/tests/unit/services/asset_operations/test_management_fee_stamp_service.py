"""Stamped attachment binding respects scope, ownership and locked snapshots."""

from types import SimpleNamespace as Row
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.schemas.management_fee_commands import ManagementFeeStampRequest
from src.services.asset_operations import management_fee_stamp_service as module
from src.services.party_scope_resolver import EffectivePartyScope

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


@pytest.fixture
def setup(monkeypatch):
    row = Row(
        id="st",
        owner_party_id="owner",
        version=2,
        status=None,
        stamped_document_id="old",
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
        module.attachment_crud, "get_for_owner", AsyncMock(return_value=Row(id="doc"))
    )
    monkeypatch.setattr(module.business_change_repository, "add", AsyncMock())
    db = MagicMock(flush=AsyncMock(), commit=AsyncMock(), rollback=AsyncMock())
    return (
        row,
        db,
        dict(
            statement_id="st",
            request=ManagementFeeStampRequest(document_id="doc", expected_version=2),
            actor_id="actor",
            scope=EffectivePartyScope(
                user_id="actor",
                source="explicit",
                scope_mode="owner",
                owner_party_ids=["owner"],
            ),
        ),
    )


async def test_stamp_replacement_updates_version_and_audit_atomically(setup):
    row, db, kwargs = setup
    result = await module.management_fee_stamp_service.bind_document(db, **kwargs)
    assert row.stamped_document_id == "doc"
    assert row.version == result.version == 3
    assert result.document_id == "doc"
    assert str(result.fee_amount) == "400.00"
    module.attachment_crud.get_for_owner.assert_awaited_once_with(
        db, attachment_id="doc", owner_type="management_fee_statement", owner_id="st"
    )
    module.business_change_repository.add.assert_awaited_once()
    db.commit.assert_awaited_once()


@pytest.mark.parametrize("status", ["confirmed", "superseded"])
async def test_locked_statement_rejects_stamp_replacement(setup, status):
    row, db, kwargs = setup
    row.status = status
    with pytest.raises(Exception) as caught:
        await module.management_fee_stamp_service.bind_document(db, **kwargs)
    assert caught.value.code == "MANAGEMENT_FEE_STATEMENT_LOCKED"
    assert row.stamped_document_id == "old"
    db.rollback.assert_awaited_once()


async def test_foreign_attachment_is_not_bound(setup):
    row, db, kwargs = setup
    module.attachment_crud.get_for_owner.return_value = None
    with pytest.raises(module.ResourceNotFoundError):
        await module.management_fee_stamp_service.bind_document(db, **kwargs)
    assert row.stamped_document_id == "old"
    db.commit.assert_not_awaited()


async def test_audit_failure_rolls_back_stamp_change(setup):
    row, db, kwargs = setup
    module.business_change_repository.add.side_effect = RuntimeError(
        "audit unavailable"
    )
    with pytest.raises(RuntimeError):
        await module.management_fee_stamp_service.bind_document(db, **kwargs)
    db.rollback.assert_awaited_once()
    db.commit.assert_not_awaited()


async def test_stale_version_does_not_replace_document(setup):
    row, db, kwargs = setup
    row.version = 4
    with pytest.raises(module.AssetOperationsVersionConflictError):
        await module.management_fee_stamp_service.bind_document(db, **kwargs)
    assert row.stamped_document_id == "old"
    module.attachment_crud.get_for_owner.assert_not_awaited()


async def test_statement_owned_attachment_passes_database_check():
    from sqlalchemy import create_engine, insert
    from sqlalchemy.exc import IntegrityError

    from src.models.attachment import Attachment

    engine = create_engine("sqlite://")
    table = Attachment.__table__
    table.create(engine)
    data = dict(
        id="doc",
        owner_type="management_fee_statement",
        owner_id="st",
        file_name="盖章.pdf",
        file_type="pdf",
        file_size=10,
        storage_key="fee/doc.pdf",
        created_by="actor",
    )
    with engine.begin() as conn:
        conn.execute(insert(table).values(**data))
        with pytest.raises(IntegrityError):
            conn.execute(
                insert(table).values(
                    **{
                        **data,
                        "id": "bad",
                        "storage_key": "bad",
                        "owner_type": "unknown",
                    }
                )
            )


async def test_attachment_migration_matches_model_owner_check(monkeypatch):
    from importlib.util import module_from_spec, spec_from_file_location
    from pathlib import Path

    from sqlalchemy import CheckConstraint

    from src.models.attachment import Attachment

    path = (
        Path(__file__).resolve().parents[4]
        / "alembic/versions/20261029_fee_attachments.py"
    )
    spec = spec_from_file_location("fee_attachment_migration", path)
    migration = module_from_spec(spec)
    spec.loader.exec_module(migration)
    operations = MagicMock()
    monkeypatch.setattr(migration, "op", operations)
    migration.upgrade()
    expected = next(
        str(item.sqltext)
        for item in Attachment.__table__.constraints
        if isinstance(item, CheckConstraint) and item.name == "ck_attachment_owner_type"
    )
    operations.create_check_constraint.assert_called_once_with(
        "ck_attachment_owner_type", "attachments", expected
    )
    assert migration.down_revision == "20261029_fee_deferrals"
    assert len(migration.revision) <= 32
    with pytest.raises(RuntimeError, match="append-only"):
        migration.downgrade()
