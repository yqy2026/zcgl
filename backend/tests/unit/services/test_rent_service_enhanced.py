"""
租赁合同服务增强测试
"""

from unittest.mock import MagicMock

import pytest

from src.models.rent_contract import RentContract, RentDepositLedger, ServiceFeeLedger
from src.services.rent_contract.service import RentContractService


@pytest.fixture
def rent_service():
    """租赁合同服务实例"""
    return RentContractService()


class TestRentContractServiceBusinessLogic:
    """测试租赁合同服务业务逻辑"""

    def test_get_contract_by_id(self, rent_service, mock_db):
        """测试获取合同详情"""
        mock_contract = MagicMock(spec=RentContract)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_contract

        result = rent_service.get_contract_by_id(
            mock_db, contract_id="contract_123"
        )

        assert result is mock_contract

    def test_get_deposit_ledger(self, rent_service, mock_db):
        """测试获取押金变动记录"""
        mock_ledger = MagicMock(spec=RentDepositLedger)
        (
            mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value
        ) = [mock_ledger]

        result = rent_service.get_deposit_ledger(
            mock_db, contract_id="contract_123"
        )

        assert result == [mock_ledger]

    def test_get_service_fee_ledger(self, rent_service, mock_db):
        """测试获取服务费台账记录"""
        mock_ledger = MagicMock(spec=ServiceFeeLedger)
        (
            mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value
        ) = [mock_ledger]

        result = rent_service.get_service_fee_ledger(
            mock_db, contract_id="contract_123"
        )

        assert result == [mock_ledger]
