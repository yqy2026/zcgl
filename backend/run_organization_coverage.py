"""
Script to run organization CRUD tests with proper environment setup
"""

import os
import sys

# Set up environment BEFORE importing anything
os.environ["DATABASE_URL"] = "sqlite:///./test_database.db"
os.environ["SECRET_KEY"] = "aB3xK7mN9pQ2rS5tU8vW1xY4zZ6bC8dE0fG2hI4jK6"
os.environ["DEBUG"] = "False"
os.environ["ENVIRONMENT"] = "testing"
os.environ["PYDANTIC_SETTINGS_IGNORE_DOT_ENV"] = "1"

# Now run pytest with coverage
import pytest

sys.exit(
    pytest.main(
        [
            "tests/unit/crud/test_organization.py",
            "--cov=src.crud.organization",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov",
            "-v",
        ]
    )
)
