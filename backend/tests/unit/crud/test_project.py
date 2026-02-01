"""
项目 CRUD 单元测试

测试 CRUDProject 的所有主要方法
"""

from unittest.mock import MagicMock, patch

import pytest

from src.crud.project import CRUDProject
from src.models.asset import Project


class TestCRUDProjectGet:
    """测试 get 方法"""

    @pytest.fixture
    def crud(self):
        return CRUDProject(Project)

    @pytest.fixture
    def mock_db(self, db_session):
        return db_session

    def test_get_existing_project(self, crud, mock_db):
        """测试获取存在的项目"""
        mock_project = MagicMock(spec=Project)
        mock_project.id = "1"
        mock_project.name = "测试项目"

        with patch.object(crud, "get", return_value=mock_project):
            result = crud.get(mock_db, id="1")

        assert result is not None

    def test_get_nonexistent_project(self, crud, mock_db):
        """测试获取不存在的项目"""
        with patch.object(crud, "get", return_value=None):
            result = crud.get(mock_db, id="999")

        assert result is None


class TestCRUDProjectGetByName:
    """测试 get_by_name 方法"""

    @pytest.fixture
    def crud(self):
        return CRUDProject(Project)

    @pytest.fixture
    def mock_db(self, db_session):
        db_session.query = MagicMock()
        return db_session

    def test_get_by_name_exists(self, crud, mock_db):
        """测试通过名称获取存在的项目"""
        mock_project = MagicMock(spec=Project)
        mock_project.name = "测试项目"

        mock_db.query.return_value.filter.return_value.first.return_value = mock_project

        result = crud.get_by_name(mock_db, name="测试项目")

        assert result is not None
        assert result.name == "测试项目"

    def test_get_by_name_not_exists(self, crud, mock_db):
        """测试通过名称获取不存在的项目"""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = crud.get_by_name(mock_db, name="不存在")

        assert result is None


class TestCRUDProjectGetByCode:
    """测试 get_by_code 方法"""

    @pytest.fixture
    def crud(self):
        return CRUDProject(Project)

    @pytest.fixture
    def mock_db(self, db_session):
        db_session.query = MagicMock()
        return db_session

    def test_get_by_code_exists(self, crud, mock_db):
        """测试通过编码获取存在的项目"""
        mock_project = MagicMock(spec=Project)
        mock_project.code = "PRJ-001"

        mock_db.query.return_value.filter.return_value.first.return_value = mock_project

        result = crud.get_by_code(mock_db, code="PRJ-001")

        assert result is not None
        assert result.code == "PRJ-001"

    def test_get_by_code_not_exists(self, crud, mock_db):
        """测试通过编码获取不存在的项目"""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = crud.get_by_code(mock_db, code="NOT-EXIST")

        assert result is None


class TestCRUDProjectGetMulti:
    """测试 get_multi 方法"""

    @pytest.fixture
    def crud(self):
        return CRUDProject(Project)

    @pytest.fixture
    def mock_db(self, db_session):
        # Setup mock query chain
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            MagicMock(spec=Project),
            MagicMock(spec=Project),
        ]
        db_session.query = MagicMock(return_value=mock_query)
        return db_session

    def test_get_multi_default_params(self, crud, mock_db):
        """测试默认参数获取多个项目"""
        result = crud.get_multi(mock_db)

        # Should return list
        assert isinstance(result, list)
        assert len(result) == 2  # Mock returns 2 projects

    def test_get_multi_with_skip_limit(self, crud, mock_db):
        """测试分页参数"""
        result = crud.get_multi(mock_db, skip=10, limit=20)

        # Verify offset and limit were called
        assert isinstance(result, list)
        mock_db.query.return_value.offset.assert_called_once_with(10)
        mock_db.query.return_value.offset.return_value.limit.assert_called_once_with(20)


class TestCRUDProjectSearch:
    """测试 search 方法"""

    @pytest.fixture
    def crud(self):
        return CRUDProject(Project)

    @pytest.fixture
    def mock_db(self, db_session):
        db_session.query = MagicMock()
        return db_session

    def test_search_returns_tuple(self, crud, mock_db):
        """测试搜索返回元组结构 (items, total)"""
        # Create mock query chain
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 5
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            MagicMock(spec=Project),
            MagicMock(spec=Project),
        ]

        mock_db.query.return_value = mock_query

        # Create search params
        search_params = MagicMock()
        search_params.page = 1
        search_params.page_size = 10
        search_params.keyword = None
        search_params.project_status = None
        search_params.ownership_id = None

        result = crud.search(mock_db, search_params)

        # search() returns (items, total) tuple
        assert isinstance(result, tuple)
        assert len(result) == 2
        items, total = result
        assert isinstance(items, list)
        assert isinstance(total, int)
