from unittest.mock import AsyncMock, MagicMock

import pytest

from src.crud.property_certificate import property_certificate_crud
from src.crud.query_builder import PartyFilter


@pytest.mark.asyncio
async def test_list_filters_authorized_certificates_by_asset_before_pagination() -> (
    None
):
    """Asset filtering narrows the authorized set without duplicating certificate rows."""
    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = []
    db = MagicMock()
    db.execute = AsyncMock(return_value=execute_result)

    await property_certificate_crud.get_multi(
        db,
        skip=20,
        limit=10,
        party_filter=PartyFilter(party_ids=["party-1"]),
        asset_id="asset-1",
    )

    stmt = db.execute.await_args.args[0]
    sql = str(stmt.compile(compile_kwargs={"literal_binds": True})).upper()

    assert sql.count("EXISTS") == 2
    assert "CERTIFICATE_PARTY_RELATIONS" in sql
    assert "PROPERTY_CERT_ASSETS" in sql
    assert " JOIN " not in sql
    assert sql.index("WHERE") < sql.index("LIMIT")
    assert stmt._offset_clause.value == 20
    assert stmt._limit_clause.value == 10


@pytest.mark.asyncio
async def test_list_eager_loads_assets_and_party_relations() -> None:
    """Response mapping must not issue lazy relationship queries per certificate."""
    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = []
    db = MagicMock()
    db.execute = AsyncMock(return_value=execute_result)

    await property_certificate_crud.get_multi(db, asset_id="asset-1")

    stmt = db.execute.await_args.args[0]
    option_paths = " ".join(str(option.path) for option in stmt._with_options)
    assert "PropertyCertificate.assets" in option_paths
    assert "PropertyCertificate.party_relations" in option_paths


@pytest.mark.asyncio
async def test_list_by_asset_ids_uses_one_unpaginated_exists_query() -> None:
    """Project risks batch-load certificates without joins or pagination drift."""
    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = []
    db = MagicMock()
    db.execute = AsyncMock(return_value=execute_result)

    await property_certificate_crud.list_by_asset_ids(
        db,
        asset_ids=["asset-1", "asset-2"],
    )

    stmt = db.execute.await_args.args[0]
    sql = str(stmt.compile(compile_kwargs={"literal_binds": True})).upper()
    option_paths = " ".join(str(option.path) for option in stmt._with_options)

    assert sql.count("EXISTS") == 1
    assert "PROPERTY_CERT_ASSETS.ASSET_ID IN ('ASSET-1', 'ASSET-2')" in sql
    assert " JOIN " not in sql
    assert stmt._limit_clause is None
    assert stmt._offset_clause is None
    assert "PropertyCertificate.assets" in option_paths
    assert "PropertyCertificate.party_relations" in option_paths


@pytest.mark.asyncio
async def test_list_by_asset_ids_skips_sql_for_empty_asset_scope() -> None:
    """An empty project asset scope must remain empty without querying all certificates."""
    db = MagicMock()
    db.execute = AsyncMock()

    result = await property_certificate_crud.list_by_asset_ids(db, asset_ids=[])

    assert result == []
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_list_orders_certificates_deterministically() -> None:
    """Paged certificate lists must not depend on unspecified database order."""
    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = []
    db = MagicMock()
    db.execute = AsyncMock(return_value=execute_result)

    await property_certificate_crud.get_multi(db, skip=0, limit=10)

    stmt = db.execute.await_args.args[0]
    sql = str(stmt.compile(compile_kwargs={"literal_binds": True})).upper()
    assert "ORDER BY PROPERTY_CERTIFICATES.ID" in sql


@pytest.mark.asyncio
async def test_get_eager_loads_assets_and_party_relations_without_party_filter() -> (
    None
):
    """Detail mapping receives the same loaded graph even for unscoped callers."""
    execute_result = MagicMock()
    execute_result.scalars.return_value.first.return_value = None
    db = MagicMock()
    db.execute = AsyncMock(return_value=execute_result)

    await property_certificate_crud.get(db, "cert-1", use_cache=False)

    stmt = db.execute.await_args.args[0]
    option_paths = " ".join(str(option.path) for option in stmt._with_options)
    assert "PropertyCertificate.assets" in option_paths
    assert "PropertyCertificate.party_relations" in option_paths
