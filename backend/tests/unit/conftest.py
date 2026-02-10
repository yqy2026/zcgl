"""
Unit test configuration and fixtures
"""

import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
if TEST_DATABASE_URL:
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL


class AsyncSessionAdapter:
    """Provide async-compatible methods over a sync SQLAlchemy session."""

    def __init__(self, session):  # noqa: ANN001 - test helper
        self._session = session

    async def execute(self, *args, **kwargs):  # noqa: ANN001
        return self._session.execute(*args, **kwargs)

    async def commit(self):  # noqa: D401 - test helper
        return self._session.commit()

    async def refresh(self, *args, **kwargs):  # noqa: ANN001
        return self._session.refresh(*args, **kwargs)

    async def flush(self):  # noqa: D401 - test helper
        return self._session.flush()

    async def rollback(self):  # noqa: D401 - test helper
        return self._session.rollback()

    async def get(self, *args, **kwargs):  # noqa: ANN001
        return self._session.get(*args, **kwargs)

    def add(self, *args, **kwargs):  # noqa: ANN001
        return self._session.add(*args, **kwargs)

    async def delete(self, *args, **kwargs):  # noqa: ANN001
        return self._session.delete(*args, **kwargs)

    def __getattr__(self, name: str):  # noqa: D401 - test helper
        return getattr(self._session, name)


@pytest.fixture(scope="session")
def test_database_url():
    """Provide the test database URL for unit tests."""
    if TEST_DATABASE_URL:
        os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    return TEST_DATABASE_URL


@pytest.fixture(scope="session")
def engine(test_database_url):
    """Create database engine for unit tests."""
    if not test_database_url:
        pytest.skip(
            "TEST_DATABASE_URL is required for db-backed unit tests",
            allow_module_level=True,
        )

    connect_args: dict[str, int] = {}
    if test_database_url.startswith("postgresql"):
        connect_args["connect_timeout"] = 3

    engine = create_engine(
        test_database_url,
        pool_pre_ping=True,
        connect_args=connect_args,
    )

    try:
        with engine.connect():
            pass
    except OperationalError as exc:
        engine.dispose()
        pytest.skip(
            f"TEST_DATABASE_URL unreachable for unit db fixtures: {exc}",
            allow_module_level=True,
        )

    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def db_tables(engine):
    """Create database tables using Alembic migrations when available."""
    import importlib

    from alembic.config import Config

    from src.database import Base

    versions_dir = Path("alembic/versions")
    has_migrations = versions_dir.exists() and len(list(versions_dir.glob("*.py"))) > 0

    if has_migrations:
        from alembic import command

        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
        try:
            command.upgrade(alembic_cfg, "head")
        except OperationalError as exc:
            pytest.skip(
                f"TEST_DATABASE_URL unreachable during Alembic upgrade: {exc}",
                allow_module_level=True,
            )

    importlib.import_module("src.models")
    try:
        Base.metadata.create_all(bind=engine)
    except OperationalError as exc:
        pytest.skip(
            f"TEST_DATABASE_URL unreachable during table setup: {exc}",
            allow_module_level=True,
        )

    yield

    try:
        Base.metadata.drop_all(bind=engine)
    except Exception:
        pass


@pytest.fixture(scope="function")
def db_session(engine, db_tables):
    """Create a new database session for each unit test."""
    test_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = test_session_local()

    connection = engine.connect()
    transaction = connection.begin()
    session.bind = connection

    yield session

    try:
        session.close()
        transaction.rollback()
        connection.close()
    except Exception:
        pass


@pytest.fixture(scope="function")
def test_db(db_session):
    """Alias fixture for tests still expecting test_db."""
    return db_session


@pytest.fixture
def mock_db():
    db = MagicMock()
    query = MagicMock()
    query.filter.return_value = query
    query.first.return_value = None
    query.all.return_value = []
    query.count.return_value = 0
    db.query.return_value = query
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.delete = AsyncMock()
    db.flush = AsyncMock()
    db.rollback = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture(autouse=True)
def mock_enum_validation_service(request):
    """
    自动 mock AsyncEnumValidationService 用于所有测试

    这个 fixture 会自动应用到所有测试，避免在每个测试中单独 mock。
    它返回常见枚举值，使测试可以正常通过验证。

    跳过 TestConvenienceFunctions 测试类，该类需要测试真实的便捷函数。
    """
    # Skip mocking for TestConvenienceFunctions tests
    if request.node.parent and "TestConvenienceFunctions" in request.node.parent.name:
        yield None
        return

    mock_service = MagicMock()

    # Mock get_valid_values 方法返回常见枚举值
    def mock_get_valid_values(enum_type_code: str) -> list[str]:
        # 定义常见的枚举值映射
        enum_values = {
            # 资产相关枚举
            "ownership_status": ["已确权", "未确权", "确权中"],
            "property_nature": ["商业", "住宅", "工业", "办公", "综合"],
            "usage_status": ["在租", "空置", "自用", "装修中"],
            "data_status": ["正常", "冻结", "已删除"],
            "business_model": ["自持", "租赁", "混合"],
            "operation_status": ["运营中", "停业", "筹备中"],
            "tenant_type": ["企业", "个人", "政府", "事业单位"],
            "business_category": ["零售", "餐饮", "办公", "仓储"],
            # 角色权限相关枚举
            "role_type": ["系统角色", "自定义角色"],
            "permission_type": ["菜单权限", "按钮权限", "数据权限"],
        }
        return enum_values.get(enum_type_code, ["test_value"])

    mock_service.get_valid_values = AsyncMock(side_effect=mock_get_valid_values)
    mock_service.validate_value = AsyncMock(return_value=(True, None))
    mock_service.validate_asset_data = AsyncMock(return_value=(True, []))

    with patch(
        "src.services.enum_validation_service.AsyncEnumValidationService",
        return_value=mock_service,
    ):
        with patch(
            "src.services.enum_validation_service.get_enum_validation_service_async",
            return_value=mock_service,
        ):
            yield mock_service


