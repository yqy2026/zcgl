"""Conftest for vision service tests to provide httpx mocking"""

from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture
def mock_httpx_async_client():
    """Auto-mock httpx.AsyncClient for all vision service tests"""
    # Create mock client that can be used as async context manager
    mock_client = AsyncMock()

    def create_mock_client(*args, **kwargs):
        """Return our mock client when AsyncClient is called"""
        return mock_client

    # Patch httpx.AsyncClient before any service imports it
    with patch("httpx.AsyncClient", side_effect=create_mock_client):
        yield mock_client
