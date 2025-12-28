"""
Root conftest.py - runs before any test collection
"""

import os

# Set environment variables at the earliest possible moment
os.environ["DATABASE_URL"] = "sqlite:///test.db"
os.environ["SECRET_KEY"] = (
    "test-secret-key-for-unit-testing-only-do-not-use-in-production"
)
os.environ["DEBUG"] = "False"
os.environ["ENVIRONMENT"] = "test"
os.environ["PYDANTIC_SETTINGS_IGNORE_DOT_ENV"] = "1"
