"""
E2E tests configuration - End-to-end testing setup

This conftest.py is specifically for end-to-end tests and ensures:
- Full application stack is available
- Database is properly initialized with migrations
- Tests can run against the complete API
"""

import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine

from tests.shared.conftest_utils import (
    AsyncSessionAdapter,
    cleanup_transactional_session,
    create_transactional_session,
)

# E2E tests use file database (not memory)
TEST_DATABASE_URL = os.getenv("E2E_TEST_DATABASE_URL") or os.getenv("TEST_DATABASE_URL")

# E2E 使用专用 Redis DB（默认 15），与开发共享 db0 隔离，避免缓存键互相污染；
# 显式设置 REDIS_DB 时尊重外部值（例如连已有数据、或 CI 独立 Redis）。
os.environ.setdefault("REDIS_DB", "15")

# 组织 code 与 CI seed / 前端 E2E spec 共用 E2E_ORG_CODE 环境变量（默认值保持一致，避免字面量漂移）
E2E_ORG_CODE = os.getenv("E2E_ORG_CODE", "E2E-ORG-ROOT")


def create_test_user(
    db_session,
    username: str,
    email: str,
    password: str,
    full_name: str,
    role: str = "user",
    phone: str | None = None,
):
    """
    Helper function to create a test user in the database.

    This function creates users directly in the database, bypassing the API
    to avoid the chicken-and-egg problem of needing authentication to create users.
    """
    from src.database import Base
    from src.models.auth import AccountType, User
    from src.models.rbac import Permission, Role, UserRoleAssignment
    from src.services.core.password_service import PasswordService

    # Ensure tables exist (for in-memory databases)
    Base.metadata.create_all(bind=db_session.bind)

    password_service = PasswordService()
    resolved_phone = phone or f"13{uuid4().int % 10**9:09d}"
    resolved_email = email
    existing_email_user = db_session.query(User).filter(User.email == email).first()
    if existing_email_user is not None:
        local, domain = email.split("@", 1)
        resolved_email = f"{local}+{uuid4().hex[:8]}@{domain}"
    organization = ensure_test_organization(db_session)
    user = User(
        username=username,
        email=resolved_email,
        phone=resolved_phone,
        full_name=full_name,
        password_hash=password_service.get_password_hash(password),
        is_active=True,
        account_type=AccountType.HUMAN,
        organization_id=organization.id,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    role_record = db_session.query(Role).filter(Role.name == role).first()
    if role_record is None:
        role_record = Role(
            name=role,
            display_name="管理员" if role in {"admin", "super_admin"} else "普通用户",
            is_system_role=role in {"admin", "super_admin", "user"},
            is_active=True,
        )
        db_session.add(role_record)
        db_session.commit()
        db_session.refresh(role_record)

    if role in {"admin", "super_admin"}:
        admin_permission = (
            db_session.query(Permission)
            .filter(
                Permission.resource == "system",
                Permission.action == "admin",
            )
            .first()
        )
        if admin_permission is None:
            admin_permission = Permission(
                name="system:admin",
                display_name="系统管理员",
                description="系统管理员全局权限",
                resource="system",
                action="admin",
                is_system_permission=True,
                requires_approval=False,
                created_by="e2e-fixture",
                updated_by="e2e-fixture",
            )
            db_session.add(admin_permission)
            db_session.commit()
            db_session.refresh(admin_permission)
        if admin_permission not in role_record.permissions:
            role_record.permissions.append(admin_permission)
            db_session.commit()

    assignment = UserRoleAssignment(
        user_id=user.id,
        role_id=role_record.id,
        assigned_by="e2e-fixture",
    )
    db_session.add(assignment)
    db_session.commit()
    return user


@pytest.fixture(scope="session")
def test_database_url():
    """Provide the test database URL."""
    if TEST_DATABASE_URL:
        os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    return TEST_DATABASE_URL


@pytest.fixture(scope="session")
def require_redis(test_database_url):
    """E2E must run against a real Redis; REDIS_ENABLED=false is not allowed.

    与根 conftest 的 unit 默认（setdefault false）不同，E2E 是分布式行为验证：
    - REDIS_ENABLED 未显式开启 → 直接失败（fail loud），而不是静默降级内存缓存；
    - Redis 客户端创建后必须真实 ping 通，防止配置指向不可达实例。
    """
    if not test_database_url:
        pytest.skip(
            "E2E_TEST_DATABASE_URL or TEST_DATABASE_URL is required",
        )

    from src.core.config import settings

    if not settings.REDIS_ENABLED or not settings.REDIS_HOST:
        pytest.fail(
            "E2E 测试要求真实 Redis（REDIS_ENABLED=true 且 REDIS_HOST 已配置）；"
            "不允许以 REDIS_ENABLED=false 降级运行"
        )

    import redis as redis_sync

    client = redis_sync.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        password=settings.REDIS_PASSWORD,
        socket_connect_timeout=3,
        socket_timeout=3,
    )
    try:
        pong = client.ping()
    except Exception as exc:  # noqa: BLE001 - 探测连接失败统一失败
        pytest.fail(
            f"E2E Redis 连接失败 {settings.REDIS_HOST}:{settings.REDIS_PORT}: {exc}"
        )
    if pong is not True:
        pytest.fail("E2E Redis ping 未返回 PONG")

    # 会话开始前清空专用 DB，保证可重复运行且不残留上一轮键；
    # db0 可能是开发共享库，禁止 flush，仅提示。
    if settings.REDIS_DB != 0:
        try:
            client.flushdb()
        except Exception as exc:  # noqa: BLE001 - 清理失败统一失败
            pytest.fail(f"E2E Redis flushdb 失败 (db={settings.REDIS_DB}): {exc}")
    else:
        import logging

        logging.getLogger(__name__).warning(
            "E2E Redis 使用 db0（开发共享库）：跳过 flushdb，测试可能残留键；"
            "建议设置 REDIS_DB=15 使用专用库"
        )
    client.close()

    # cache_manager 模块级单例在 import 时即创建后端（Redis 不可达会抛
    # ConfigurationError），因此必须放在 ping 成功之后导入。
    from src.core.cache_manager import cache_manager

    if type(cache_manager.backend).__name__ != "RedisCache":
        pytest.fail(
            f"E2E 缓存后端未使用 Redis（backend={type(cache_manager.backend).__name__}），拒绝运行"
        )
    yield


