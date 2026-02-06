"""
组织服务增强测试（已停用）

原测试依赖已移除的同步 OrganizationService API。待异步接口补齐后恢复。
"""

import pytest

pytest.skip(
    "Legacy OrganizationService enhanced tests pending async API alignment.",
    allow_module_level=True,
)