@pytest.fixture
def client(monkeypatch, db_session):
    """Create a test client for unit tests with authentication bypassed"""
    from src.database import get_async_db
    from src.main import app
    from src.middleware import auth as auth_module
    from src.middleware.auth import (
        get_current_active_user,
        get_current_user,
        get_current_user_from_cookie,
        require_admin,
        require_permission,
    )

    # Mock authenticated user
    mock_user = MagicMock()
    mock_user.id = "test_user_001"
    mock_user.username = "testuser"
    mock_user.email = "test@example.com"
    mock_user.role_id = "role-admin-id"
    mock_user.role_name = "admin"
    mock_user.roles = ["admin"]
    mock_user.role_ids = ["role-admin-id"]
    mock_user.is_admin = True
    mock_user.is_active = True

    # Use monkeypatch to replace functions at module level
    def mock_get_current_user():
        return mock_user

    def mock_require_permission(resource, action):
        def dependency():
            return mock_user

        return dependency

    monkeypatch.setattr(auth_module, "get_current_active_user", mock_get_current_user)
    monkeypatch.setattr(auth_module, "get_current_user", mock_get_current_user)
    monkeypatch.setattr(
        auth_module, "get_current_user_from_cookie", mock_get_current_user
    )
    monkeypatch.setattr(auth_module, "require_permission", mock_require_permission)

    # Override dependencies in FastAPI app
    app.dependency_overrides[get_current_active_user] = mock_get_current_user
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_current_user_from_cookie] = mock_get_current_user
    app.dependency_overrides[require_permission] = mock_require_permission
    app.dependency_overrides[require_admin] = mock_get_current_user

    # Override RBAC permission checkers created at route import time
    def mock_rbac_checker():  # noqa: ANN001 - test stub
        return mock_user

    def apply_rbac_overrides(dependant):
        for sub in getattr(dependant, "dependencies", []):
            if type(sub.call).__name__ == "RBACPermissionChecker":
                app.dependency_overrides[sub.call] = mock_rbac_checker
            apply_rbac_overrides(sub)

    for route in app.router.routes:
        dependant = getattr(route, "dependant", None)
        if dependant:
            apply_rbac_overrides(dependant)

    # Use real database session
    async def override_get_db():
        yield AsyncSessionAdapter(db_session)

    app.dependency_overrides[get_async_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture
def admin_user():
    """Mock admin user for testing admin-only endpoints"""
    mock_user = MagicMock()
    mock_user.id = "admin_001"
    mock_user.username = "admin"
    mock_user.email = "admin@example.com"
    mock_user.role_id = "role-admin-id"
    mock_user.role_name = "admin"
    mock_user.roles = ["admin"]
    mock_user.role_ids = ["role-admin-id"]
    mock_user.is_admin = True
    mock_user.is_active = True
    return mock_user


@pytest.fixture
def normal_user():
    """Mock normal user for testing permission checks"""
    mock_user = MagicMock()
    mock_user.id = "user_001"
    mock_user.username = "testuser"
    mock_user.email = "user@example.com"
    mock_user.role_id = "role-user-id"
    mock_user.role_name = "asset_viewer"
    mock_user.roles = ["asset_viewer"]
    mock_user.role_ids = ["role-user-id"]
    mock_user.is_admin = False
    mock_user.is_active = True
    return mock_user


@pytest.fixture
def unauthenticated_client():
    """Create a test client without authentication for testing unauthorized access"""
    from fastapi.testclient import TestClient

    from src.main import app

    # Return client without auth headers
    return TestClient(app)


@pytest.fixture
def client_normal_user(db_session, normal_user):
    """Create a test client with a normal user and real admin checks enabled."""
    from fastapi.testclient import TestClient

    from src.database import get_async_db
    from src.main import app
    from src.middleware.auth import (
        get_current_active_user,
        get_current_user,
        get_current_user_from_cookie,
    )

    def mock_get_current_user():
        return normal_user

    app.dependency_overrides[get_current_active_user] = mock_get_current_user
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_current_user_from_cookie] = mock_get_current_user

    async def override_get_db():
        yield AsyncSessionAdapter(db_session)

    app.dependency_overrides[get_async_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
