"""分层约束测试：auth audit 路由应委托服务层。"""

import inspect
import re
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.api


def test_auth_audit_module_should_not_use_crud_adapter_calls() -> None:
    """路由模块不应直接调用 audit_crud。"""
    from src.api.v1.auth.auth_modules import audit

    module_source = inspect.getsource(audit)
    assert "audit_crud." not in module_source


def test_auth_audit_module_should_import_authz_dependency() -> None:
    """audit 路由应引入统一 ABAC 依赖。"""
    from src.api.v1.auth.auth_modules import audit

    module_source = inspect.getsource(audit)
    assert "AuthzContext" in module_source
    assert "require_authz" in module_source


def test_auth_audit_endpoint_should_use_require_authz() -> None:
    """审计统计端点应接入 require_authz。"""
    from src.api.v1.auth.auth_modules import audit

    module_source = inspect.getsource(audit)
    pattern = (
        r"async def get_audit_statistics[\s\S]*?require_authz\("
        r"[\s\S]*?action=\"read\"[\s\S]*?resource_type=\"operation_log\""
    )
    assert re.search(pattern, module_source), pattern


@pytest.mark.asyncio
async def test_get_audit_statistics_should_delegate_audit_service() -> None:
    """审计统计路由应委托 audit_service.get_login_statistics。"""
    from src.api.v1.auth.auth_modules.audit import get_audit_statistics

    mock_audit_service = MagicMock()
    mock_audit_service.get_login_statistics = AsyncMock(
        return_value={
            "total_logins": 10,
            "successful_logins": 9,
            "failed_logins": 1,
            "success_rate": 90.0,
        }
    )

    result = await get_audit_statistics(
        days=30,
        db=MagicMock(),
        current_user=MagicMock(),
        audit_service=mock_audit_service,
    )

    assert result["total_logins"] == 10
    mock_audit_service.get_login_statistics.assert_awaited_once_with(days=30)
