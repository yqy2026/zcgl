"""分层约束测试：pdf_upload 路由应走统一 ABAC 依赖。"""

import re
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

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
        r"[\s\S]*?action=\"create\"[\s\S]*?resource_type=\"contract\""
        r"[\s\S]*?resource_context=_CONTRACT_CREATE_RESOURCE_CONTEXT"
    )
    assert re.search(expected_pattern, module_source), expected_pattern


def test_confirm_import_endpoint_should_be_exposed_on_confirm_path() -> None:
    """pdf 确认导入端点应暴露在 /confirm，而不是 legacy /confirm_import。"""
    module_source = _read_module_source()
    assert '@router.post("/confirm"' in module_source
    assert 'confirm_import"' not in module_source


def test_pdf_upload_unscoped_create_context_should_be_defined() -> None:
    from src.api.v1.documents import pdf_upload as module

    expected_sentinel = "__unscoped__:contract:create"
    assert module._CONTRACT_CREATE_UNSCOPED_PARTY_ID == expected_sentinel
    assert module._CONTRACT_CREATE_RESOURCE_CONTEXT == {
        "party_id": expected_sentinel,
        "owner_party_id": expected_sentinel,
        "manager_party_id": expected_sentinel,
    }


@pytest.mark.asyncio
async def test_confirm_import_endpoint_should_forward_string_user_id_to_service() -> None:
    from src.api.v1.documents import pdf_upload as module
    from src.schemas.pdf_import import ConfirmImportRequest

    payload = ConfirmImportRequest(
        session_id="session-123",
        confirmed_data={"contract_number": "HT-001"},
    )
    db = AsyncMock()
    current_user = MagicMock(id="550e8400-e29b-41d4-a716-446655440000")
    pdf_service = MagicMock()
    pdf_service.confirm_import = AsyncMock(
        return_value={
            "success": True,
            "message": "ok",
            "contract_group_id": "group-123",
            "contract_id": "contract-456",
        }
    )

    result = await module.confirm_import(
        payload=payload,
        db=db,
        pdf_service=pdf_service,
        current_user=current_user,
        _authz_ctx=MagicMock(),
    )

    assert result.contract_group_id == "group-123"
    assert result.contract_id == "contract-456"
    pdf_service.confirm_import.assert_awaited_once_with(
        db,
        payload.session_id,
        payload.confirmed_data,
        user_id="550e8400-e29b-41d4-a716-446655440000",
    )
