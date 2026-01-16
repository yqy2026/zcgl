"""
Unit test configuration and fixtures
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a test client for unit tests"""
    from src.main import app
    return TestClient(app)
