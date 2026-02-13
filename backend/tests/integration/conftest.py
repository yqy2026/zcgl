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
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import ProgrammingError, SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from tests.shared.conftest_utils import AsyncSessionAdapter

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


def _ensure_alembic_version_capacity(engine) -> None:  # noqa: ANN001
    """Ensure alembic_version.version_num can store long revision ids."""
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS alembic_version (
                    version_num VARCHAR(128) NOT NULL PRIMARY KEY
                )
                """
            )
        )
        conn.execute(
            text(
                "ALTER TABLE alembic_version "
                "ALTER COLUMN version_num TYPE VARCHAR(128)"
            )
        )


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
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        engine.dispose()
        pytest.skip(
            f"Integration database is unavailable ({exc.__class__.__name__})",
            allow_module_level=True,
        )

    yield engine
    engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def ensure_integration_engine_ready(engine):
    """
    Force all integration tests to initialize `engine` first.

    This guarantees database availability checks run even for tests that
    don't explicitly depend on `engine`/`db_session` fixtures.
    """
    yield


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
            # If schema objects already exist without a matching Alembic version, stamp head.
            error_text = str(exc)
            schema_already_exists = (
                "DuplicateTable" in error_text
                or "DuplicateColumn" in error_text
                or "already exists" in error_text
            )
            if schema_already_exists:
                inspector = inspect(engine)
                if not inspector.get_table_names():
                    Base.metadata.create_all(bind=engine)
                _ensure_alembic_version_capacity(engine)
                command.stamp(alembic_cfg, "head")
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
    connection = engine.connect()
    transaction = connection.begin()
    test_session_local = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=connection,
    )
    session = test_session_local()

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
    from src.models.rbac import Permission, Role, UserRoleAssignment
    from src.services.core.password_service import PasswordService

    password_service = PasswordService()

    # Create or reuse test organization
    test_org = db_session.query(Organization).filter(Organization.code == "TEST_ORG").first()
    if test_org is None:
        test_org = Organization(
            name="Test Organization", code="TEST_ORG", type="department"
        )
        db_session.add(test_org)
        db_session.commit()
        db_session.refresh(test_org)

    # Create or reuse test admin user
    test_admin = db_session.query(User).filter(User.username == "admin").first()
    if test_admin is None:
        test_admin = User(
            username="admin",
            email="admin@test.com",
            phone="13800009999",
            full_name="Test Admin",
            password_hash=password_service.get_password_hash("Admin123!@#"),
            is_active=True,
            default_organization_id=test_org.id,
            created_by="integration_test",
            updated_by="integration_test",
        )
        db_session.add(test_admin)
        db_session.commit()
        db_session.refresh(test_admin)
    else:
        test_admin.email = "admin@test.com"
        test_admin.phone = "13800009999"
        test_admin.full_name = "Test Admin"
        test_admin.password_hash = password_service.get_password_hash("Admin123!@#")
        test_admin.is_active = True
        test_admin.default_organization_id = test_org.id
        test_admin.updated_by = "integration_test"
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
            created_by="integration_test",
            updated_by="integration_test",
        )
        db_session.add(admin_permission)
        db_session.commit()
        db_session.refresh(admin_permission)
    if admin_permission not in admin_role.permissions:
        admin_role.permissions.append(admin_permission)
        db_session.commit()

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
