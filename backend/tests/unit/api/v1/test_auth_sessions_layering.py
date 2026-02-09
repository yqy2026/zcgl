"""分层约束测试：auth sessions 路由应委托服务层。"""

import inspect
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.api


def test_auth_sessions_module_should_not_use_crud_adapter_calls() -> None:
    """路由模块不应直接调用 session_crud。"""
    from src.api.v1.auth.auth_modules import sessions

    module_source = inspect.getsource(sessions)
    assert "session_crud." not in module_source


@pytest.mark.asyncio
async def test_get_user_sessions_should_delegate_session_service() -> None:
    """获取会话列表路由应委托 session_service.get_user_sessions。"""
    from src.api.v1.auth.auth_modules.sessions import get_user_sessions

    current_user = MagicMock(id="user-1")
    mock_session = MagicMock()
    mock_session.id = "session-1"
    mock_session.user_id = "user-1"
    mock_session.device_info = None
    mock_session.ip_address = "127.0.0.1"
    mock_session.is_active = True
    mock_session.expires_at = datetime.now(UTC)
    mock_session.created_at = datetime.now(UTC)
    mock_session.last_accessed_at = datetime.now(UTC)
    mock_session_service = MagicMock()
    mock_session_service.get_user_sessions = AsyncMock(return_value=[mock_session])

    result = await get_user_sessions(
        db=MagicMock(),
        current_user=current_user,
        session_service=mock_session_service,
    )

    assert len(result) == 1
    mock_session_service.get_user_sessions.assert_awaited_once_with(
        "user-1", active_only=True
    )


@pytest.mark.asyncio
async def test_revoke_session_should_delegate_lookup_and_revoke() -> None:
    """撤销会话路由应委托 session_service 查询和撤销。"""
    from src.api.v1.auth.auth_modules.sessions import revoke_session

    session_id = "session-1"
    current_user = MagicMock(id="user-1")
    mock_session = MagicMock(user_id="user-1", refresh_token="refresh-token")
    mock_session_service = MagicMock()
    mock_session_service.get_session_by_id = AsyncMock(return_value=mock_session)
    mock_session_service.revoke_session = AsyncMock(return_value=True)

    result = await revoke_session(
        session_id=session_id,
        db=MagicMock(),
        current_user=current_user,
        session_service=mock_session_service,
    )

    assert result == {"message": "会话已撤销"}
    mock_session_service.get_session_by_id.assert_awaited_once_with(session_id)
    mock_session_service.revoke_session.assert_awaited_once_with("refresh-token")
