"""分层约束测试：backup 路由应委托 BackupService。"""

import inspect
import re
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.api


def test_backup_api_module_should_not_import_crud() -> None:
    """路由层不应直接引入 CRUD 层。"""
    from src.api.v1.system import backup

    module_source = inspect.getsource(backup)
    assert "crud" not in module_source


def test_backup_endpoints_should_use_require_authz() -> None:
    """backup 关键端点应接入 require_authz。"""
    from src.api.v1.system import backup

    module_source = inspect.getsource(backup)
    assert "AuthzContext" in module_source
    assert "require_authz" in module_source
    assert "require_any_role" in module_source

    patterns = [
        r"async def create_backup[\s\S]*?require_authz\([\s\S]*?action=\"create\"[\s\S]*?resource_type=\"backup\"[\s\S]*?resource_context=_BACKUP_CREATE_RESOURCE_CONTEXT",
        r"def list_backups[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"backup\"",
        r"def download_backup[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"backup\"[\s\S]*?resource_id=\"\{backup_name\}\"[\s\S]*?deny_as_not_found=True",
        r"async def restore_backup[\s\S]*?require_authz\([\s\S]*?action=\"update\"[\s\S]*?resource_type=\"backup\"[\s\S]*?resource_id=\"\{backup_name\}\"",
        r"def delete_backup[\s\S]*?require_authz\([\s\S]*?action=\"delete\"[\s\S]*?resource_type=\"backup\"[\s\S]*?resource_id=\"\{backup_name\}\"",
        r"def get_backup_stats[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"backup\"",
        r"def validate_backup[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"backup\"[\s\S]*?resource_id=\"\{backup_name\}\"",
        r"def cleanup_old_backups[\s\S]*?require_authz\([\s\S]*?action=\"delete\"[\s\S]*?resource_type=\"backup\"[\s\S]*?resource_context=_BACKUP_DELETE_RESOURCE_CONTEXT",
    ]
    for pattern in patterns:
        assert re.search(pattern, module_source), pattern


def test_backup_write_authz_context_should_use_unscoped_sentinel() -> None:
    from src.api.v1.system import backup

    expected_create_sentinel = "__unscoped__:backup:create"
    assert backup._BACKUP_CREATE_UNSCOPED_PARTY_ID == expected_create_sentinel
    assert backup._BACKUP_CREATE_RESOURCE_CONTEXT == {
        "party_id": expected_create_sentinel,
        "owner_party_id": expected_create_sentinel,
        "manager_party_id": expected_create_sentinel,
    }

    expected_delete_sentinel = "__unscoped__:backup:delete"
    assert backup._BACKUP_DELETE_UNSCOPED_PARTY_ID == expected_delete_sentinel
    assert backup._BACKUP_DELETE_RESOURCE_CONTEXT == {
        "party_id": expected_delete_sentinel,
        "owner_party_id": expected_delete_sentinel,
        "manager_party_id": expected_delete_sentinel,
    }


def test_list_backups_should_delegate_to_backup_service() -> None:
    """备份列表端点应委托给 BackupService.list_backups。"""
    from src.api.v1.system import backup as module
    from src.api.v1.system.backup import list_backups

    mock_service = MagicMock()
    mock_service.list_backups.return_value = [{"filename": "a.dump"}]

    with pytest.MonkeyPatch.context() as monkeypatch:
        mock_service_cls = MagicMock(return_value=mock_service)
        monkeypatch.setattr(module, "BackupService", mock_service_cls)
        result = list_backups()

    assert result["success"] is True
    assert result["data"] == [{"filename": "a.dump"}]
    mock_service.list_backups.assert_called_once_with()
