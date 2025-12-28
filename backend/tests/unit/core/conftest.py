"""
Core unit tests configuration
Handles settings initialization for testing
"""
import os
import sys


def pytest_configure(config):
    """
    This hook runs before any test collection.
    Set environment variables BEFORE any imports from src.core.
    """
    os.environ["DATABASE_URL"] = "sqlite:///test.db"
    os.environ["SECRET_KEY"] = "test-secret-key-for-unit-testing-only-do-not-use-in-production"
    os.environ["DEBUG"] = "False"  # Must be False (capital F) or 0 for pydantic bool
    os.environ["ENVIRONMENT"] = "test"

    # Prevent .env file from being loaded by pydantic-settings
    os.environ["PYDANTIC_SETTINGS_IGNORE_DOT_ENV"] = "1"
