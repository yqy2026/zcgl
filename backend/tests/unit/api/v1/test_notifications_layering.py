"""分层约束测试：notifications 路由应接入统一 ABAC 依赖。"""

import inspect
import re

import pytest

pytestmark = pytest.mark.api


def test_notifications_api_module_should_not_use_crud_adapter_calls() -> None:
    """路由层不应直接调用 notification_crud。"""
    from src.api.v1.system import notifications

    module_source = inspect.getsource(notifications)
    assert "notification_crud." not in module_source


def test_notifications_endpoints_should_use_require_authz() -> None:
    """notifications 关键端点应接入 require_authz。"""
    from src.api.v1.system import notifications

    module_source = inspect.getsource(notifications)
    assert "AuthzContext" in module_source
    assert "require_authz" in module_source

    patterns = [
        r"async def get_notifications[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"notification\"",
        r"async def get_unread_count[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"notification\"",
        r"async def mark_notification_as_read[\s\S]*?require_authz\([\s\S]*?action=\"update\"[\s\S]*?resource_type=\"notification\"[\s\S]*?resource_id=\"\{notification_id\}\"",
        r"async def mark_all_as_read[\s\S]*?require_authz\([\s\S]*?action=\"update\"[\s\S]*?resource_type=\"notification\"",
        r"async def delete_notification[\s\S]*?require_authz\([\s\S]*?action=\"delete\"[\s\S]*?resource_type=\"notification\"[\s\S]*?resource_id=\"\{notification_id\}\"",
        r"async def run_notification_tasks_endpoint[\s\S]*?require_authz\([\s\S]*?action=\"update\"[\s\S]*?resource_type=\"notification\"",
    ]

    for pattern in patterns:
        assert re.search(pattern, module_source), pattern


def test_notifications_should_not_define_fake_unscoped_update_context() -> None:
    from src.api.v1.system import notifications

    assert not hasattr(notifications, "_NOTIFICATION_UPDATE_UNSCOPED_PARTY_ID")
    assert not hasattr(notifications, "_NOTIFICATION_UPDATE_RESOURCE_CONTEXT")
