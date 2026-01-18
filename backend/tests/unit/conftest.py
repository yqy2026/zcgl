"""
Unit test configuration and fixtures
"""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


@pytest.fixture
def client(monkeypatch):
    """Create a test client for unit tests with authentication bypassed"""
    from src.database import get_db
    from src.main import app
    from src.middleware.auth import get_current_active_user, require_permission

    # Mock authenticated user
    mock_user = MagicMock()
    mock_user.id = "test_user_001"
    mock_user.username = "testuser"
    mock_user.email = "test@example.com"
    mock_user.role = "admin"
    mock_user.is_active = True

    # Use monkeypatch to replace functions at module level
    def mock_get_current_user():
        return mock_user

    def mock_require_permission(resource, action):
        def dependency():
            return mock_user

        return dependency

    monkeypatch.setattr(
        "src.middleware.auth.get_current_active_user", mock_get_current_user
    )
    monkeypatch.setattr(
        "src.middleware.auth.require_permission", mock_require_permission
    )

    # Override dependencies in FastAPI app
    app.dependency_overrides[get_current_active_user] = mock_get_current_user
    app.dependency_overrides[require_permission] = mock_require_permission

    # Mock database session
    def mock_get_db():
        db = MagicMock(spec=Session)
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = mock_get_db

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
    mock_user.role = "admin"
    mock_user.is_active = True
    return mock_user


@pytest.fixture
def normal_user():
    """Mock normal user for testing permission checks"""
    mock_user = MagicMock()
    mock_user.id = "user_001"
    mock_user.username = "testuser"
    mock_user.email = "user@example.com"
    mock_user.role = "user"
    mock_user.is_active = True
    return mock_user


@pytest.fixture
def unauthenticated_client():
    """Create a test client without authentication for testing unauthorized access"""
    from fastapi.testclient import TestClient

    from src.main import app

    # Return client without auth headers
    return TestClient(app)
