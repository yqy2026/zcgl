"""
E2E tests configuration - End-to-end testing setup

This conftest.py is specifically for end-to-end tests and ensures:
- Full application stack is available
- Database is properly initialized with migrations
- Tests can run against the complete API
"""

import os
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# E2E tests use file database (not memory)
TEST_DATABASE_URL = os.getenv("E2E_TEST_DATABASE_URL") or os.getenv("TEST_DATABASE_URL")


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

    def add(self, *args, **kwargs):  # noqa: ANN001
        return self._session.add(*args, **kwargs)

    def delete(self, *args, **kwargs):  # noqa: ANN001
        return self._session.delete(*args, **kwargs)

    def __getattr__(self, name: str):  # noqa: D401 - test helper
        return getattr(self._session, name)


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
    from src.models.auth import User
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
    user = User(
        username=username,
        email=resolved_email,
        phone=resolved_phone,
        full_name=full_name,
        password_hash=password_service.get_password_hash(password),
        is_active=True,
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
def engine(test_database_url):
    """Create database engine for tests."""
    if not test_database_url:
        pytest.skip(
            "E2E_TEST_DATABASE_URL or TEST_DATABASE_URL is required",
            allow_module_level=True,
        )

    if not test_database_url.startswith("postgresql"):
        raise RuntimeError("测试必须使用 PostgreSQL")

    engine = create_engine(test_database_url, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def db_tables(engine):
    """Create all database tables using Alembic migrations."""
    from alembic.config import Config

    from alembic import command
    from src.database import Base

    # Check if Alembic migrations exist
    versions_dir = Path("alembic/versions")
    has_migrations = versions_dir.exists() and len(list(versions_dir.glob("*.py"))) > 0

    # Run Alembic migrations to create tables
    if has_migrations:
        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
        command.upgrade(alembic_cfg, "head")
        Base.metadata.create_all(bind=engine)
    else:
        Base.metadata.create_all(bind=engine)

    yield

    # Clean up: Drop all tables after test session
    try:
        Base.metadata.drop_all(bind=engine)
    except Exception:
        pass


@pytest.fixture(scope="function")
def db_session(engine, db_tables):
    """Create a new database session for each test."""
    test_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    session = test_session_local()

    # Begin a transaction for this test
    connection = engine.connect()
    transaction = connection.begin()
    session.bind = connection

    yield session

    # Roll back the transaction after test
    try:
        session.close()
        transaction.rollback()
        connection.close()
    except Exception:
        pass


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
