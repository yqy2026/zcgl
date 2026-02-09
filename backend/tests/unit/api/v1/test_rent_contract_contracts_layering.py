"""分层约束测试：rent_contract contracts 路由应委托服务层。"""

import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import ANY, AsyncMock, MagicMock

import pytest

from src.schemas.rent_contract import RentContractCreate, RentTermCreate

pytestmark = pytest.mark.api


def _build_contract_create_payload() -> RentContractCreate:
    term = RentTermCreate(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        monthly_rent=Decimal("1000.00"),
    )
    return RentContractCreate(
        contract_number="CT-2026-001",
        tenant_name="Tenant A",
        ownership_id="ownership-1",
        asset_ids=["asset-1"],
        sign_date=date(2026, 1, 1),
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        rent_terms=[term],
    )


def test_contracts_module_should_not_import_crud_directly() -> None:
    """contracts 路由模块不应直接导入 asset/ownership/rent_contract CRUD。"""
    from src.api.v1.rent_contracts import contracts as module

    module_source = Path(module.__file__).read_text(encoding="utf-8")
    assert "from ....crud.asset import asset_crud" not in module_source
    assert "from ....crud.ownership import ownership" not in module_source
    assert "from ....crud.rent_contract import rent_contract" not in module_source
    assert "asset_crud." not in module_source
    assert "ownership." not in module_source
    assert "rent_contract." not in module_source


@pytest.mark.asyncio
async def test_create_contract_should_delegate_service_validation_and_create() -> None:
    """创建合同应委托服务层做资产/权属校验与创建。"""
    from src.api.v1.rent_contracts import contracts as module
    from src.api.v1.rent_contracts.contracts import create_contract

    mock_service = MagicMock()
    mock_service.get_assets_by_ids_async = AsyncMock(return_value=[MagicMock(id="asset-1")])
    mock_service.get_ownership_by_id_async = AsyncMock(return_value=MagicMock(id="ownership-1"))
    mock_service.create_contract_async = AsyncMock(return_value=MagicMock(id="contract-1"))

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "rent_contract_service", mock_service)
        result = await create_contract(
            db=MagicMock(),
            contract_in=_build_contract_create_payload(),
            current_user=MagicMock(),
        )

    assert getattr(result, "id", None) == "contract-1"
    mock_service.get_assets_by_ids_async.assert_awaited_once_with(
        db=ANY,
        asset_ids=["asset-1"],
    )
    mock_service.get_ownership_by_id_async.assert_awaited_once_with(
        db=ANY,
        ownership_id="ownership-1",
    )
    mock_service.create_contract_async.assert_awaited_once_with(
        db=ANY,
        obj_in=ANY,
    )


@pytest.mark.asyncio
async def test_get_contracts_should_delegate_service_query() -> None:
    """合同列表接口应委托服务层分页查询。"""
    from src.api.v1.rent_contracts import contracts as module
    from src.api.v1.rent_contracts.contracts import get_contracts

    mock_service = MagicMock()
    mock_service.get_contract_page_async = AsyncMock(return_value=([MagicMock(id="c-1")], 1))

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "rent_contract_service", mock_service)
        monkeypatch.setattr(
            module.RentContractResponse,
            "model_validate",
            staticmethod(lambda _: {"id": "c-1"}),
        )
        response = await get_contracts(
            db=MagicMock(),
            current_user=MagicMock(),
            page=2,
            page_size=10,
            contract_number="CT",
            tenant_name="Tenant",
            asset_id="asset-1",
            ownership_id="ownership-1",
            contract_status="ACTIVE",
            start_date=None,
            end_date=None,
        )

    body = json.loads(response.body.decode())
    assert body["data"]["pagination"]["page"] == 2
    assert body["data"]["pagination"]["total"] == 1
    mock_service.get_contract_page_async.assert_awaited_once_with(
        db=ANY,
        skip=10,
        limit=10,
        contract_number="CT",
        tenant_name="Tenant",
        asset_id="asset-1",
        ownership_id="ownership-1",
        contract_status="ACTIVE",
        start_date=None,
        end_date=None,
    )

