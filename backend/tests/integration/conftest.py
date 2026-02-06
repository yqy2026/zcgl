"""
Integration tests configuration - Database setup and fixtures

This conftest.py is specifically for integration tests and ensures:
- Database is properly initialized with migrations
- Test data is isolated between tests
- Database transactions are rolled back after each test
"""

import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import sessionmaker

# Lazy imports - only import when fixtures are actually used
# This avoids ModuleNotFoundError during pytest collection

# Conditionally import testcontainers
try:
    from testcontainers.postgres import PostgresContainer

    HAS_TESTCONTAINERS = True
except ImportError:
    HAS_TESTCONTAINERS = False
    PostgresContainer = None


# Integration tests use file database (not memory)
# Unit tests use memory database to avoid lock contention
TEST_DATABASE_URL = os.getenv("INTEGRATION_TEST_DATABASE_URL") or os.getenv(
    "TEST_DATABASE_URL"
)

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

    def add(self, *args, **kwargs):  # noqa: ANN001
        return self._session.add(*args, **kwargs)

    def delete(self, *args, **kwargs):  # noqa: ANN001
        return self._session.delete(*args, **kwargs)

    def __getattr__(self, name: str):  # noqa: D401 - test helper
        return getattr(self._session, name)


@pytest.fixture(scope="session")
def test_database_url():
    """
    Provide the test database URL.
    Uses INTEGRATION_TEST_DATABASE_URL when available.
    """
    if TEST_DATABASE_URL:
        os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    return TEST_DATABASE_URL


@pytest.fixture(scope="session")
def engine(test_database_url):
    """
    Create database engine for tests.

    Uses PostgreSQL (either provided URL or testcontainers).
    """
    if os.getenv("TEST_USE_POSTGRES") == "true" and HAS_TESTCONTAINERS:
        postgres = PostgresContainer("postgres:15")
        postgres.start()
        db_url = postgres.get_connection_url()
        engine = create_engine(db_url, pool_pre_ping=True)
        yield engine
        postgres.stop()
        return

    if not test_database_url:
        pytest.skip(
            "INTEGRATION_TEST_DATABASE_URL or TEST_DATABASE_URL is required",
            allow_module_level=True,
        )

    engine = create_engine(test_database_url, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def db_tables(engine):
    """
    Create all database tables using Alembic migrations.
    This ensures the database schema matches production.

    Runs once per test session for performance.
    """
    # Import Base here - after pytest has set up the path
    # Base is defined in src/database.py, NOT src/models/base.py!
    # Import Alembic configuration
    from alembic.config import Config

    from src.database import Base

    # Check if Alembic migrations exist
    versions_dir = Path("alembic/versions")
    has_migrations = versions_dir.exists() and len(list(versions_dir.glob("*.py"))) > 0

    # Run Alembic migrations first, then create any remaining tables
    if has_migrations:
        # Use Alembic migrations if they exist
        from alembic import command

        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
        try:
            command.upgrade(alembic_cfg, "head")
        except ProgrammingError as exc:
            # If tables already exist without a matching Alembic version, stamp head.
            if "DuplicateTable" in str(exc) or "already exists" in str(exc):
                inspector = inspect(engine)
                if inspector.get_table_names():
                    command.stamp(alembic_cfg, "head")
                else:
                    raise
            else:
                raise

    # ALWAYS create tables from Base.metadata
    # The initial migration is empty (placeholder), so we need to create base tables
    # This also creates any tables that aren't managed by Alembic
    Base.metadata.create_all(bind=engine)

    yield

    # Clean up: Drop all tables after test session
    try:
        Base.metadata.drop_all(bind=engine)
    except Exception:
        # Ignore cleanup errors (database might not exist, etc.)
        pass


@pytest.fixture(scope="function")
def db_session(engine, db_tables):
    """
    Create a new database session for each test.
    Automatically rolls back transactions after each test.

    This ensures test isolation - changes made in one test
    don't affect other tests.
    """
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
        # Ignore cleanup errors
        pass


@pytest.fixture(scope="function")
def test_data(db_session):
    """
    Provide common test data for integration tests.
    Creates minimal test data that tests can rely on.

    Tests should create their own specific data,
    but can use this fixture for common entities.
    """
    # Import models needed for test data
    from src.models.auth import User
    from src.models.organization import Organization
    from src.models.rbac import Role, UserRoleAssignment
    from src.services.core.password_service import PasswordService
    from src.services.enum_data_init import init_enum_data

    password_service = PasswordService()

    init_enum_data(db_session, created_by="integration_test")

    # Create test organization
    test_org = Organization(
        name="Test Organization", code="TEST_ORG", type="department"
    )
    db_session.add(test_org)
    db_session.commit()

    # Create test admin user
    test_admin = User(
        username="admin",
        email="admin@test.com",
        full_name="Test Admin",
        password_hash=password_service.get_password_hash("Admin123!@#"),
        is_active=True,
        default_organization_id=test_org.id,
    )
    db_session.add(test_admin)
    db_session.commit()
    db_session.refresh(test_admin)

    admin_role = db_session.query(Role).filter(Role.name == "admin").first()
    if admin_role is None:
        admin_role = Role(
            name="admin",
            display_name="管理员",
            is_system_role=True,
            is_active=True,
        )
        db_session.add(admin_role)
        db_session.commit()
        db_session.refresh(admin_role)

    db_session.add(
        UserRoleAssignment(
            user_id=test_admin.id,
            role_id=admin_role.id,
            assigned_by="integration_test",
        )
    )
    db_session.commit()

    # Provide test data as a dictionary
    yield {"organization": test_org, "admin": test_admin}

    # Cleanup is handled by db_session fixture (rollback)


@pytest.fixture
def client(db_session):
    """
    Create a FastAPI TestClient with database session.

    This overrides the database dependency injection to use
    our test database session instead of the real database.
    """
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


@pytest.fixture(scope="function")
def test_token():
    """
    Provide a test token for API authentication.

    NOTE: This is a dummy token for testing. In a real test setup,
    you would generate a valid JWT token using the test user.
    """
    return "test_token"


@pytest.fixture(scope="function")
def auth_headers(test_token: str):
    """Provide empty headers (cookie-only auth)."""
    _ = test_token
    return {}
