"""静态约束：核心模块不应继续使用 datetime.utcnow()."""

from pathlib import Path

import pytest

MODULE_PATHS = [
    "src/crud/notification.py",
    "src/models/asset.py",
    "src/models/asset_history.py",
    "src/models/associations.py",
    "src/models/auth.py",
    "src/models/collection.py",
    "src/models/contact.py",
    "src/models/enum_field.py",
    "src/models/llm_prompt.py",
    "src/models/notification.py",
    "src/models/ownership.py",
    "src/models/project.py",
    "src/models/project_relations.py",
    "src/models/property_certificate.py",
    "src/models/security_event.py",
    "src/models/system_dictionary.py",
    "src/models/task.py",
]

BACKEND_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("module_path", MODULE_PATHS)
def test_module_avoids_datetime_utcnow(module_path: str) -> None:
    """指定模块源码中不应包含 datetime.utcnow 调用。"""
    content = (BACKEND_ROOT / module_path).read_text(encoding="utf-8")

    assert "datetime.utcnow(" not in content
