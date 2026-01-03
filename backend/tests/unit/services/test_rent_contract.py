from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from src.models.rent_contract import RentContract, RentLedger, RentTerm
from src.schemas.rent_contract import (
    GenerateLedgerRequest,
    RentContractCreate,
    RentContractUpdate,
    RentLedgerBatchUpdate,
    RentTermCreate,
    RentTermUpdate,
)
from src.services.rent_contract.service import RentContractService

# Constants for testing
TEST_CONTRACT_ID = "contract_123"
TEST_ASSET_ID = "asset_123"
TEST_OWNERSHIP_ID = "ownership_123"


@pytest.fixture
def mock_db():
    return MagicMock(spec=Session)


@pytest.fixture
def service():
    return RentContractService()


class TestRentContractService:
    def test_create_contract(self, service, mock_db):
        # Prepare input data
        term_data = RentTermCreate(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            monthly_rent=Decimal("1000"),
            management_fee=Decimal("100"),
        )
        contract_in = RentContractCreate(
            contract_number="TEST2024001",
            tenant_name="Test Tenant",
            asset_id=TEST_ASSET_ID,
            ownership_id=TEST_OWNERSHIP_ID,
            sign_date=date(2024, 1, 1),
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            rent_terms=[term_data],
        )

        # Mock internal methods
        service._generate_contract_number = MagicMock(return_value="TEST2024001")
        service._create_history = MagicMock()

        # Execute
        result = service.create_contract(mock_db, obj_in=contract_in)

        # Verify
        assert isinstance(result, RentContract)
        assert result.contract_number == "TEST2024001"
        assert len(result.rent_terms) == 0  # In unit test with mocked add, relations might not link automatically unless logic does it
        # However, our service creates RentTerm and adds it to DB.
        
        # Check DB calls
        # 1 add for contract, 1 add for term, 1 for history (inside _create_history)
        # Actually _create_history also does add/commit.
        
        # Verify contract creation
        contract_add_call = mock_db.add.call_args_list[0]
        assert isinstance(contract_add_call[0][0], RentContract)
        
        # Verify term creation
        term_add_call = mock_db.add.call_args_list[1]
        assert isinstance(term_add_call[0][0], RentTerm)
        assert term_add_call[0][0].monthly_rent == Decimal("1000")
        assert term_add_call[0][0].total_monthly_amount == Decimal("1100") # 1000 + 100

        mock_db.commit.assert_called()
        mock_db.flush.assert_called()

    def test_update_contract(self, service, mock_db):
        # Prepare
        db_obj = RentContract(
            id=TEST_CONTRACT_ID,
            contract_number="OLD123",
            tenant_name="Old Name",
            rent_terms=[]
        )
        update_in = RentContractUpdate(
            tenant_name="New Name",
            rent_terms=[
                RentTermUpdate(
                    start_date=date(2025, 1, 1),
                    end_date=date(2025, 12, 31),
                    monthly_rent=Decimal("2000")
                )
            ]
        )
        
        service._create_history = MagicMock()
        
        # Mock query return for deleting terms
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        
        # Execute
        result = service.update_contract(mock_db, db_obj=db_obj, obj_in=update_in)
        
        # Verify
        assert result.tenant_name == "New Name"
        mock_query.delete.assert_called() # Terms deleted
        
        # New term added
        # mock_db.add called for term and contract update
        # We expect at least one add for term.
        # db.add(db_obj) is also called.
        
        term_added = False
        for call in mock_db.add.call_args_list:
            if isinstance(call[0][0], RentTerm):
                term_added = True
                assert call[0][0].monthly_rent == Decimal("2000")
        assert term_added

    @patch("src.services.rent_contract.service.rent_contract")
    @patch("src.services.rent_contract.service.rent_term")
    @patch("src.services.rent_contract.service.rent_ledger")
    def test_generate_monthly_ledger(self, mock_ledger_crud, mock_term_crud, mock_contract_crud, service, mock_db):
        # Prepare mocks
        contract = RentContract(
            id=TEST_CONTRACT_ID,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 3, 31), # 3 months
            asset_id=TEST_ASSET_ID,
            ownership_id=TEST_OWNERSHIP_ID
        )
        mock_contract_crud.get.return_value = contract
        
        term = RentTerm(
            contract_id=TEST_CONTRACT_ID,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            monthly_rent=Decimal("1000"),
            total_monthly_amount=Decimal("1000")
        )
        mock_term_crud.get_by_contract.return_value = [term]
        
        # Assume no existing ledgers
        mock_ledger_crud.get_by_contract_and_month.return_value = None
        
        request = GenerateLedgerRequest(contract_id=TEST_CONTRACT_ID)
        
        # Execute
        result = service.generate_monthly_ledger(mock_db, request=request)
        
        # Verify
        assert len(result) == 3 # Jan, Feb, Mar
        assert result[0].year_month == "2024-01"
        assert result[0].due_amount == Decimal("1000")
        
        mock_db.add.call_count == 3
        mock_db.commit.assert_called()

    def test_batch_update_payment(self, service, mock_db):
        # Prepare
        ledger1 = RentLedger(id="1", due_amount=Decimal("1000"), paid_amount=Decimal("0"), payment_status="未支付")
        ledger2 = RentLedger(id="2", due_amount=Decimal("1000"), paid_amount=Decimal("500"), payment_status="部分支付")
        
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [ledger1, ledger2]
        
        request = RentLedgerBatchUpdate(
            ledger_ids=["1", "2"],
            payment_status="已支付",
            notes="Batch update"
        )
        
        # Execute
        result = service.batch_update_payment(mock_db, request=request)
        
        # Verify
        assert ledger1.payment_status == "已支付"
        assert ledger1.notes == "Batch update"
        # Logic: if "已支付", overdue should be calc.
        # But paid_amount didn't change in update request?
        # The service logic checks: 
        # if ledger.paid_amount < ledger.due_amount:
        #    ledger.overdue_amount = (ledger.due_amount - ledger.paid_amount)
        
        assert ledger1.overdue_amount == Decimal("1000") # Because paid is 0
        assert ledger2.overdue_amount == Decimal("500") # Because paid is 500
        
        mock_db.commit.assert_called()
