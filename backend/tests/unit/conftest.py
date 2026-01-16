"""
Unit test configuration and fixtures
"""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a test client for unit tests"""
    from src.main import app
    return TestClient(app)


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
