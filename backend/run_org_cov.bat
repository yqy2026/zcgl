@echo off
REM Set environment variables before pytest-cov loads
if not defined TEST_DATABASE_URL (
  set DATABASE_URL=postgresql://user:pass@localhost:5432/zcgl_test
) else (
  set DATABASE_URL=%TEST_DATABASE_URL%
)
set SECRET_KEY=aB3xK7mN9pQ2rS5tU8vW1xY4zZ6bC8dE0fG2hI4jK6
set DEBUG=False
set ENVIRONMENT=testing
set PYDANTIC_SETTINGS_IGNORE_DOT_ENV=1

REM Run pytest with coverage
python -m pytest tests/unit/crud/test_organization.py --cov=src.crud.organization --cov-report=term-missing -v
