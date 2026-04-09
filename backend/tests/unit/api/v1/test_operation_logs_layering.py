"""分层约束测试：operation_logs 路由应通过 Service 协调。"""

import ast
import inspect
import re
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.api


def _get_crud_imports(module_source: str) -> list[str]:
    tree = ast.parse(module_source)
    crud_imports: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module_name = node.module or ""
            if "crud" in module_name.split("."):
                crud_imports.append(module_name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imported_name = alias.name
                if "crud" in imported_name.split("."):
                    crud_imports.append(imported_name)

    return crud_imports


def test_operation_logs_api_module_should_not_import_crud():
    """API 层不应直接依赖 CRUD 模块。"""
    from src.api.v1.system import operation_logs

    module_source = inspect.getsource(operation_logs)
    crud_imports = _get_crud_imports(module_source)

    assert crud_imports == []


def test_operation_logs_endpoints_should_use_require_authz() -> None:
    """operation_logs 关键端点应接入 require_authz。"""
    from src.api.v1.system import operation_logs

    module_source = inspect.getsource(operation_logs)
    assert "AuthzContext" in module_source
    assert "require_authz" in module_source
    assert "require_any_role" in module_source

    patterns = [
        r"async def get_operation_logs[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"operation_log\"",
        r"async def get_operation_log[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"operation_log\"[\s\S]*?resource_id=\"\{log_id\}\"[\s\S]*?deny_as_not_found=True",
        r"async def get_user_operation_statistics[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"operation_log\"",
        r"async def get_module_operation_statistics[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"operation_log\"",
        r"async def get_daily_operation_statistics[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"operation_log\"",
        r"async def get_error_operation_statistics[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"operation_log\"",
        r"async def get_operation_log_summary[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"operation_log\"",
        r"async def export_operation_logs[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"operation_log\"",
        r"async def cleanup_old_logs[\s\S]*?require_authz\([\s\S]*?action=\"delete\"[\s\S]*?resource_type=\"operation_log\"[\s\S]*?resource_context=_OPERATION_LOG_DELETE_RESOURCE_CONTEXT",
    ]
    for pattern in patterns:
        assert re.search(pattern, module_source), pattern


def test_operation_logs_unscoped_delete_context_should_be_defined() -> None:
    from src.api.v1.system import operation_logs as module

    expected_sentinel = "__unscoped__:operation_log:delete"
    assert module._OPERATION_LOG_DELETE_UNSCOPED_PARTY_ID == expected_sentinel
    assert module._OPERATION_LOG_DELETE_RESOURCE_CONTEXT == {
        "party_id": expected_sentinel,
        "owner_party_id": expected_sentinel,
        "manager_party_id": expected_sentinel,
    }


def _build_mock_log() -> MagicMock:
    log = MagicMock()
    log.id = "log-1"
    log.user_id = "user-1"
    log.username = "tester"
    log.action = "create"
    log.action_name = "创建"
    log.module = "asset"
    log.module_name = "资产"
    log.resource_type = "asset"
    log.resource_id = "asset-1"
    log.resource_name = "测试资产"
    log.request_method = "POST"
    log.request_url = "/api/v1/assets"
    log.request_params = None
    log.request_body = None
    log.response_status = 200
    log.response_time = 12
    log.error_message = None
    log.ip_address = "127.0.0.1"
    log.user_agent = "pytest"
    log.details = None
    log.created_at = datetime.now(UTC)
    return log


@pytest.mark.asyncio
async def test_get_operation_logs_should_delegate_to_service(mock_db):
    """日志列表路由应委托给 service。"""
    from src.api.v1.system.operation_logs import get_operation_logs

    mock_service = MagicMock()
    mock_service.get_operation_logs = AsyncMock(return_value=([_build_mock_log()], 1))

    response = await get_operation_logs(
        page=1,
        page_size=20,
        user_id=None,
        action=None,
        module=None,
        resource_type=None,
        response_status=None,
        search=None,
        start_date=None,
        end_date=None,
        db=mock_db,
        current_user=MagicMock(id="user-1"),
        service=mock_service,
    )

    assert response.status_code == 200
    mock_service.get_operation_logs.assert_awaited_once_with(
        db=mock_db,
        page=1,
        page_size=20,
        user_id=None,
        action=None,
        module=None,
        resource_type=None,
        response_status=None,
        search=None,
        start_date=None,
        end_date=None,
    )


@pytest.mark.asyncio
async def test_cleanup_old_logs_should_delegate_to_service(mock_db):
    """清理路由应委托给 service。"""
    from src.api.v1.system.operation_logs import cleanup_old_logs

    mock_service = MagicMock()
    mock_service.cleanup_old_logs = AsyncMock(return_value=5)

    result = await cleanup_old_logs(
        days=90,
        db=mock_db,
        current_user=MagicMock(id="admin-1"),
        service=mock_service,
    )

    assert result["deleted_count"] == 5
    mock_service.cleanup_old_logs.assert_awaited_once_with(db=mock_db, days=90)
