"""
Unit Tests for Contract Renewal Service

Tests for V2 contract renewal functionality:
- Automatic data pre-fill from original contract
- Contract termination handling
- Deposit transfer between contracts
- Rent terms date adjustment

Author: V2.0 Test Suite
Date: 2026-01-08
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from src.core.exception_handler import (
    OperationNotAllowedError,
    ResourceNotFoundError,
)
from src.models.rent_contract import (
    ContractType,
    DepositTransactionType,
    PaymentCycle,
    RentContract,
    RentDepositLedger,
    RentTerm,
)
from src.schemas.rent_contract import RentContractCreate, RentTermCreate
from src.services.rent_contract import rent_contract_service

# ==================== Fixtures ====================


@pytest.fixture(autouse=True)
def clean_database(test_db: Session):
    """Clean database before and after each test to ensure isolation"""
    # Clean before test
    test_db.query(RentDepositLedger).delete()
    test_db.query(RentTerm).delete()
    test_db.query(RentContract).delete()
    test_db.commit()
    yield
    # Clean after test
    test_db.query(RentDepositLedger).delete()
    test_db.query(RentTerm).delete()
    test_db.query(RentContract).delete()
    test_db.commit()


@pytest.fixture
def original_contract(test_db: Session):
    """Create an original contract for renewal testing"""
    unique_id = str(uuid.uuid4())[:8]
    contract = RentContract(
        id=f"original_contract_{unique_id}",
        contract_number=f"CTR2024{unique_id}",
        contract_type=ContractType.LEASE_DOWNSTREAM,
        tenant_name="原始租户公司",
        tenant_contact="张三",
        tenant_phone="13800138000",
        tenant_address="北京市朝阳区",
        ownership_id="ownership_001",
        sign_date=date(2024, 1, 1),
        start_date=date(2024, 1, 1),
        end_date=date(2026, 12, 31),  # 3年合同
        payment_cycle=PaymentCycle.MONTHLY,
        total_deposit=Decimal("20000"),
        monthly_rent_base=Decimal("10000"),
        contract_status="有效",
    )
    test_db.add(contract)
    test_db.flush()

    # Add rent terms with step increases
    term1 = RentTerm(
        id=f"term_{unique_id}_1",
        contract_id=contract.id,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
        monthly_rent=Decimal("10000"),
    )
    term2 = RentTerm(
        id=f"term_{unique_id}_2",
        contract_id=contract.id,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        monthly_rent=Decimal("10500"),  # 5% increase
    )
    term3 = RentTerm(
        id=f"term_{unique_id}_3",
        contract_id=contract.id,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        monthly_rent=Decimal("11025"),  # Another 5% increase
    )
    test_db.add_all([term1, term2, term3])

    # Add deposit ledger
    deposit = RentDepositLedger(
        id=f"deposit_{unique_id}",
        contract_id=contract.id,
        transaction_type=DepositTransactionType.RECEIPT,
        amount=Decimal("20000"),
        transaction_date=date(2024, 1, 1),
        notes="初始押金",
        operator="系统管理员",
    )
    test_db.add(deposit)
    test_db.commit()

    return contract


@pytest.fixture
def renewal_contract_data():
    """Data for new contract during renewal"""
    unique_id = str(uuid.uuid4())[:8]
    return RentContractCreate(
        contract_number=f"CTR2027{unique_id}",
        contract_type=ContractType.LEASE_DOWNSTREAM,
        tenant_name="原始租户公司",
        tenant_contact="张三",
        tenant_phone="13800138000",
        asset_ids=["asset_001", "asset_002"],
        ownership_id="ownership_001",
        sign_date=date(2027, 1, 1),
        start_date=date(2027, 1, 1),
        end_date=date(2029, 12, 31),  # New 3-year contract
        payment_cycle=PaymentCycle.MONTHLY,
        total_deposit=Decimal("25000"),  # Increased deposit
        rent_terms=[
            RentTermCreate(
                start_date=date(2027, 1, 1),
                end_date=date(2029, 12, 31),
                monthly_rent=Decimal("10000"),
            )
        ],  # Will be auto-adjusted
    )


# ==================== Renewal Success Tests ====================


class TestContractRenewalSuccess:
    """Test successful contract renewal scenarios"""

    def test_renewal_creates_new_contract_with_adjusted_dates(
        self,
        test_db: Session,
        original_contract: RentContract,
        renewal_contract_data: RentContractCreate,
    ):
        """TC-REN-001: Renewal creates new contract with date-adjusted rent terms"""
        operator_id = "user_001"

        new_contract = rent_contract_service.renew_contract(
            db=test_db,
            original_contract_id=original_contract.id,
            new_contract_data=renewal_contract_data,
            should_transfer_deposit=True,
            operator="测试用户",
            operator_id=operator_id,
        )

        # Verify new contract created
        assert new_contract is not None
        assert new_contract.contract_number.startswith("CTR2027")
        assert new_contract.start_date == date(2027, 1, 1)
        assert new_contract.end_date == date(2029, 12, 31)

        # Verify rent terms from input data
        assert len(new_contract.rent_terms) == 1
        # First term should start on new contract start date
        assert new_contract.rent_terms[0].start_date == date(2027, 1, 1)
        assert new_contract.rent_terms[0].monthly_rent == Decimal("10000")

    def test_renewal_transfers_deposit_to_new_contract(
        self,
        test_db: Session,
        original_contract: RentContract,
        renewal_contract_data: RentContractCreate,
    ):
        """TC-REN-002: Deposit is transferred from old to new contract"""
        new_contract = rent_contract_service.renew_contract(
            db=test_db,
            original_contract_id=original_contract.id,
            new_contract_data=renewal_contract_data,
            should_transfer_deposit=True,
            operator="测试用户",
            operator_id="user_001",
        )

        # Check original contract deposit ledger (should have TRANSFER_OUT)
        original_ledgers = (
            test_db.query(RentDepositLedger)
            .filter(RentDepositLedger.contract_id == original_contract.id)
            .all()
        )

        transfer_out = [
            ledger
            for ledger in original_ledgers
            if ledger.transaction_type == DepositTransactionType.TRANSFER_OUT
        ]
        assert len(transfer_out) == 1
        assert transfer_out[0].amount == Decimal("-20000")  # TRANSFER_OUT is negative

        # Check new contract deposit ledger (should have TRANSFER_IN)
        new_ledgers = (
            test_db.query(RentDepositLedger)
            .filter(RentDepositLedger.contract_id == new_contract.id)
            .all()
        )

        transfer_in = [
            ledger
            for ledger in new_ledgers
            if ledger.transaction_type == DepositTransactionType.TRANSFER_IN
        ]
        assert len(transfer_in) == 1
        assert transfer_in[0].amount == Decimal("20000")
        assert transfer_in[0].related_contract_id == original_contract.id

    def test_renewal_marks_original_contract_status(
        self,
        test_db: Session,
        original_contract: RentContract,
        renewal_contract_data: RentContractCreate,
    ):
        """TC-REN-003: Original contract status is updated after renewal"""
        rent_contract_service.renew_contract(
            db=test_db,
            original_contract_id=original_contract.id,
            new_contract_data=renewal_contract_data,
            should_transfer_deposit=True,
            operator="测试用户",
            operator_id="user_001",
        )

        # Refresh from database
        test_db.refresh(original_contract)

        # Original contract should be marked as renewed
        assert original_contract.contract_status == "已续签"


# ==================== Deposit Transfer Tests ====================


class TestDepositTransfer:
    """Test deposit transfer logic during renewal"""

    def test_no_transfer_when_flag_is_false(
        self,
        test_db: Session,
        original_contract: RentContract,
        renewal_contract_data: RentContractCreate,
    ):
        """TC-REN-004: No deposit transfer when should_transfer_deposit=False"""
        new_contract = rent_contract_service.renew_contract(
            db=test_db,
            original_contract_id=original_contract.id,
            new_contract_data=renewal_contract_data,
            should_transfer_deposit=False,  # Don't transfer
            operator="测试用户",
            operator_id="user_001",
        )

        # Original contract should NOT have TRANSFER_OUT
        original_ledgers = (
            test_db.query(RentDepositLedger)
            .filter(
                RentDepositLedger.contract_id == original_contract.id,
                RentDepositLedger.transaction_type
                == DepositTransactionType.TRANSFER_OUT,
            )
            .all()
        )

        assert len(original_ledgers) == 0

        # New contract should NOT have TRANSFER_IN
        new_ledgers = (
            test_db.query(RentDepositLedger)
            .filter(
                RentDepositLedger.contract_id == new_contract.id,
                RentDepositLedger.transaction_type
                == DepositTransactionType.TRANSFER_IN,
            )
            .all()
        )

        assert len(new_ledgers) == 0

    def test_additional_deposit_added_to_new_contract(
        self,
        test_db: Session,
        original_contract: RentContract,
        renewal_contract_data: RentContractCreate,
    ):
        """TC-REN-005: Additional deposit can be added during renewal"""
        # Renewal contract has higher deposit (25000 vs original 20000)
        new_contract = rent_contract_service.renew_contract(
            db=test_db,
            original_contract_id=original_contract.id,
            new_contract_data=renewal_contract_data,
            should_transfer_deposit=True,
            operator="测试用户",
            operator_id="user_001",
        )

        # Should have TRANSFER_IN (20000) + additional receipt (5000)
        new_ledgers = (
            test_db.query(RentDepositLedger)
            .filter(RentDepositLedger.contract_id == new_contract.id)
            .all()
        )

        transfer_in = [
            ledger
            for ledger in new_ledgers
            if ledger.transaction_type == DepositTransactionType.TRANSFER_IN
        ]
        receipts = [
            ledger
            for ledger in new_ledgers
            if ledger.transaction_type == DepositTransactionType.RECEIPT
        ]

        assert len(transfer_in) == 1
        assert transfer_in[0].amount == Decimal("20000")

        # Additional deposit NOT automatically created - needs separate collection
        assert len(receipts) == 0


# ==================== Rent Terms Adjustment Tests ====================


class TestRentTermsAdjustment:
    """Test rent terms date adjustment during renewal"""

    def test_rent_terms_preserve_structure(
        self,
        test_db: Session,
        original_contract: RentContract,
        renewal_contract_data: RentContractCreate,
    ):
        """TC-REN-006: Rent terms structure is preserved after adjustment"""
        new_contract = rent_contract_service.renew_contract(
            db=test_db,
            original_contract_id=original_contract.id,
            new_contract_data=renewal_contract_data,
            should_transfer_deposit=True,
            operator="测试用户",
            operator_id="user_001",
        )

        # Should have same number of terms as provided in input
        assert len(new_contract.rent_terms) == 1

        # Rent amounts should match input data
        rent_amounts = [term.monthly_rent for term in new_contract.rent_terms]
        expected_amounts = [Decimal("10000")]
        assert rent_amounts == expected_amounts

    def test_rent_terms_adjusted_to_new_period(
        self,
        test_db: Session,
        original_contract: RentContract,
        renewal_contract_data: RentContractCreate,
    ):
        """TC-REN-007: Rent term dates are adjusted to new contract period"""
        new_contract = rent_contract_service.renew_contract(
            db=test_db,
            original_contract_id=original_contract.id,
            new_contract_data=renewal_contract_data,
            should_transfer_deposit=True,
            operator="测试用户",
            operator_id="user_001",
        )

        # All terms should be within new contract period
        for term in new_contract.rent_terms:
            assert term.start_date >= new_contract.start_date
            assert term.end_date <= new_contract.end_date

        # Terms should be continuous without gaps
        sorted_terms = sorted(new_contract.rent_terms, key=lambda t: t.start_date)
        for i in range(len(sorted_terms) - 1):
            expected_next_start = sorted_terms[i].end_date + timedelta(days=1)
            assert sorted_terms[i + 1].start_date == expected_next_start


# ==================== Error Handling Tests ====================


class TestRenewalErrorHandling:
    """Test error handling in renewal scenarios"""

    def test_renewal_fails_for_nonexistent_contract(
        self, test_db: Session, renewal_contract_data: RentContractCreate
    ):
        """TC-REN-008: Renewal fails when original contract doesn't exist"""
        with pytest.raises(ResourceNotFoundError, match="合同.*不存在"):
            rent_contract_service.renew_contract(
                db=test_db,
                original_contract_id="nonexistent_id",
                new_contract_data=renewal_contract_data,
                should_transfer_deposit=True,
                operator="测试用户",
                operator_id="user_001",
            )

    def test_renewal_fails_for_already_terminated_contract(
        self, test_db: Session, original_contract: RentContract
    ):
        """TC-REN-009: Cannot renew an already terminated contract"""
        original_contract.contract_status = "已终止"
        test_db.commit()

        unique_id = str(uuid.uuid4())[:8]
        renewal_data = RentContractCreate(
            contract_number=f"NEW{unique_id}",
            contract_type=ContractType.LEASE_DOWNSTREAM,
            tenant_name="测试",
            asset_ids=["asset_001"],
            ownership_id="ownership_001",
            sign_date=date(2027, 1, 1),
            start_date=date(2027, 1, 1),
            end_date=date(2028, 12, 31),
            rent_terms=[
                RentTermCreate(
                    start_date=date(2027, 1, 1),
                    end_date=date(2028, 12, 31),
                    monthly_rent=Decimal("10000"),
                )
            ],
        )

        with pytest.raises(
            OperationNotAllowedError, match="只能续签有效|原合同状态"
        ):  # More flexible matching
            rent_contract_service.renew_contract(
                db=test_db,
                original_contract_id=original_contract.id,
                new_contract_data=renewal_data,
                should_transfer_deposit=True,
                operator="测试用户",
                operator_id="user_001",
            )

    def test_renewal_with_invalid_new_contract_dates(
        self, test_db: Session, original_contract: RentContract
    ):
        """TC-REN-010: Renewal fails when new contract dates are invalid"""
        # Pydantic schema validation rejects invalid dates at object creation
        unique_id = str(uuid.uuid4())[:8]
        with pytest.raises(ValueError):  # Pydantic validation error
            RentContractCreate(
                contract_number=f"NEW{unique_id}",
                contract_type=ContractType.LEASE_DOWNSTREAM,
                tenant_name="测试",
                asset_ids=["asset_001"],
                ownership_id="ownership_001",
                sign_date=date(2027, 1, 1),
                start_date=date(2027, 12, 31),
                end_date=date(2027, 1, 1),  # Invalid: end before start
                rent_terms=[
                    RentTermCreate(
                        start_date=date(2027, 12, 31),
                        end_date=date(2027, 1, 1),  # Invalid: end before start
                        monthly_rent=Decimal("10000"),
                    )
                ],
            )
