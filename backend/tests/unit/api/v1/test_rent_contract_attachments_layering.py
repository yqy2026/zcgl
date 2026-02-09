"""分层约束测试：rent_contract attachments 路由应委托服务层。"""

from datetime import datetime
from pathlib import Path
from unittest.mock import ANY, AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.api


def test_attachments_module_should_not_import_crud_directly() -> None:
    """attachments 路由模块不应直接导入 rent_contract CRUD。"""
    from src.api.v1.rent_contracts import attachments as module

    module_source = Path(module.__file__).read_text(encoding="utf-8")
    assert "from ....crud.rent_contract import rent_contract" not in module_source
    assert (
        "from ....crud.rent_contract_attachment import rent_contract_attachment_crud"
        not in module_source
    )
    assert "rent_contract_attachment_crud." not in module_source
    assert "rent_contract.get_async(" not in module_source


@pytest.mark.asyncio
async def test_get_contract_attachments_should_delegate_service_calls() -> None:
    """附件列表接口应委托 rent_contract_service 查询合同与附件。"""
    from src.api.v1.rent_contracts import attachments as module
    from src.api.v1.rent_contracts.attachments import get_contract_attachments

    attachment = MagicMock(
        id="att-1",
        file_name="test.pdf",
        file_size=1024,
        file_type="contract_scan",
        mime_type="application/pdf",
        description="desc",
        uploader="tester",
        created_at=datetime(2026, 1, 1, 0, 0, 0),
    )

    mock_service = MagicMock()
    mock_service.get_contract_by_id_async = AsyncMock(return_value=MagicMock(id="contract-1"))
    mock_service.get_contract_attachments_async = AsyncMock(return_value=[attachment])

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "rent_contract_service", mock_service)
        result = await get_contract_attachments(
            contract_id="contract-1",
            current_user=MagicMock(),
            db=MagicMock(),
        )

    assert len(result) == 1
    assert result[0]["id"] == "att-1"
    mock_service.get_contract_by_id_async.assert_awaited_once_with(
        db=ANY,
        contract_id="contract-1",
    )
    mock_service.get_contract_attachments_async.assert_awaited_once_with(
        db=ANY,
        contract_id="contract-1",
    )


@pytest.mark.asyncio
async def test_delete_contract_attachment_should_delegate_service_calls() -> None:
    """删除附件接口应委托服务层查询并删除附件。"""
    from src.api.v1.rent_contracts import attachments as module
    from src.api.v1.rent_contracts.attachments import delete_contract_attachment

    attachment = MagicMock(file_path="/tmp/not-exists.pdf")
    mock_service = MagicMock()
    mock_service.get_contract_attachment_async = AsyncMock(return_value=attachment)
    mock_service.delete_contract_attachment_async = AsyncMock(return_value=None)

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "rent_contract_service", mock_service)
        monkeypatch.setattr(module.Path, "exists", lambda _self: False)
        result = await delete_contract_attachment(
            contract_id="contract-1",
            attachment_id="att-1",
            current_user=MagicMock(),
            db=MagicMock(),
        )

    assert result["message"] == "附件已删除"
    mock_service.get_contract_attachment_async.assert_awaited_once_with(
        db=ANY,
        attachment_id="att-1",
        contract_id="contract-1",
    )
    mock_service.delete_contract_attachment_async.assert_awaited_once_with(
        db=ANY,
        attachment=attachment,
    )
