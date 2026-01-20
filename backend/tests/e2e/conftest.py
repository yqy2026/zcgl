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
