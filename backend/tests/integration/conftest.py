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
from sqlalchemy import create_engine
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
TEST_DATABASE_URL = os.getenv(
    "INTEGRATION_TEST_DATABASE_URL", "sqlite:///./test_integration.db"
)

# Set DATABASE_URL early so root conftest's setup_test_database fixture
# uses this for migrations instead of the default :memory:
os.environ["DATABASE_URL"] = TEST_DATABASE_URL


@pytest.fixture(scope="session")
def test_database_url():
    """
    Provide the test database URL.
    Uses CI database path when available, otherwise defaults to local test database.
    """
    # Set DATABASE_URL env var so that root conftest's setup_test_database
    # fixture runs migrations against the correct database
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    return TEST_DATABASE_URL


@pytest.fixture(scope="session")
def engine(test_database_url):
    """
    Create database engine for tests.

    For SQLite: Creates an in-memory or file-based database
    For PostgreSQL: Uses testcontainers for isolated test database
    """
    # Check if we should use PostgreSQL (for more realistic integration tests)
    if os.getenv("TEST_USE_POSTGRES") == "true" and HAS_TESTCONTAINERS:
        postgres = PostgresContainer("postgres:15")
        postgres.start()

        # Get the connection URL
        db_url = postgres.get_connection_url()

        # Create engine
        engine = create_engine(db_url, pool_pre_ping=True)

        yield engine

        postgres.stop()
    else:
        # Use SQLite for faster tests
        engine = create_engine(
            test_database_url,
            connect_args={"check_same_thread": False}
            if "sqlite" in test_database_url
            else {},
            pool_pre_ping=True,
        )
        yield engine

        # Clean up SQLite database file if it's a file path
        if "sqlite" in test_database_url and "test_database.db" in test_database_url:
            db_path = test_database_url.replace("sqlite:///", "")
            if os.path.exists(db_path):
                try:
                    os.remove(db_path)
                except PermissionError:
                    # File might be locked, especially on Windows
                    pass


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
        command.upgrade(alembic_cfg, "head")

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
    from src.services.core.password_service import PasswordService

    password_service = PasswordService()

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
        role="admin",
        is_active=True,
        default_organization_id=test_org.id,
    )
    db_session.add(test_admin)
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

    from src.database import get_db
    from src.main import app

    # Override the database dependency
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

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
    """Provide authentication headers for API requests."""
    return {"Authorization": f"Bearer {test_token}"}
