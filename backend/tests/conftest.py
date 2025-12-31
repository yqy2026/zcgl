"""
Root conftest.py - runs before any test collection
"""

import os

import pytest

# Set environment variables at the earliest possible moment
os.environ["DATABASE_URL"] = "sqlite:///test.db"
os.environ["SECRET_KEY"] = (
    "test-secret-key-for-unit-testing-only-do-not-use-in-production"
)
os.environ["DEBUG"] = "False"
os.environ["ENVIRONMENT"] = "test"
os.environ["PYDANTIC_SETTINGS_IGNORE_DOT_ENV"] = "1"


@pytest.fixture(autouse=True)
def reset_settings_debug():
    """
    Auto-used fixture to ensure settings.DEBUG is reset before each test.
    This prevents test isolation issues when tests modify the global settings object.
    This fixture applies to ALL tests in the entire test suite.
    """
    from src.core.config import settings

    original_debug = settings.DEBUG
    yield
    # Always restore to original value after test
    settings.DEBUG = original_debug
