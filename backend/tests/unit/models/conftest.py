"""
Fixtures for model unit tests
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database import Base


@pytest.fixture(scope="function")
def db_session():
    """
    Create a test database session for model unit tests.
    This is a lightweight in-memory database for testing model behavior.
    """
    # Use in-memory SQLite for fast unit tests
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False}
    )

    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Create session
    test_session_local = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine
    )

    session = test_session_local()

    yield session

    # Cleanup
    session.close()
    Base.metadata.drop_all(bind=engine)
