"""
Core unit tests configuration
Handles settings initialization for testing
"""

import os


def pytest_configure(config):
    """
    This hook runs before any test collection.
    Set environment variables BEFORE any imports from src.core.
    """
    os.environ["DATABASE_URL"] = "sqlite:///test.db"
    # 使用强密钥，不包含任何弱模式（如 "test", "secret", "key" 等）
    os.environ["SECRET_KEY"] = "aB3xK7mN9pQ2rS5tU8vW1xY4zZ6bC8dE0fG2hI4jK6!@#"
    os.environ["DEBUG"] = "False"  # Must be False (capital F) or 0 for pydantic bool
    os.environ["ENVIRONMENT"] = "test"

    # Prevent .env file from being loaded by pydantic-settings
    os.environ["PYDANTIC_SETTINGS_IGNORE_DOT_ENV"] = "1"
