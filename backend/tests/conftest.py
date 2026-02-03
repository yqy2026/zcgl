"""
Root conftest.py - runs before any test collection
"""

import os
import unittest.mock as _mock

# Work around Python's MagicMock(spec=..., __dict__=...) init bug in tests.
_OriginalMagicMock = _mock.MagicMock


class _SafeMagicMock(_OriginalMagicMock):
    def __init__(self, *args, **kwargs):
        dict_override = kwargs.pop("__dict__", None)
        super().__init__(*args, **kwargs)
        if dict_override:
            object.__getattribute__(self, "__dict__").update(dict_override)


_mock.MagicMock = _SafeMagicMock

import pytest

# Set environment variables at the earliest possible moment
# Use TEST_DATABASE_URL for database-backed tests
# Integration/E2E tests should set their own *_TEST_DATABASE_URL
# Performance improvement: 37min → <5min (estimated)
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
if TEST_DATABASE_URL:
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
elif "DATABASE_URL" not in os.environ:
    # Fallback placeholder to satisfy settings import in non-DB tests
    os.environ["DATABASE_URL"] = (
        "postgresql+psycopg://user:pass@localhost:5432/zcgl_test"
    )
    TEST_DATABASE_URL = None

# 为测试环境设置强密钥（使用固定种子确保可复现性，或动态生成）
# 这里使用动态生成，因为测试不应依赖于特定的密钥值
# 注意：必须使用真正随机的密钥，不能包含 "test", "secret", "key" 等弱模式
test_secret_key = os.getenv("SECRET_KEY")
if not test_secret_key or any(
    weak in test_secret_key.lower() for weak in ["test", "secret", "key", "changeme"]
):
    # 使用固定的测试密钥（确保无弱模式）
    # 53字符字符串，包含大写、小写、数字和特殊字符，满足Task 7验证器要求
    os.environ["SECRET_KEY"] = "aB3xK7mN9pQ2rS5tU8vW1xY4zZ6bC8dE0fG2hI4jK6!@#$%^&*"
    # 设置测试数据加密密钥 (43字节 + 版本后缀，满足32字节最小要求)
    os.environ["DATA_ENCRYPTION_KEY"] = (
        "TestEncryptionKeyWithSpecialChars123!@#XyZ456:1"
    )

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

    database_url = os.environ.get("TEST_DATABASE_URL")
    if not database_url:
        yield
        return

    # Only run migrations for integration tests
    run_migrations = False
    try:
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument("tests", nargs="*", default=[])
        args, _ = parser.parse_known_args()

        if "-m" not in sys.argv and "unit" not in sys.argv:
            run_migrations = True
    except Exception:
        run_migrations = True

    if run_migrations and "postgresql" in database_url:
        try:
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
                from sqlalchemy import create_engine

                from src.database import Base

                engine = create_engine(database_url)
                Base.metadata.create_all(bind=engine)
                print("[OK] Database tables created (fallback)")
        except Exception as e:
            print(f"[!] Database setup failed: {e}")
            try:
                from sqlalchemy import create_engine

                from src.database import Base

                engine = create_engine(database_url)
                Base.metadata.create_all(bind=engine)
                print("[OK] Database tables created (fallback)")
            except Exception as e2:
                print(f"[ERROR] Database setup failed completely: {e2}")

    yield


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
def reset_settings_secret_key():
    """
    Keep settings.SECRET_KEY aligned with the current environment for test isolation.
    Some test modules mutate os.environ; ensure the global settings object stays stable.
    """
    from src.core.config import settings

    def sync_secret_key() -> None:
        env_key = os.environ.get("SECRET_KEY")
        if env_key:
            settings.SECRET_KEY = env_key

    sync_secret_key()
    yield
    sync_secret_key()


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


# =============================================================================
# Mock Factory Fixtures
# =============================================================================


@pytest.fixture
def mock_factory():
    """
    Mock 工厂 fixture
    提供统一的 Mock 对象创建方法
    """
    from tests.factories.mock_factory import MockFactory

    return MockFactory


@pytest.fixture
def mock_db(mock_factory):
    """
    Mock 数据库会话 fixture
    返回一个配置好的 Mock 数据库对象
    """
    return mock_factory.create_mock_db()


@pytest.fixture
def mock_user(mock_factory):
    """
    Mock 用户对象 fixture
    """
    return mock_factory.create_mock_user()


@pytest.fixture
def mock_asset(mock_factory):
    """
    Mock 资产对象 fixture
    """
    return mock_factory.create_mock_asset()


@pytest.fixture
def mock_contract(mock_factory):
    """
    Mock 合同对象 fixture
    """
    return mock_factory.create_mock_contract()


@pytest.fixture
def mock_ownership(mock_factory):
    """
    Mock 权属对象 fixture
    """
    return mock_factory.create_mock_ownership()


@pytest.fixture
def mock_organization(mock_factory):
    """
    Mock 组织机构对象 fixture
    """
    return mock_factory.create_mock_organization()


@pytest.fixture
def test_data_generator():
    """
    测试数据生成器 fixture
    使用 Faker 生成真实的测试数据
    """
    from tests.fixtures.test_data_generator import TestDataGenerator

    return TestDataGenerator
