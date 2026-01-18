"""
Root conftest.py - runs before any test collection
"""

import os

import pytest

# Set environment variables at the earliest possible moment
# Use consistent database path with CI workflow
# CI uses: sqlite:///./test_database.db
# Tests use: sqlite:///./test_database.db (aligned)
os.environ["DATABASE_URL"] = os.getenv("DATABASE_URL", "sqlite:///./test_database.db")

# 为测试环境设置强密钥（使用固定种子确保可复现性，或动态生成）
# 这里使用动态生成，因为测试不应依赖于特定的密钥值
# 注意：必须使用真正随机的密钥，不能包含 "test", "secret", "key" 等弱模式
test_secret_key = os.getenv("SECRET_KEY")
if not test_secret_key or any(
    weak in test_secret_key.lower() for weak in ["test", "secret", "key", "changeme"]
):
    # 使用固定的测试密钥（确保无弱模式）
    # 这是个43字符的URL安全字符串，不包含任何弱密钥模式
    os.environ["SECRET_KEY"] = "aB3xK7mN9pQ2rS5tU8vW1xY4zZ6bC8dE0fG2hI4jK6"

os.environ["DEBUG"] = "False"
os.environ["ENVIRONMENT"] = "testing"
os.environ["PYDANTIC_SETTINGS_IGNORE_DOT_ENV"] = "1"


def pytest_collection_modifyitems(items, config):
    """
    钩子：为特定目录下的测试自动应用标记

    这个钩子在测试收集完成后、测试执行前被调用
    """
    for item in items:
        # 获取测试文件的路径
        test_path = str(item.fspath)

        # 根据目录自动添加标记
        if "/tests/unit/" in test_path or "\\tests\\unit\\" in test_path:
            if "unit" not in [mark.name for mark in item.iter_markers()]:
                item.add_marker(pytest.mark.unit)
        elif (
            "/tests/integration/" in test_path or "\\tests\\integration\\" in test_path
        ):
            if "integration" not in [mark.name for mark in item.iter_markers()]:
                item.add_marker(pytest.mark.integration)
        elif "/tests/api/" in test_path or "\\tests\\api\\" in test_path:
            if "api" not in [mark.name for mark in item.iter_markers()]:
                item.add_marker(pytest.mark.api)


@pytest.fixture(scope="session", autouse=True)
def hide_env_file():
    """
    Session-scoped fixture to temporarily hide .env file during tests.
    This prevents Pydantic Settings from reading DATA_ENCRYPTION_KEY from .env,
    allowing tests to control the encryption key via environment variables.

    The .env file is renamed to .env.backup before tests and restored after.
    """
    import shutil

    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    backup_path = env_path + ".backup"

    # Check if .env file exists
    if os.path.exists(env_path):
        # Rename .env to .env.backup
        shutil.move(env_path, backup_path)
        print("[*] Temporarily hid .env file for tests (backed up as .env.backup)")

    yield

    # Restore .env file after all tests complete
    if os.path.exists(backup_path):
        shutil.move(backup_path, env_path)
        print("[*] Restored .env file after tests")


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """
    Session-scoped fixture to set up the test database before any tests run.
    This ensures database tables exist for integration tests.

    Runs once per test session for performance.
    """
    import subprocess
    import sys

    database_url = os.environ.get("DATABASE_URL", "sqlite:///./test_database.db")

    # Only run migrations for integration tests
    # Check if we're running integration tests
    run_migrations = False
    try:
        # Check if any integration tests are being run
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument("tests", nargs="*", default=[])
        args, _ = parser.parse_known_args()

        # Simple heuristic: if pytest was invoked without -m unit,
        # assume integration tests might run
        import sys

        if "-m" not in sys.argv and "unit" not in sys.argv:
            run_migrations = True
    except Exception:
        # If we can't determine, be safe and run migrations
        run_migrations = True

    if run_migrations and ("sqlite" in database_url or "postgresql" in database_url):
        try:
            # Run Alembic migrations
            print(f"\n[*] Setting up test database: {database_url}")
            result = subprocess.run(
                [sys.executable, "-m", "alembic", "upgrade", "head"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode == 0:
                print("[OK] Database migrations completed successfully")
            else:
                print(f"[!] Migration warnings: {result.stderr}")
                # Fallback: create tables directly
                from sqlalchemy import create_engine

                # Base is defined in src/database.py, NOT src/models/base.py!
                from src.database import Base

                engine = create_engine(database_url)
                Base.metadata.create_all(bind=engine)
                print("[OK] Database tables created (fallback)")
        except Exception as e:
            print(f"[!] Database setup failed: {e}")
            # Try to create tables directly as fallback
            try:
                from sqlalchemy import create_engine

                # Base is defined in src/database.py, NOT src/models/base.py!
                from src.database import Base

                engine = create_engine(database_url)
                Base.metadata.create_all(bind=engine)
                print("[OK] Database tables created (fallback)")
            except Exception as e2:
                print(f"[ERROR] Database setup failed completely: {e2}")

    yield

    # Cleanup: Optionally remove test database file
    if (
        "sqlite" in database_url or "postgresql" in database_url
    ) and "test" in database_url:
        db_path = database_url.replace("sqlite:///", "")
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
                print(f"[*] Cleaned up test database: {db_path}")
            except PermissionError:
                # File might be locked, especially on Windows
                print(f"[!] Could not remove test database (file locked): {db_path}")
            except Exception as e:
                print(f"[!] Could not remove test database: {e}")


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


@pytest.fixture(autouse=True)
def reset_encryption_key(monkeypatch):
    """
    Auto-used fixture to reset DATA_ENCRYPTION_KEY before each test.
    This prevents test isolation issues for encryption tests.
    """
    # Remove DATA_ENCRYPTION_KEY from environment before each test
    monkeypatch.delenv("DATA_ENCRYPTION_KEY", raising=False)
    yield
    # Clean up after test
    monkeypatch.delenv("DATA_ENCRYPTION_KEY", raising=False)
