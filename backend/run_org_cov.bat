@echo off
REM Set environment variables before pytest-cov loads
set DATABASE_URL=sqlite:///./test_database.db
set SECRET_KEY=aB3xK7mN9pQ2rS5tU8vW1xY4zZ6bC8dE0fG2hI4jK6
set DEBUG=False
set ENVIRONMENT=testing
set PYDANTIC_SETTINGS_IGNORE_DOT_ENV=1

REM Run pytest with coverage
python -m pytest tests/unit/crud/test_organization.py --cov=src.crud.organization --cov-report=term-missing -v
