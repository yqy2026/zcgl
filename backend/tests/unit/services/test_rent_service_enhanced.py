"""
租赁合同服务增强测试
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.rent_contract import RentContract, RentDepositLedger, ServiceFeeLedger
from src.services.rent_contract.service import RentContractService


@pytest.fixture
def rent_service():
    """租赁合同服务实例"""
    return RentContractService()


class TestRentContractServiceBusinessLogic:
    """测试租赁合同服务业务逻辑"""

    @pytest.mark.asyncio
    async def test_get_contract_by_id(self, rent_service, mock_db):
        """测试获取合同详情"""
        mock_contract = MagicMock(spec=RentContract)
        with patch(
            "src.services.rent_contract.service.rent_contract_crud.get_async",
            new=AsyncMock(return_value=mock_contract),
        ) as mock_get:
            result = await rent_service.get_contract_by_id_async(
                mock_db, contract_id="contract_123"
            )

        assert result is mock_contract
        mock_get.assert_awaited_once_with(mock_db, id="contract_123")

    @pytest.mark.asyncio
    async def test_get_deposit_ledger(self, rent_service, mock_db):
        """测试获取押金变动记录"""
        mock_ledger = MagicMock(spec=RentDepositLedger)
        with patch(
            "src.services.rent_contract.ledger_service.rent_ledger.get_deposit_ledger_by_contract_async",
            new=AsyncMock(return_value=[mock_ledger]),
        ) as mock_get:
            result = await rent_service.get_deposit_ledger_async(
                mock_db, contract_id="contract_123"
            )

        assert result == [mock_ledger]
        mock_get.assert_awaited_once_with(
            mock_db,
            contract_id="contract_123",
        )

    @pytest.mark.asyncio
    async def test_get_service_fee_ledger(self, rent_service, mock_db):
        """测试获取服务费台账记录"""
        mock_ledger = MagicMock(spec=ServiceFeeLedger)
        with patch(
            "src.services.rent_contract.ledger_service.rent_ledger.get_service_fee_ledger_by_contract_async",
            new=AsyncMock(return_value=[mock_ledger]),
        ) as mock_get:
            result = await rent_service.get_service_fee_ledger_async(
                mock_db, contract_id="contract_123"
            )

        assert result == [mock_ledger]
        mock_get.assert_awaited_once_with(
            mock_db,
            contract_id="contract_123",
        )
