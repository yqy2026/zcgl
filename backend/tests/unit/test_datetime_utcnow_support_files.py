"""静态约束：支持脚本/迁移/测试夹具不再使用 datetime.utcnow()."""

from pathlib import Path

import pytest

FILE_PATHS = [
    "conftest.py",
    "tests/fixtures/auth.py",
    "scripts/documentation/generate_api_docs.py",
    "scripts/documentation/generate_db_docs.py",
    "scripts/documentation/generate_system_docs.py",
    "scripts/setup/init_rbac_data.py",
    "alembic/versions/20260206_add_asset_fields_and_system_admin_permission.py",
    "alembic/versions/20260206_remove_legacy_role_and_asset_ownership_entity.py",
    "alembic/versions/20260208_simplify_organization_schema.py",
]

BACKEND_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("file_path", FILE_PATHS)
def test_support_file_avoids_datetime_utcnow(file_path: str) -> None:
    """指定支持文件源码中不应包含 datetime.utcnow 调用。"""
    content = (BACKEND_ROOT / file_path).read_text(encoding="utf-8")
    assert "datetime.utcnow(" not in content
