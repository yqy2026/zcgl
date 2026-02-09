"""分层约束测试：rent_contract ledger 路由应委托服务层。"""

import json
from pathlib import Path
from unittest.mock import ANY, AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.api


def test_ledger_module_should_not_import_rent_ledger_crud_directly() -> None:
    """ledger 路由模块不应直接导入 rent_ledger。"""
    from src.api.v1.rent_contracts import ledger as module

    module_source = Path(module.__file__).read_text(encoding="utf-8")
    assert "from ....crud.rent_contract import rent_ledger" not in module_source
    assert "rent_ledger." not in module_source


@pytest.mark.asyncio
async def test_get_rent_ledger_should_delegate_service_query() -> None:
    """租金台账列表接口应委托 rent_contract_service.get_rent_ledger_page_async。"""
    from src.api.v1.rent_contracts import ledger as module
    from src.api.v1.rent_contracts.ledger import get_rent_ledger

    mock_service = MagicMock()
    mock_service.get_rent_ledger_page_async = AsyncMock(return_value=([MagicMock()], 1))

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "rent_contract_service", mock_service)
        monkeypatch.setattr(
            module.RentLedgerResponse,
            "model_validate",
            staticmethod(lambda _: {"id": "ledger-1"}),
        )
        response = await get_rent_ledger(
            db=MagicMock(),
            current_user=MagicMock(),
            page=1,
            page_size=10,
            contract_id=None,
            asset_id=None,
            ownership_id=None,
            year_month=None,
            payment_status=None,
            start_date=None,
            end_date=None,
        )

    payload = json.loads(response.body)
    assert payload["data"]["pagination"]["total"] == 1
    mock_service.get_rent_ledger_page_async.assert_awaited_once_with(
        db=ANY,
        skip=0,
        limit=10,
        contract_id=None,
        asset_id=None,
        ownership_id=None,
        year_month=None,
        payment_status=None,
        start_date=None,
        end_date=None,
    )


@pytest.mark.asyncio
async def test_get_rent_ledger_detail_should_delegate_service_lookup() -> None:
    """台账详情接口应委托 rent_contract_service.get_rent_ledger_by_id_async。"""
    from src.api.v1.rent_contracts import ledger as module
    from src.api.v1.rent_contracts.ledger import get_rent_ledger_detail

    mock_service = MagicMock()
    mock_service.get_rent_ledger_by_id_async = AsyncMock(return_value=MagicMock(id="ledger-1"))

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "rent_contract_service", mock_service)
        result = await get_rent_ledger_detail(
            ledger_id="ledger-1",
            db=MagicMock(),
            current_user=MagicMock(),
        )

    assert getattr(result, "id", None) == "ledger-1"
    mock_service.get_rent_ledger_by_id_async.assert_awaited_once_with(
        db=ANY,
        ledger_id="ledger-1",
    )


@pytest.mark.asyncio
async def test_get_contract_ledger_should_delegate_service_query() -> None:
    """合同台账接口应委托 rent_contract_service.get_contract_ledger_async。"""
    from src.api.v1.rent_contracts import ledger as module
    from src.api.v1.rent_contracts.ledger import get_contract_ledger

    mock_service = MagicMock()
    mock_service.get_contract_ledger_async = AsyncMock(return_value=[MagicMock(id="ledger-1")])

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "rent_contract_service", mock_service)
        result = await get_contract_ledger(
            contract_id="contract-1",
            db=MagicMock(),
            current_user=MagicMock(),
        )

    assert len(result) == 1
    mock_service.get_contract_ledger_async.assert_awaited_once_with(
        db=ANY,
        contract_id="contract-1",
        limit=1000,
    )
