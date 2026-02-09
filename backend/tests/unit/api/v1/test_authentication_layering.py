"""分层约束测试：authentication 路由应委托服务层。"""

import asyncio
import inspect
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Response

from src.core.exception_handler import BaseBusinessError
from src.schemas.auth import LoginRequest

pytestmark = pytest.mark.api


@pytest.fixture
def mock_request():
    request = MagicMock()
    request.client = MagicMock()
    request.client.host = "127.0.0.1"
    request.headers = {"user-agent": "test-agent"}
    return request


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.rollback = AsyncMock()
    return db


def test_authentication_module_should_not_use_crud_adapter_calls() -> None:
    """路由模块不应直接调用 crud.auth。"""
    from src.api.v1.auth.auth_modules import authentication

    module_source = inspect.getsource(authentication)
    assert "from .....crud.auth" not in module_source
    assert "user_crud." not in module_source
    assert "audit_crud." not in module_source


def test_authentication_module_should_not_commit_in_route_layer() -> None:
    """authentication 路由模块不应直接执行 db.commit。"""
    from src.api.v1.auth.auth_modules import authentication

    module_source = inspect.getsource(authentication)
    assert "await db.commit()" not in module_source


def test_login_failed_should_delegate_user_lookup_and_audit_logger(
    mock_request, mock_db
) -> None:
    """登录失败分支应委托用户查询与审计服务。"""
    from src.api.v1.auth.auth_modules.authentication import login

    credentials = LoginRequest(username="testuser", password="wrong-password")
    response = MagicMock(spec=Response)

    with (
        patch(
            "src.api.v1.auth.auth_modules.authentication.AsyncAuthenticationService"
        ) as mock_auth_service_cls,
        patch("src.api.v1.auth.auth_modules.authentication.UserCRUD") as mock_user_cls,
        patch(
            "src.api.v1.auth.auth_modules.authentication.AuditLogCRUD"
        ) as mock_audit_cls,
    ):
        auth_service = mock_auth_service_cls.return_value
        auth_service.authenticate_user = AsyncMock(return_value=None)

        existing_user = MagicMock()
        existing_user.id = "user-1"
        user_repository = mock_user_cls.return_value
        user_repository.get_by_username_async = AsyncMock(return_value=existing_user)

        audit_logger = mock_audit_cls.return_value
        audit_logger.create_async = AsyncMock(return_value=None)

        with pytest.raises(BaseBusinessError) as exc_info:
            asyncio.run(login(mock_request, credentials, response, mock_db))

        assert exc_info.value.code == "AUTHENTICATION_ERROR"
        user_repository.get_by_username_async.assert_awaited_once_with(
            mock_db, "testuser"
        )
        audit_logger.create_async.assert_awaited_once()
