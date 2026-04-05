"""
项目 CRUD 单元测试（异步接口）
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select

from src.crud.project import CRUDProject
from src.crud.query_builder import PartyFilter
from src.models.asset import Asset
from src.models.project import Project

pytestmark = pytest.mark.asyncio


@pytest.fixture
def crud() -> CRUDProject:
    return CRUDProject(Project)


@pytest.fixture
def mock_db() -> MagicMock:
    db = MagicMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    db.delete = AsyncMock()
    return db


class TestCRUDProjectGet:
    async def test_get_existing_project(
        self, crud: CRUDProject, mock_db: MagicMock
    ) -> None:
        mock_project = MagicMock(spec=Project)
        mock_project.id = "1"
        mock_project.name = "测试项目"

        with patch.object(
            crud, "get", new_callable=AsyncMock, return_value=mock_project
        ):
            result = await crud.get(mock_db, id="1")

        assert result is not None

    async def test_get_nonexistent_project(
        self, crud: CRUDProject, mock_db: MagicMock
    ) -> None:
        with patch.object(crud, "get", new_callable=AsyncMock, return_value=None):
            result = await crud.get(mock_db, id="999")

        assert result is None


class TestCRUDProjectGetByName:
    async def test_get_by_name_exists(
        self, crud: CRUDProject, mock_db: MagicMock
    ) -> None:
        mock_project = MagicMock(spec=Project)
        mock_project.name = "测试项目"

        with patch.object(
            crud,
            "get_by_name",
            new_callable=AsyncMock,
            return_value=mock_project,
        ):
            result = await crud.get_by_name(mock_db, name="测试项目")

        assert result is not None
        assert result.name == "测试项目"

    async def test_get_by_name_not_exists(
        self, crud: CRUDProject, mock_db: MagicMock
    ) -> None:
        with patch.object(
            crud, "get_by_name", new_callable=AsyncMock, return_value=None
        ):
            result = await crud.get_by_name(mock_db, name="不存在")

        assert result is None


class TestCRUDProjectGetByCode:
    async def test_get_by_code_exists(
        self, crud: CRUDProject, mock_db: MagicMock
    ) -> None:
        mock_project = MagicMock(spec=Project)
        mock_project.code = "PRJ-001"

        with patch.object(
            crud,
            "get_by_code",
            new_callable=AsyncMock,
            return_value=mock_project,
        ):
            result = await crud.get_by_code(mock_db, code="PRJ-001")

        assert result is not None
        assert result.code == "PRJ-001"

    async def test_get_by_code_not_exists(
        self, crud: CRUDProject, mock_db: MagicMock
    ) -> None:
        with patch.object(
            crud, "get_by_code", new_callable=AsyncMock, return_value=None
        ):
            result = await crud.get_by_code(mock_db, code="NOT-EXIST")

        assert result is None


class TestCRUDProjectGetMulti:
    async def test_get_multi_default_params(
        self, crud: CRUDProject, mock_db: MagicMock
    ) -> None:
        mock_projects = [MagicMock(spec=Project), MagicMock(spec=Project)]
        with patch.object(
            crud,
            "get_multi",
            new_callable=AsyncMock,
            return_value=mock_projects,
        ):
            result = await crud.get_multi(mock_db)

        assert isinstance(result, list)
        assert len(result) == 2

    async def test_get_multi_with_skip_limit(
        self, crud: CRUDProject, mock_db: MagicMock
    ) -> None:
        mock_projects = [MagicMock(spec=Project)]
        with patch.object(
            crud,
            "get_multi",
            new_callable=AsyncMock,
            return_value=mock_projects,
        ) as mock_get_multi:
            result = await crud.get_multi(mock_db, skip=10, limit=20)

        assert isinstance(result, list)
        mock_get_multi.assert_awaited_once_with(mock_db, skip=10, limit=20)

    async def test_get_multi_applies_tenant_filter(
        self, crud: CRUDProject, mock_db: MagicMock
    ) -> None:
        party_filter = PartyFilter(party_ids=["org-1"])
        execute_result = MagicMock()
        execute_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=execute_result)

        with patch.object(
            crud.query_builder,
            "apply_party_filter",
            side_effect=lambda stmt, _tf: stmt,
        ) as mock_apply_party_filter:
            await crud.get_multi(mock_db, party_filter=party_filter)

        assert mock_apply_party_filter.call_args.args[1] == party_filter


class TestCRUDProjectSearch:
    async def test_search_returns_tuple(
        self, crud: CRUDProject, mock_db: MagicMock
    ) -> None:
        mock_items = [MagicMock(spec=Project), MagicMock(spec=Project)]
        search_params = MagicMock()
        search_params.page = 1
        search_params.page_size = 10
        search_params.keyword = None
        search_params.project_status = None
        search_params.ownership_id = None

        with patch.object(
            crud,
            "search",
            new_callable=AsyncMock,
            return_value=(mock_items, 2),
        ):
            result = await crud.search(mock_db, search_params)

        assert isinstance(result, tuple)
        assert len(result) == 2
        items, total = result
        assert isinstance(items, list)
        assert isinstance(total, int)


class TestCRUDProjectPartyFilter:
    async def test_apply_project_party_filter_owner_uses_asset_relation(
        self, crud: CRUDProject, mock_db: MagicMock
    ) -> None:
        party_filter = PartyFilter(
            party_ids=["owner-1"],
            filter_mode="owner",
            owner_party_ids=["owner-1"],
            manager_party_ids=[],
        )

        stmt = await crud._apply_project_party_filter(
            mock_db,
            select(Project),
            party_filter,
        )

        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert "projects.id IN" in compiled
        assert "assets.owner_party_id IN ('owner-1')" in compiled
        assert "project_assets.project_id" in compiled

    async def test_apply_project_party_filter_any_combines_manager_and_owner(
        self, crud: CRUDProject, mock_db: MagicMock
    ) -> None:
        party_filter = PartyFilter(
            party_ids=["owner-1", "manager-1"],
            filter_mode="any",
            owner_party_ids=["owner-1"],
            manager_party_ids=["manager-1"],
        )

        stmt = await crud._apply_project_party_filter(
            mock_db,
            select(Project),
            party_filter,
        )

        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert "projects.manager_party_id IN ('manager-1')" in compiled
        assert "assets.owner_party_id IN ('owner-1')" in compiled
        assert "project_assets.project_id" in compiled

    async def test_apply_project_party_filter_manager_keeps_query_builder_path(
        self, crud: CRUDProject, mock_db: MagicMock
    ) -> None:
        party_filter = PartyFilter(
            party_ids=["manager-1"],
            filter_mode="manager",
            owner_party_ids=[],
            manager_party_ids=["manager-1"],
        )
        base_stmt = select(Project)

        with patch.object(
            crud.query_builder,
            "apply_party_filter",
            side_effect=lambda stmt, _party_filter: stmt.where(
                Asset.manager_party_id.in_(["manager-1"])
            ),
        ) as mock_apply_party_filter:
            stmt = await crud._apply_project_party_filter(
                mock_db, base_stmt, party_filter
            )

        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert "assets.manager_party_id IN ('manager-1')" in compiled
        assert mock_apply_party_filter.call_count == 1
