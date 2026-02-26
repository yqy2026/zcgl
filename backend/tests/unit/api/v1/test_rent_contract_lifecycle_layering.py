"""分层约束测试：rent_contract lifecycle 路由应委托服务层。"""

import re
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import ANY, AsyncMock, MagicMock

import pytest

from src.schemas.rent_contract import RentContractCreate, RentTermCreate

pytestmark = pytest.mark.api


def _read_module_source() -> str:
    from src.api.v1.rent_contracts import lifecycle as module

    return Path(module.__file__).read_text(encoding="utf-8")


def _build_contract_create_payload() -> RentContractCreate:
    term = RentTermCreate(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        monthly_rent=Decimal("1000.00"),
    )
    return RentContractCreate(
        contract_number="CT-2026-RENEW-001",
        tenant_name="Tenant A",
        ownership_id="ownership-1",
        asset_ids=["asset-1"],
        sign_date=date(2026, 1, 1),
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        rent_terms=[term],
    )


def test_lifecycle_module_should_not_import_rent_contract_crud_directly() -> None:
    """lifecycle 路由模块不应直接导入 rent_contract CRUD。"""
    module_source = _read_module_source()
    assert "from ....crud.rent_contract" not in module_source
    assert "rent_contract." not in module_source


def test_lifecycle_module_should_import_authz_dependency() -> None:
    """lifecycle 路由应引入统一 ABAC 依赖。"""
    module_source = _read_module_source()
    assert "AuthzContext" in module_source
    assert "require_authz" in module_source


def test_lifecycle_endpoints_should_use_require_authz() -> None:
    """合同续签/终止端点应接入 require_authz。"""
    module_source = _read_module_source()
    expected_patterns = [
        r"async def renew_contract[\s\S]*?require_authz\([\s\S]*?action=\"update\"[\s\S]*?resource_type=\"rent_contract\"[\s\S]*?resource_id=\"\{contract_id\}\"",
        r"async def terminate_contract[\s\S]*?require_authz\([\s\S]*?action=\"update\"[\s\S]*?resource_type=\"rent_contract\"[\s\S]*?resource_id=\"\{contract_id\}\"",
    ]
    for pattern in expected_patterns:
        assert re.search(pattern, module_source), pattern


@pytest.mark.asyncio
async def test_renew_contract_should_delegate_service() -> None:
    """续签接口应委托 rent_contract_service.renew_contract_async。"""
    from src.api.v1.rent_contracts import lifecycle as module
    from src.api.v1.rent_contracts.lifecycle import renew_contract

    mock_service = MagicMock()
    mock_service.renew_contract_async = AsyncMock(return_value=MagicMock(id="contract-new"))

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "rent_contract_service", mock_service)
        result = await renew_contract(
            contract_id="contract-1",
            db=MagicMock(),
            new_contract_data=_build_contract_create_payload(),
            should_transfer_deposit=True,
            current_user=MagicMock(username="tester", id="user-1"),
        )

    assert getattr(result, "id", None) == "contract-new"
    mock_service.renew_contract_async.assert_awaited_once_with(
        db=ANY,
        original_contract_id="contract-1",
        new_contract_data=ANY,
        should_transfer_deposit=True,
        operator="tester",
        operator_id="user-1",
    )


@pytest.mark.asyncio
async def test_terminate_contract_should_delegate_service() -> None:
    """终止接口应委托 rent_contract_service.terminate_contract_async。"""
    from src.api.v1.rent_contracts import lifecycle as module
    from src.api.v1.rent_contracts.lifecycle import terminate_contract

    mock_service = MagicMock()
    mock_service.terminate_contract_async = AsyncMock(
        return_value=MagicMock(id="contract-1")
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "rent_contract_service", mock_service)
        result = await terminate_contract(
            contract_id="contract-1",
            db=MagicMock(),
            termination_date=date(2026, 6, 30),
            should_refund_deposit=True,
            deduction_amount=100.0,
            termination_reason="normal",
            current_user=MagicMock(username="tester", id="user-1"),
        )

    assert getattr(result, "id", None) == "contract-1"
    mock_service.terminate_contract_async.assert_awaited_once_with(
        db=ANY,
        contract_id="contract-1",
        termination_date=date(2026, 6, 30),
        should_refund_deposit=True,
        deduction_amount=Decimal("100.0"),
        termination_reason="normal",
        operator="tester",
        operator_id="user-1",
    )
