"""Certificate links use inclusive temporal bounds and no legacy relations."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.crud.asset_unit_certificate import AssetUnitCertificateRepository

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


async def test_certificate_query_has_temporal_bounds_and_unique_objects():
    result = MagicMock()
    result.scalars.return_value.unique.return_value.all.return_value = ["certificate"]
    db = MagicMock(execute=AsyncMock(return_value=result))
    assert await AssetUnitCertificateRepository().list(
        db, unit_id="unit-a", as_of=date(2026, 11, 2)
    ) == ["certificate"]
    statement = db.execute.await_args.args[0]
    sql = str(statement.compile(compile_kwargs={"literal_binds": True}))
    assert "property_certificate_asset_units.asset_unit_id = 'unit-a'" in sql
    assert "effective_from <= '2026-11-02'" in sql
    assert "effective_to IS NULL" in sql
    assert "effective_to >= '2026-11-02'" in sql
    assert "property_cert_assets" not in sql
    assert "certificate_party_relations" not in sql


async def test_find_link_returns_the_single_row_for_the_pair():
    link = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = link
    db = MagicMock(execute=AsyncMock(return_value=result))
    assert (
        await AssetUnitCertificateRepository().find_link(
            db, unit_id="unit-a", certificate_id="cert-1"
        )
        is link
    )
    sql = str(
        db.execute.await_args.args[0].compile(compile_kwargs={"literal_binds": True})
    )
    assert "asset_unit_id = 'unit-a'" in sql
    assert "certificate_id = 'cert-1'" in sql


async def test_find_active_returns_row_covering_the_requested_date():
    link = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = link
    db = MagicMock(execute=AsyncMock(return_value=result))
    assert (
        await AssetUnitCertificateRepository().find_active(
            db, unit_id="unit-a", certificate_id="cert-1", on=date(2026, 3, 1)
        )
        is link
    )
    sql = str(
        db.execute.await_args.args[0].compile(compile_kwargs={"literal_binds": True})
    )
    assert "effective_from <= '2026-03-01'" in sql
    assert "effective_to IS NULL" in sql
    assert "effective_to >= '2026-03-01'" in sql


async def test_add_flushes_new_link_row():
    db = MagicMock(flush=AsyncMock())
    document = await AssetUnitCertificateRepository().add(
        db,
        unit_id="unit-a",
        certificate_id="cert-1",
        effective_from=date(2026, 1, 1),
        effective_to=None,
    )
    db.add.assert_called_once_with(document)
    db.flush.assert_awaited_once()
    assert document.asset_unit_id == "unit-a"
    assert document.certificate_id == "cert-1"
    assert document.effective_from == date(2026, 1, 1)
    assert document.effective_to is None


async def test_close_interval_updates_end_and_flushes():
    link = MagicMock(effective_from=date(2026, 1, 1), effective_to=None)
    db = MagicMock(flush=AsyncMock())
    await AssetUnitCertificateRepository().close_interval(
        db, link=link, effective_to=date(2026, 10, 31)
    )
    assert link.effective_to == date(2026, 10, 31)
    db.flush.assert_awaited_once()


async def test_remove_flushes_deletion():
    link = MagicMock()
    db = MagicMock(flush=AsyncMock(), delete=AsyncMock())
    await AssetUnitCertificateRepository().remove(db, link=link)
    db.delete.assert_called_once_with(link)
    db.flush.assert_awaited_once()


async def test_certificate_delete_guard_checks_all_historical_links():
    result = MagicMock()
    result.scalar_one.return_value = True
    db = MagicMock(execute=AsyncMock(return_value=result))
    assert await AssetUnitCertificateRepository().has_links_for_certificate(
        db, certificate_id="cert-1"
    )
    statement = str(
        db.execute.await_args.args[0].compile(compile_kwargs={"literal_binds": True})
    )
    assert "certificate_id = 'cert-1'" in statement
    assert "effective_from" not in statement
    assert "effective_to" not in statement


async def test_target_visibility_uses_current_scoped_unit_links():
    from src.services.party_scope_resolver import EffectivePartyScope

    result = MagicMock()
    result.scalar_one_or_none.return_value = "unit-a"
    db = MagicMock(execute=AsyncMock(return_value=result))
    assert await AssetUnitCertificateRepository().is_known_certificate(
        db,
        certificate_id="cert-1",
        scope=EffectivePartyScope(
            user_id="actor",
            source="explicit",
            scope_mode="owner",
            owner_party_ids=["owner"],
        ),
        as_of=date(2026, 11, 2),
    )
    sql = str(
        db.execute.await_args.args[0].compile(compile_kwargs={"literal_binds": True})
    )
    assert "owner_party_id IN ('owner')" in sql
    assert "effective_from <= '2026-11-02'" in sql
    assert "effective_to" not in sql
    assert "property_certificates" not in sql


async def test_current_holder_uses_owner_roles_and_full_timestamp():
    from datetime import datetime

    result = MagicMock()
    result.scalar_one.return_value = True
    db = MagicMock(execute=AsyncMock(return_value=result))
    assert await AssetUnitCertificateRepository().has_current_holder(
        db, certificate_id="cert", party_id="locked-owner", at=datetime(2026, 11, 2, 12)
    )
    sql = str(
        db.execute.await_args.args[0].compile(compile_kwargs={"literal_binds": True})
    )
    assert "party_id = 'locked-owner'" in sql
    assert "relation_role IN ('owner', 'co_owner')" in sql
    assert "valid_from <= '2026-11-02 12:00:00'" in sql
    assert "valid_to >= '2026-11-02 12:00:00'" in sql
