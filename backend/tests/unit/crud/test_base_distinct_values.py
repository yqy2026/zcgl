"""Tests for CRUDBase.get_distinct_field_values()."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.exception_handler import InvalidRequestError
from src.crud.asset import asset_crud
from src.crud.query_builder import TenantFilter
from src.crud.rbac import role_crud


@pytest.fixture(autouse=True)
def clear_asset_crud_cache():
    asset_crud.clear_cache()
    yield
    asset_crud.clear_cache()


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
    async def test_distinct_values_apply_tenant_filter(self, mock_db: MagicMock):
        mock_result = MagicMock()
        mock_result.all.return_value = [("admin",)]
        mock_db.execute = AsyncMock(return_value=mock_result)

        await role_crud.get_distinct_field_values(
            mock_db,
            "name",
            tenant_filter=TenantFilter(organization_ids=["org-1"]),
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
            tenant_filter=TenantFilter(organization_ids=["org-1", "org-2"]),
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
            tenant_filter=TenantFilter(organization_ids=[]),
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
            tenant_filter=TenantFilter(organization_ids=["org-1"]),
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
            tenant_filter=TenantFilter(organization_ids=[]),
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
            tenant_filter=TenantFilter(organization_ids=["org-2"]),
        )

        stmt = mock_db.execute.await_args.args[0]
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert "roles.organization_id IN ('org-2')" in compiled