@pytest.fixture(scope="session")
def engine(test_database_url, require_redis):
    """Create database engine for tests."""
    if not test_database_url:
        pytest.skip(
            "E2E_TEST_DATABASE_URL or TEST_DATABASE_URL is required",
        )

    if not test_database_url.startswith("postgresql"):
        raise RuntimeError("测试必须使用 PostgreSQL")

    engine = create_engine(test_database_url, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def db_tables(engine):
    """Reuse the root test DB bootstrap to avoid duplicate Alembic/setup work."""
    _ = engine
    yield


@pytest.fixture(autouse=True)
def reset_global_redis_clients_for_test():
    """每个测试重建全局 async Redis 客户端与权限缓存服务。

    TestClient 每个测试持有独立 event loop；全局单例 Redis 客户端绑定首个
    loop，后续测试复用会抛 "Event loop is closed" 并使权限缓存静默降级回 DB
    （REDIS_ENABLED=false 时无此问题，因为 get_redis() 直接返回 None）。
    每测试重置两个模块级单例，让客户端在测试自己的 loop 内创建，权限缓存
    在真实 Redis 上真正生效。
    """
    import src.database as database_module
    from src.services.permission import permission_cache_service as pcs_module

    database_module._redis_client = None
    pcs_module._permission_cache_service = None
    yield
    database_module._redis_client = None
    pcs_module._permission_cache_service = None


@pytest.fixture(scope="function")
def db_session(engine, db_tables):
    """Create a new database session for each test."""
    session, connection, transaction = create_transactional_session(engine)

    yield session

    # Roll back the transaction after test
    cleanup_transactional_session(session, connection, transaction)


@pytest.fixture(scope="function")
def client(db_session):
    """Create a FastAPI TestClient with database session."""
    from fastapi.testclient import TestClient

    from src.database import get_async_db
    from src.main import app

    # Override the database dependency
    async def override_get_db():
        yield AsyncSessionAdapter(db_session)

    app.dependency_overrides[get_async_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    # Clean up dependency override
    app.dependency_overrides.clear()


@pytest.fixture
def test_admin_user(db_session, db_tables):
    """
    Create a test admin user in the database.

    This fixture provides an admin user for tests that need to test admin functionality.
    The user is created directly in the database to avoid authentication requirements.
    Depends on db_tables to ensure tables exist before creating users.
    """
    return create_test_user(
        db_session,
        username="admin_test",
        email="admin_test@example.com",
        password="AdminPass123!",
        full_name="Admin Test User",
        role="admin",
    )


@pytest.fixture
def test_regular_user(db_session, db_tables):
    """
    Create a test regular user in the database.

    This fixture provides a regular user for tests that need to test user functionality.
    The user is created directly in the database to avoid authentication requirements.
    Depends on db_tables to ensure tables exist before creating users.
    """
    return create_test_user(
        db_session,
        username="regular_user",
        email="regular_user@example.com",
        password="UserPass123!",
        full_name="Regular User",
        role="user",
    )


@pytest.fixture
def create_test_user_factory(db_session, db_tables):
    def _create_test_user(
        username: str,
        email: str,
        password: str,
        full_name: str,
        role: str = "user",
    ):
        return create_test_user(
            db_session,
            username=username,
            email=email,
            password=password,
            full_name=full_name,
            role=role,
        )

    return _create_test_user


def ensure_test_organization(db_session):
    """Ensure at least one active organization exists for tenant-scoped queries."""
    from src.models.organization import Organization

    organization = (
        db_session.query(Organization).filter(Organization.code == E2E_ORG_CODE).first()
    )
    if organization is None:
        organization = Organization(
            name="E2E Test Organization",
            code=E2E_ORG_CODE,
            level=1,
            sort_order=0,
            type="总部",
            status="active",
            path=f"/{E2E_ORG_CODE}",
            is_deleted=False,
            created_by="e2e-fixture",
            updated_by="e2e-fixture",
        )
        db_session.add(organization)
        db_session.commit()
        db_session.refresh(organization)
    return organization


@pytest.fixture
def authenticated_client(client, create_test_user_factory, db_session):
    """Create an authenticated admin client using real login flow."""
    user = create_test_user_factory(
        username="e2e_admin",
        email="e2e_admin@example.com",
        password="Admin123!@#",
        full_name="E2E Admin User",
        role="admin",
    )
    response = client.post(
        "/api/v1/auth/login",
        json={"identifier": "e2e_admin", "password": "Admin123!@#"},
    )
    assert response.status_code == 200

    auth_token = response.cookies.get("auth_token")
    csrf_token = response.cookies.get("csrf_token")
    if auth_token is not None:
        client.cookies.set("auth_token", auth_token)
    if csrf_token is not None:
        client.cookies.set("csrf_token", csrf_token)

    setattr(client, "_csrf_token", csrf_token)
    setattr(client, "_user_id", user.id)
    return client


@pytest.fixture
def csrf_headers(authenticated_client) -> dict[str, str]:
    csrf_token = getattr(authenticated_client, "_csrf_token", None)
    if csrf_token is None:
        return {}
    return {"X-CSRF-Token": csrf_token}
