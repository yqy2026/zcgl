#!/usr/bin/env python
"""Test runner that sets environment variables before pytest"""
import os
import sys

# Set environment variables before importing pytest
os.environ["DATABASE_URL"] = "sqlite:///test.db"
os.environ["SECRET_KEY"] = "test-secret-key-for-unit-testing-only-do-not-use-in-production"
os.environ["DEBUG"] = "False"
os.environ["ENVIRONMENT"] = "test"
os.environ["PYDANTIC_SETTINGS_IGNORE_DOT_ENV"] = "1"

# Now run pytest
import pytest
sys.exit(pytest.main(sys.argv[1:]))
