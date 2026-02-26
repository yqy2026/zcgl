"""Tests for CRUDBase.get_distinct_field_values()."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.exception_handler import InvalidRequestError
from src.crud.asset import asset_crud
from src.crud.query_builder import PartyFilter
from src.crud.rbac import role_crud


@pytest.fixture(autouse=True)
def clear_asset_crud_cache():
    asset_crud.clear_cache()
    role_crud.clear_cache()
    yield
    asset_crud.clear_cache()
    role_crud.clear_cache()


class TestGetDistinctFieldValues:
    """Test suite for CRUDBase.get_distinct_field_values()."""

    @pytest.mark.asyncio
    async def test_invalid_field_name(self, mock_db: MagicMock):
        with pytest.raises(AttributeError, match="does not exist on model"):
            await asset_crud.get_distinct_field_values(mock_db, "nonexistent_field")

    @pytest.mark.asyncio
    async def test_invalid_sort_order(self, mock_db: MagicMock):
        with pytest.raises(InvalidRequestError, match="sort_order must be"):
            await asset_crud.get_distinct_field_values(
                mock_db,
                "ownership_id",
                sort_order="invalid",
            )

    @pytest.mark.asyncio
    async def test_query_execution_and_result_mapping(self, mock_db: MagicMock):
        mock_result = MagicMock()
        mock_result.all.return_value = [("value1",), ("value2",)]
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await asset_crud.get_distinct_field_values(
            mock_db,
            "ownership_id",
            sort_order="asc",
            use_cache=False,
            exclude_empty=True,
        )

        assert result == ["value1", "value2"]
        mock_db.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_query_with_filters(self, mock_db: MagicMock):
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        await asset_crud.get_distinct_field_values(
            mock_db,
            "ownership_id",
            filters={"is_active": True},
            use_cache=False,
        )

        mock_db.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_descending_sort_generates_desc_statement(self, mock_db: MagicMock):
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        await asset_crud.get_distinct_field_values(
            mock_db,
            "ownership_id",
            sort_order="desc",
            use_cache=False,
        )

        stmt = mock_db.execute.await_args.args[0]
        assert "DESC" in str(stmt)

    @pytest.mark.asyncio
    async def test_exclude_empty_false_still_executes(self, mock_db: MagicMock):
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        await asset_crud.get_distinct_field_values(
            mock_db,
            "ownership_id",
            exclude_empty=False,
            use_cache=False,
        )

        mock_db.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_caching_mechanism(self, mock_db: MagicMock):
        mock_result = MagicMock()
        mock_result.all.return_value = [("value1",)]
        mock_db.execute = AsyncMock(return_value=mock_result)

        result1 = await asset_crud.get_distinct_field_values(
            mock_db,
            "ownership_id",
            use_cache=True,
        )
        result2 = await asset_crud.get_distinct_field_values(
            mock_db,
            "ownership_id",
            use_cache=True,
        )

        assert result1 == result2 == ["value1"]
        mock_db.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_caching_is_isolated_by_tenant_filter(self, mock_db: MagicMock):
        mock_result_org_1 = MagicMock()
        mock_result_org_1.all.return_value = [("org-1-role",)]
        mock_result_org_2 = MagicMock()
        mock_result_org_2.all.return_value = [("org-2-role",)]
        mock_db.execute = AsyncMock(side_effect=[mock_result_org_1, mock_result_org_2])

        result_org_1 = await role_crud.get_distinct_field_values(
            mock_db,
            "name",
            party_filter=PartyFilter(party_ids=["org-1"]),
            use_cache=True,
        )
        result_org_2 = await role_crud.get_distinct_field_values(
            mock_db,
            "name",
            party_filter=PartyFilter(party_ids=["org-2"]),
            use_cache=True,
        )

        assert result_org_1 == ["org-1-role"]
        assert result_org_2 == ["org-2-role"]
        assert mock_db.execute.await_count == 2

    @pytest.mark.asyncio
    async def test_empty_values_filtered(self, mock_db: MagicMock):
        mock_result = MagicMock()
        mock_result.all.return_value = [
            ("value1",),
            ("value2",),
            (None,),
            ("",),
            ("value3",),
        ]
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await asset_crud.get_distinct_field_values(
            mock_db,
            "ownership_id",
            use_cache=False,
        )

        assert result == ["value1", "value2", "value3"]

    @pytest.mark.asyncio
    async def test_distinct_values_apply_party_filter(self, mock_db: MagicMock):
        mock_result = MagicMock()
        mock_result.all.return_value = [("admin",)]
        mock_db.execute = AsyncMock(return_value=mock_result)

        await role_crud.get_distinct_field_values(
            mock_db,
            "name",
            party_filter=PartyFilter(party_ids=["org-1"]),
            use_cache=False,
        )

        stmt = mock_db.execute.await_args.args[0]
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert "roles.organization_id IN ('org-1')" in compiled


class TestCountWithTenantFilter:
    @pytest.mark.asyncio
    async def test_count_applies_tenant_filter(self, mock_db: MagicMock):
        mock_result = MagicMock()
        mock_result.scalar.return_value = 3
        mock_db.execute = AsyncMock(return_value=mock_result)

        total = await role_crud.count(
            mock_db,
            party_filter=PartyFilter(party_ids=["org-1", "org-2"]),
        )

        assert total == 3
        stmt = mock_db.execute.await_args.args[0]
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert "roles.organization_id IN ('org-1', 'org-2')" in compiled

    @pytest.mark.asyncio
    async def test_count_fail_closed_when_tenant_filter_empty(self, mock_db: MagicMock):
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_db.execute = AsyncMock(return_value=mock_result)

        total = await role_crud.count(
            mock_db,
            party_filter=PartyFilter(party_ids=[]),
        )

        assert total == 0
        stmt = mock_db.execute.await_args.args[0]
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert "false" in compiled.lower() or "0 = 1" in compiled


class TestGetAndGetMultiWithTenantFilter:
    @pytest.mark.asyncio
    async def test_get_applies_tenant_filter(self, mock_db: MagicMock):
        role_crud.clear_cache()
        mock_role = MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_role
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await role_crud.get(
            mock_db,
            id="role-1",
            use_cache=False,
            party_filter=PartyFilter(party_ids=["org-1"]),
        )

        assert result is mock_role
        stmt = mock_db.execute.await_args.args[0]
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert "roles.id = 'role-1'" in compiled
        assert "roles.organization_id IN ('org-1')" in compiled

    @pytest.mark.asyncio
    async def test_get_fail_closed_when_tenant_filter_empty(self, mock_db: MagicMock):
        role_crud.clear_cache()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await role_crud.get(
            mock_db,
            id="role-1",
            use_cache=False,
            party_filter=PartyFilter(party_ids=[]),
        )

        assert result is None
        stmt = mock_db.execute.await_args.args[0]
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert "false" in compiled.lower() or "0 = 1" in compiled

    @pytest.mark.asyncio
    async def test_get_multi_applies_tenant_filter(self, mock_db: MagicMock):
        role_crud.clear_cache()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        _ = await role_crud.get_multi(
            mock_db,
            skip=0,
            limit=20,
            use_cache=False,
            party_filter=PartyFilter(party_ids=["org-2"]),
        )

        stmt = mock_db.execute.await_args.args[0]
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert "roles.organization_id IN ('org-2')" in compiled


class TestCacheInvalidationWithTenantFilter:
    @pytest.mark.asyncio
    async def test_remove_clears_tenant_scoped_get_cache(self, mock_db: MagicMock):
        party_filter = PartyFilter(party_ids=["org-1"])
        cache_key = role_crud._get_cache_key(
            "get",
            id="role-1",
            party_filter=role_crud._serialize_party_filter(party_filter),
        )
        role_crud._set_cache(cache_key, MagicMock())

        mock_db.get = AsyncMock(return_value=SimpleNamespace(id="role-1"))
        mock_db.delete = AsyncMock()
        mock_db.commit = AsyncMock()

        await role_crud.remove(mock_db, id="role-1")

        assert cache_key not in role_crud._cache

    @pytest.mark.asyncio
    async def test_update_clears_tenant_scoped_get_cache(self, mock_db: MagicMock):
        party_filter = PartyFilter(party_ids=["org-1"])
        cache_key = role_crud._get_cache_key(
            "get",
            id="role-1",
            party_filter=role_crud._serialize_party_filter(party_filter),
        )
        role_crud._set_cache(cache_key, MagicMock())

        role = SimpleNamespace(id="role-1", name="old-role", organization_id="org-1")
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        updated = await role_crud.update(
            mock_db,
            db_obj=role,
            obj_in={"name": "new-role"},
        )

        assert updated.name == "new-role"
        assert cache_key not in role_crud._cache


class TestCacheKeyStability:
    def test_cache_key_stable_for_nested_filter_order(self):
        key1 = role_crud._get_cache_key(
            "distinct_values",
            filters={
                "status": "active",
                "metadata": {"b": 2, "a": 1},
            },
        )
        key2 = role_crud._get_cache_key(
            "distinct_values",
            filters={
                "metadata": {"a": 1, "b": 2},
                "status": "active",
            },
        )

        assert key1 == key2

    def test_cache_key_distinguishes_string_and_numeric_ids(self):
        numeric_key = role_crud._get_cache_key("get", id=1)
        string_key = role_crud._get_cache_key("get", id="1")

        assert numeric_key != string_key

    def test_cache_key_distinguishes_relation_aware_owner_manager_scopes(self):
        shared_party_ids = ["org-a", "org-b"]
        owner_first_filter = PartyFilter(
            party_ids=shared_party_ids,
            owner_party_ids=["org-a"],
            manager_party_ids=["org-b"],
        )
        manager_first_filter = PartyFilter(
            party_ids=shared_party_ids,
            owner_party_ids=["org-b"],
            manager_party_ids=["org-a"],
        )

        owner_first_key = role_crud._get_cache_key(
            "get_multi",
            skip=0,
            limit=20,
            party_filter=role_crud._serialize_party_filter(owner_first_filter),
        )
        manager_first_key = role_crud._get_cache_key(
            "get_multi",
            skip=0,
            limit=20,
            party_filter=role_crud._serialize_party_filter(manager_first_filter),
        )

        assert owner_first_key != manager_first_key

    def test_cache_key_distinguishes_none_and_empty_relation_scopes(self):
        legacy_filter = PartyFilter(
            party_ids=["org-a"],
            owner_party_ids=None,
            manager_party_ids=None,
        )
        relation_aware_empty_filter = PartyFilter(
            party_ids=["org-a"],
            owner_party_ids=[],
            manager_party_ids=[],
        )

        legacy_key = role_crud._get_cache_key(
            "get_multi",
            skip=0,
            limit=20,
            party_filter=role_crud._serialize_party_filter(legacy_filter),
        )
        relation_aware_empty_key = role_crud._get_cache_key(
            "get_multi",
            skip=0,
            limit=20,
            party_filter=role_crud._serialize_party_filter(
                relation_aware_empty_filter
            ),
        )

        assert legacy_key != relation_aware_empty_key
