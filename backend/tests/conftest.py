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
