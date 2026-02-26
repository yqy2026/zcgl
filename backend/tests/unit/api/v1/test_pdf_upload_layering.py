"""分层约束测试：pdf_upload 路由应走统一 ABAC 依赖。"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.api


def _read_module_source() -> str:
    from src.api.v1.documents import pdf_upload as module

    return Path(module.__file__).read_text(encoding="utf-8")


def test_pdf_upload_module_should_not_import_session_crud_directly() -> None:
    """pdf_upload 路由模块不应直接导入 PDFImportSessionCRUD。"""
    module_source = _read_module_source()
    assert "from ....crud.pdf_import_session import PDFImportSessionCRUD" not in module_source
    assert "PDFImportSessionCRUD(" not in module_source


def test_upload_pdf_file_endpoint_should_use_require_authz() -> None:
    """pdf 上传端点应接入统一 ABAC 依赖。"""
    module_source = _read_module_source()
    expected_pattern = (
        r"async def upload_pdf_file[\s\S]*?require_authz\("
        r"[\s\S]*?action=\"create\"[\s\S]*?resource_type=\"rent_contract\""
        r"[\s\S]*?resource_context=_RENT_CONTRACT_CREATE_RESOURCE_CONTEXT"
    )
    assert re.search(expected_pattern, module_source), expected_pattern


def test_pdf_upload_unscoped_create_context_should_be_defined() -> None:
    from src.api.v1.documents import pdf_upload as module

    expected_sentinel = "__unscoped__:rent_contract:create"
    assert module._RENT_CONTRACT_CREATE_UNSCOPED_PARTY_ID == expected_sentinel
    assert module._RENT_CONTRACT_CREATE_RESOURCE_CONTEXT == {
        "party_id": expected_sentinel,
        "owner_party_id": expected_sentinel,
        "manager_party_id": expected_sentinel,
    }
