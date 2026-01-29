import pytest
from unittest.mock import MagicMock, patch, ANY
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session
from src.services.rent_contract.service import RentContractService
from src.schemas.rent_contract import (
    RentContractCreate,
    RentContractUpdate,
    RentTermCreate,
    GenerateLedgerRequest,
    RentLedgerBatchUpdate,
    RentStatisticsQuery
)
from src.core.enums import ContractStatus, ContractType
from src.models.rent_contract import (
    RentContract,
    RentTerm,
    RentLedger
)
from src.models.asset import Asset

class TestRentContractServiceCoverage:
    @pytest.fixture
    def service(self):
        return RentContractService()

    @pytest.fixture
    def mock_db(self):
        return MagicMock(spec=Session)

    @pytest.fixture
    def mock_asset(self):
        asset = MagicMock(spec=Asset)
        asset.id = "asset_1"
        asset.property_name = "Test Asset"
        asset.rentable_area = Decimal("100.0")
        return asset

    def test_generate_contract_number(self, service, mock_db):
        """Test contract number generation logic"""
        mock_db.query.return_value.filter.return_value.count.return_value = 5
        contract_number = service._generate_contract_number(mock_db)
        today_str = datetime.now().strftime("%Y%m%d")
        expected_number = f"ZJ{today_str}006"
        assert contract_number == expected_number

    def test_create_contract_basic(self, service, mock_db, mock_asset):
        """Test basic contract creation flow"""
        term_data = RentTermCreate(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            monthly_rent=Decimal("1000.00"),
            management_fee=Decimal("100.00")
        )

        contract_data = RentContractCreate(
            contract_number="TEST001",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            sign_date=date(2024, 1, 1),
            ownership_id="owner_1",
            asset_ids=["asset_1"],
            tenant_name="Test Tenant",
            contract_type=ContractType.LEASE_DOWNSTREAM,
            rent_terms=[term_data]
        )

        mock_db.query.return_value.filter.return_value.all.return_value = [mock_asset]

        # Use string path patching for reliability
        with patch('src.services.rent_contract.service.RentContractService._check_asset_rent_conflicts', return_value=[]):
            with patch('src.services.rent_contract.service.model_to_dict', return_value={}):
                result = service.create_contract(mock_db, obj_in=contract_data)

        assert isinstance(result, RentContract)
        mock_db.add.assert_called()
        mock_db.commit.assert_called()

    def test_create_contract_with_conflict(self, service, mock_db):
        """Test conflict detection raises error"""
        term_data = RentTermCreate(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            monthly_rent=Decimal("1000.00")
        )

        contract_data = RentContractCreate(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            sign_date=date(2024, 1, 1),
            ownership_id="owner_1",
            asset_ids=["asset_1"],
            tenant_name="Test Tenant",
            rent_terms=[term_data]
        )

        conflict_info = [{
            "asset_name": "Asset A",
            "contract_number": "OLD001",
            "contract_start_date": "2023-01-01",
            "contract_end_date": "2024-06-01"
        }]

        with patch('src.services.rent_contract.service.RentContractService._check_asset_rent_conflicts', return_value=conflict_info):
            with pytest.raises(ValueError) as excinfo:
                service.create_contract(mock_db, obj_in=contract_data)
            assert "资产租金冲突检测" in str(excinfo.value)

    def test_update_contract(self, service, mock_db, mock_asset):
        """Test contract update logic"""
        db_contract = RentContract(
            id="contract_1",
            contract_number="OLD001",
            assets=[mock_asset]
        )

        update_data = RentContractUpdate(
            tenant_name="Updated Tenant",
            asset_ids=["asset_1"]
        )

        mock_db.query.return_value.filter.return_value.all.return_value = [mock_asset]

        with patch('src.services.rent_contract.service.model_to_dict', return_value={"id": "contract_1"}):
            result = service.update_contract(mock_db, db_obj=db_contract, obj_in=update_data)

        assert result.tenant_name == "Updated Tenant"
        mock_db.commit.assert_called()

    def test_renew_contract(self, service, mock_db):
        """Test contract renewal logic"""
        original_contract = RentContract(
            id="old_1",
            contract_number="OLD001",
            contract_status=ContractStatus.ACTIVE,
            total_deposit=Decimal("5000.00")
        )

        term_data = RentTermCreate(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            monthly_rent=Decimal("1000.00")
        )

        new_contract_data = RentContractCreate(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            sign_date=date(2025, 1, 1),
            ownership_id="owner_1",
            tenant_name="Test Tenant",
            rent_terms=[term_data]
        )

        mock_db.query.return_value.filter.return_value.first.return_value = original_contract
        new_contract_mock = RentContract(id="new_1", contract_number="NEW001")

        with patch('src.services.rent_contract.service.RentContractService.create_contract', return_value=new_contract_mock):
            with patch('src.services.rent_contract.service.model_to_dict', return_value={}):
                 result = service.renew_contract(
                    mock_db,
                    original_contract_id="old_1",
                    new_contract_data=new_contract_data
                )

        assert original_contract.contract_status == ContractStatus.RENEWED
        assert mock_db.add.call_count >= 3
        assert result == new_contract_mock

    def test_terminate_contract(self, service, mock_db):
        """Test contract termination logic"""
        contract = RentContract(
            id="c1",
            contract_status=ContractStatus.ACTIVE,
            total_deposit=Decimal("2000.00")
        )
        mock_db.query.return_value.filter.return_value.first.return_value = contract
        termination_date = date(2024, 6, 30)

        with patch('src.services.rent_contract.service.model_to_dict', return_value={}):
            service.terminate_contract(
                mock_db,
                contract_id="c1",
                termination_date=termination_date,
                should_refund_deposit=True,
                deduction_amount=Decimal("500.00"),
                termination_reason="Early exit"
            )

        assert contract.contract_status == ContractStatus.TERMINATED
        assert contract.end_date == termination_date
        mock_db.commit.assert_called()

    def test_generate_monthly_ledger(self, service, mock_db):
        """Test ledger generation"""
        contract = RentContract(
            id="c1",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 3, 31),
            ownership_id="own1"
        )
        term = RentTerm(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            total_monthly_amount=Decimal("1000.00")
        )

        with patch("src.crud.rent_contract.rent_contract.get", return_value=contract), \
             patch("src.crud.rent_contract.rent_term.get_by_contract", return_value=[term]), \
             patch("src.crud.rent_contract.rent_ledger.get_by_contract_and_month", return_value=None):

            request = GenerateLedgerRequest(contract_id="c1")
            ledgers = service.generate_monthly_ledger(mock_db, request=request)

            assert len(ledgers) == 3
            assert ledgers[0].due_amount == Decimal("1000.00")
            assert ledgers[0].year_month == "2024-01"

    def test_batch_update_payment(self, service, mock_db):
        """Test batch payment update"""
        ledger = RentLedger(
            id="l1",
            due_amount=Decimal("1000.00"),
            paid_amount=Decimal("0"),
            contract_id="c1"
        )
        mock_db.query.return_value.filter.return_value.all.return_value = [ledger]

        request = RentLedgerBatchUpdate(
            ledger_ids=["l1"],
            payment_status="已支付",
            payment_date=date(2024, 1, 5)
        )

        service.batch_update_payment(mock_db, request=request)

        assert ledger.payment_status == "已支付"
        assert ledger.payment_date == date(2024, 1, 5)
        mock_db.commit.assert_called()

    def test_calculate_average_unit_price(self, service, mock_db):
        """Test average unit price calculation"""
        contract = MagicMock(spec=RentContract)
        contract.contract_type = ContractType.LEASE_DOWNSTREAM
        contract.monthly_rent_base = Decimal("5000.00")
        asset = MagicMock(spec=Asset)
        asset.rentable_area = Decimal("100.00")
        contract.assets = [asset]

        mock_db.query.return_value.options.return_value.filter.return_value.all.return_value = [contract]

        query = RentStatisticsQuery()
        avg_price = service._calculate_average_unit_price(mock_db, query)
        assert avg_price == Decimal("50.00")

    def test_calculate_renewal_rate(self, service, mock_db):
        """Test renewal rate calculation"""
        mock_results = [
            (ContractStatus.RENEWED, 2),
            (ContractStatus.EXPIRED, 1),
            (ContractStatus.TERMINATED, 1)
        ]
        mock_db.query.return_value.group_by.return_value.all.return_value = mock_results

        query = RentStatisticsQuery()
        rate = service._calculate_renewal_rate(mock_db, query)
        assert rate == Decimal("50.00")