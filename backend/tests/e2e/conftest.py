"""
E2E tests configuration - End-to-end testing setup

This conftest.py is specifically for end-to-end tests and ensures:
- Full application stack is available
- Database is properly initialized with migrations
- Tests can run against the complete API
"""

import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# E2E tests use file database (not memory)
TEST_DATABASE_URL = os.getenv("E2E_TEST_DATABASE_URL", "sqlite:///./test_e2e.db")


def create_test_user(
    db_session,
    username: str,
    email: str,
    password: str,
    full_name: str,
    role: str = "user",
):
    """
    Helper function to create a test user in the database.

    This function creates users directly in the database, bypassing the API
    to avoid the chicken-and-egg problem of needing authentication to create users.
    """
    from src.database import Base
    from src.models.auth import User
    from src.services.core.password_service import PasswordService

    # Ensure tables exist (for in-memory databases)
    Base.metadata.create_all(bind=db_session.bind)

    password_service = PasswordService()
    user = User(
        username=username,
        email=email,
        full_name=full_name,
        password_hash=password_service.get_password_hash(password),
        role=role,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="session")
def test_database_url():
    """Provide the test database URL."""
    return TEST_DATABASE_URL


@pytest.fixture(scope="session")
def engine(test_database_url):
    """Create database engine for tests."""
    engine = create_engine(
        test_database_url,
        connect_args={"check_same_thread": False}
        if "sqlite" in test_database_url
        else {},
        pool_pre_ping=True,
    )
    yield engine

    # Clean up SQLite database file
    if "sqlite" in test_database_url and "test_e2e.db" in test_database_url:
        db_path = test_database_url.replace("sqlite:///", "")
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except PermissionError:
                pass


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
