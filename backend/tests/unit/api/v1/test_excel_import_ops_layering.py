"""Architecture guards for Excel import upload handling."""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.api


def _read_module_source() -> str:
    from src.api.v1.documents.excel import import_ops

    return Path(import_ops.__file__).read_text(encoding="utf-8")


def test_excel_import_ops_module_should_not_use_crud_adapter_calls() -> None:
    module_source = _read_module_source()
    assert "task_crud." not in module_source
    assert "rollback(" not in module_source
    assert "datetime.utcnow(" not in module_source


def test_excel_import_ops_key_endpoints_should_use_require_authz() -> None:
    module_source = _read_module_source()
    expected_patterns = [
        r"async def import_excel[\s\S]*?require_authz\([\s\S]*?action=\"create\"[\s\S]*?resource_type=\"asset\"[\s\S]*?resource_context=_ASSET_CREATE_RESOURCE_CONTEXT",
        r"async def import_excel_async[\s\S]*?require_authz\([\s\S]*?action=\"create\"[\s\S]*?resource_type=\"asset\"[\s\S]*?resource_context=_ASSET_CREATE_RESOURCE_CONTEXT",
    ]
    for pattern in expected_patterns:
        assert re.search(pattern, module_source), pattern


def test_excel_import_ops_unscoped_create_context_should_be_defined() -> None:
    from src.api.v1.documents.excel import import_ops as module

    expected_sentinel = "__unscoped__:asset:create"
    assert module._ASSET_CREATE_UNSCOPED_PARTY_ID == expected_sentinel
    assert module._ASSET_CREATE_RESOURCE_CONTEXT == {
        "party_id": expected_sentinel,
        "owner_party_id": expected_sentinel,
        "manager_party_id": expected_sentinel,
    }


def test_excel_import_ops_uses_fixed_profile_and_staged_lifecycle() -> None:
    module_source = _read_module_source()
    assert "UploadPurpose.EXCEL_IMPORT" in module_source
    assert "StagedFileService" in module_source
    assert "security_middleware" not in module_source
    assert "await file.read()" not in module_source
