"""分层约束测试：system_settings 路由应委托 SystemSettingsService。"""

import inspect
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.api


def test_system_settings_api_module_should_not_use_crud_adapter_calls():
    """路由层不应直接调用 AuditLogCRUD/security_event_crud。"""
    from src.api.v1.system import system_settings

    module_source = inspect.getsource(system_settings)
    assert "AuditLogCRUD" not in module_source
    assert "security_event_crud." not in module_source


def test_system_settings_api_module_should_not_execute_db_query_directly():
    """路由层不应直接执行数据库连通性 SQL。"""
    from src.api.v1.system import system_settings

    module_source = inspect.getsource(system_settings)
    assert "await db.execute(" not in module_source
    assert 'text("SELECT 1")' not in module_source


@pytest.mark.asyncio
@patch("src.api.v1.system.system_settings.RBACService")
async def test_get_security_events_should_delegate_to_service(mock_rbac_cls, mock_db):
    """安全事件列表端点应委托给 service.get_security_events。"""
    from src.api.v1.system.system_settings import get_security_events

    mock_rbac = MagicMock()
    mock_rbac.is_admin = AsyncMock(return_value=True)
    mock_rbac_cls.return_value = mock_rbac

    event = MagicMock()
    event.id = "event-1"
    event.event_type = "auth_failure"
    event.user_id = "user-1"
    event.ip_address = "127.0.0.1"
    event.severity = "high"
    event.event_metadata = {"reason": "password"}
    event.created_at = datetime(2026, 1, 1, 10, 0, 0)

    mock_service = MagicMock()
    mock_service.get_security_events = AsyncMock(return_value=([event], 1))

    result = await get_security_events(
        db=mock_db,
        current_user=MagicMock(id="admin-1"),
        skip=5,
        page_size=10,
        service=mock_service,
    )

    assert result["total"] == 1
    assert result["skip"] == 5
    assert result["page_size"] == 10
    assert result["events"][0]["id"] == "event-1"
    mock_service.get_security_events.assert_awaited_once_with(
        db=mock_db,
        skip=5,
        limit=10,
    )


@pytest.mark.asyncio
@patch("src.api.v1.system.system_settings.get_client_ip", return_value="127.0.0.1")
async def test_create_audit_log_with_fallback_async_should_delegate_to_service(
    _mock_get_client_ip, mock_db
):
    """审计日志辅助函数应委托给 service.create_audit_log_async。"""
    from src.api.v1.system.system_settings import create_audit_log_with_fallback_async

    mock_service = MagicMock()
    mock_service.create_audit_log_async = AsyncMock(return_value=None)

    request = MagicMock()
    request.headers = {"user-agent": "pytest-agent"}
    current_user = MagicMock(id="user-1")

    await create_audit_log_with_fallback_async(
        db=mock_db,
        current_user=current_user,
        action="TEST_ACTION",
        resource_type="system",
        request=request,
        service=mock_service,
        payload="value",
    )

    mock_service.create_audit_log_async.assert_awaited_once_with(
        db=mock_db,
        user_id="user-1",
        action="TEST_ACTION",
        resource_type="system",
        ip_address="127.0.0.1",
        user_agent="pytest-agent",
        request_body='{"payload": "value"}',
    )


@pytest.mark.asyncio
async def test_get_system_info_should_delegate_database_check_to_service(mock_db):
    """系统信息端点应委托 service 检查数据库连接。"""
    from src.api.v1.system.system_settings import get_system_info

    mock_service = MagicMock()
    mock_service.check_database_connection = AsyncMock(return_value=True)

    result = await get_system_info(
        db=mock_db,
        current_user=MagicMock(id="admin-1"),
        service=mock_service,
    )

    assert result.data.database_status == "connected"
    mock_service.check_database_connection.assert_awaited_once_with(db=mock_db)
