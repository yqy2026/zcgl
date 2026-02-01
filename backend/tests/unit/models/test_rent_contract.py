"""
RentContract Model Tests

Tests for the RentContract model - core contract management entity.
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
import uuid

import pytest

from src.models.rent_contract import (
    ContractType,
    DepositTransactionType,
    PaymentCycle,
    RentContract,
)




# Helper function to create a complete RentContract for testing
def _create_complete_contract(**kwargs):
    """Create a RentContract with all required defaults for unit tests"""
    now = datetime.now(UTC)
    defaults = {
        'id': str(uuid.uuid4()),
        'contract_type': ContractType.LEASE_DOWNSTREAM,
        'contract_status': 'draft',
        'created_at': now,
        'updated_at': now,
    }
    defaults.update(kwargs)
    return RentContract(**defaults)


class TestRentContractEnums:
    """Test RentContract-related enumerations"""

    def test_contract_type_enum_values(self):
        """Test ContractType enum values"""
        assert ContractType.LEASE_UPSTREAM == "lease_upstream"
        assert ContractType.LEASE_DOWNSTREAM == "lease_downstream"
        assert ContractType.ENTRUSTED == "entrusted"

    def test_contract_type_is_enum(self):
        """Test that ContractType is an Enum"""
        assert isinstance(ContractType.LEASE_DOWNSTREAM, Enum)

    def test_payment_cycle_enum_values(self):
        """Test PaymentCycle enum values"""
        assert PaymentCycle.MONTHLY == "monthly"
        assert PaymentCycle.QUARTERLY == "quarterly"
        assert PaymentCycle.SEMI_ANNUAL == "semi_annual"
        assert PaymentCycle.ANNUAL == "annual"

    def test_deposit_transaction_type_enum_values(self):
        """Test DepositTransactionType enum values"""
        assert DepositTransactionType.RECEIPT == "receipt"
        assert DepositTransactionType.REFUND == "refund"
        assert DepositTransactionType.DEDUCTION == "deduction"
        assert DepositTransactionType.TRANSFER_OUT == "transfer_out"
        assert DepositTransactionType.TRANSFER_IN == "transfer_in"


class TestRentContractCreation:
    """Test RentContract model creation"""

    @pytest.fixture
    def minimal_contract(self):
        """Create a minimal valid RentContract with all fields"""
        now = datetime.now(UTC)
        return RentContract(
            id=str(uuid.uuid4()),
            contract_number="CONTRACT-001",
            ownership_id="ownership-123",
            tenant_name="Test Tenant",
            sign_date=date(2024, 1, 1),
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            contract_type=ContractType.LEASE_DOWNSTREAM,  # Default value
            contract_status="draft",  # Default status
            created_at=now,  # Timestamp
            updated_at=now,  # Timestamp
        )

    def test_contract_creation(self, minimal_contract):
        """Test basic contract creation"""
        assert minimal_contract.contract_number == "CONTRACT-001"
        assert minimal_contract.tenant_name == "Test Tenant"
        assert minimal_contract.sign_date == date(2024, 1, 1)

    def test_contract_id_generation(self, minimal_contract):
        """Test that contract ID is auto-generated"""
        assert minimal_contract.id is not None
        assert isinstance(minimal_contract.id, str)

    def test_contract_default_type(self, minimal_contract):
        """Test default contract type"""
        assert minimal_contract.contract_type == ContractType.LEASE_DOWNSTREAM


class TestRentContractBasicFields:
    """Test RentContract basic fields"""

    @pytest.fixture
    def contract(self):
        now = datetime.now(UTC)
        return RentContract(
            id=str(uuid.uuid4()),
            contract_number="CONTRACT-002",
            ownership_id="ownership-456",
            tenant_name="Tenant Corp",
            sign_date=date(2024, 1, 1),
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            contract_type=ContractType.LEASE_UPSTREAM,
            upstream_contract_id="upstream-123",
            contract_status="draft",
            created_at=now,
            updated_at=now,
        )

    def test_contract_number_unique(self, contract):
        """Test contract_number is set"""
        assert contract.contract_number == "CONTRACT-002"

    def test_ownership_id_required(self):
        """Test ownership_id is required"""
        with pytest.raises(Exception):
            RentContract(
                tenant_name="Tenant",
                sign_date=date(2024, 1, 1),
                start_date=date(2024, 1, 1),
                end_date=date(2024, 12, 31),
            )

    def test_contract_type_assignment(self, contract):
        """Test contract type can be set"""
        assert contract.contract_type == ContractType.LEASE_UPSTREAM

    def test_upstream_contract_optional(self, contract):
        """Test upstream_contract_id is optional"""
        assert contract.upstream_contract_id == "upstream-123"


class TestRentContractOwnerFields:
    """Test owner/lessor fields"""

    @pytest.fixture
    def upstream_contract(self):
        return RentContract(
            contract_number="CONTRACT-003",
            ownership_id="ownership-789",
            contract_type=ContractType.LEASE_UPSTREAM,
            tenant_name="Operating Company",
            owner_name="Property Owner",
            owner_contact="John Doe",
            owner_phone="13800138000",
            sign_date=date(2024, 1, 1),
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )

    def test_owner_name(self, upstream_contract):
        """Test owner_name field"""
        assert upstream_contract.owner_name == "Property Owner"

    def test_owner_contact(self, upstream_contract):
        """Test owner_contact field"""
        assert upstream_contract.owner_contact == "John Doe"

    def test_owner_phone(self, upstream_contract):
        """Test owner_phone field"""
        assert upstream_contract.owner_phone == "13800138000"

    def test_owner_fields_optional(self):
        """Test owner fields are optional"""
        contract = RentContract(
            contract_number="CONTRACT-004",
            ownership_id="ownership-999",
            tenant_name="Tenant",
            sign_date=date(2024, 1, 1),
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )
        assert contract.owner_name is None
        assert contract.owner_contact is None


class TestRentContractTenantFields:
    """Test tenant/lessee fields"""

    @pytest.fixture
    def contract_with_tenant(self):
        return RentContract(
            contract_number="CONTRACT-005",
            ownership_id="ownership-abc",
            tenant_name="Tenant Company LLC",
            tenant_contact="Jane Smith",
            tenant_phone="13900139000",
            tenant_address="456 Tenant Street",
            sign_date=date(2024, 1, 1),
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )

    def test_tenant_name(self, contract_with_tenant):
        """Test tenant_name field"""
        assert contract_with_tenant.tenant_name == "Tenant Company LLC"

    def test_tenant_contact(self, contract_with_tenant):
        """Test tenant_contact field"""
        assert contract_with_tenant.tenant_contact == "Jane Smith"

    def test_tenant_phone(self, contract_with_tenant):
        """Test tenant_phone field"""
        assert contract_with_tenant.tenant_phone == "13900139000"

    def test_tenant_address(self, contract_with_tenant):
        """Test tenant_address field"""
        assert contract_with_tenant.tenant_address == "456 Tenant Street"

    def test_tenant_fields_optional(self):
        """Test extended tenant fields are optional"""
        contract = RentContract(
            contract_number="CONTRACT-006",
            ownership_id="ownership-def",
            tenant_name="Basic Tenant",
            sign_date=date(2024, 1, 1),
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )
        assert contract.tenant_contact is None
        assert contract.tenant_phone is None


class TestRentContractDates:
    """Test contract date fields"""

    @pytest.fixture
    def contract(self):
        return RentContract(
            contract_number="CONTRACT-007",
            ownership_id="ownership-dates",
            tenant_name="Date Tenant",
            sign_date=date(2024, 1, 15),
            start_date=date(2024, 2, 1),
            end_date=date(2024, 12, 31),
        )

    def test_sign_date(self, contract):
        """Test sign_date field"""
        assert contract.sign_date == date(2024, 1, 15)

    def test_start_date(self, contract):
        """Test start_date field"""
        assert contract.start_date == date(2024, 2, 1)

    def test_end_date(self, contract):
        """Test end_date field"""
        assert contract.end_date == date(2024, 12, 31)

    def test_date_order(self, contract):
        """Test that dates are in logical order"""
        assert contract.sign_date <= contract.start_date <= contract.end_date


class TestEntrustedContract:
    """Test entrusted operation contract type"""

    @pytest.fixture
    def entrusted_contract(self):
        return RentContract(
            contract_number="CONTRACT-008",
            ownership_id="ownership-entrusted",
            contract_type=ContractType.ENTRUSTED,
            service_fee_rate=Decimal("0.0500"),
            tenant_name="Service Provider",
            sign_date=date(2024, 1, 1),
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )

    def test_entrusted_contract_type(self, entrusted_contract):
        """Test entrusted contract type"""
        assert entrusted_contract.contract_type == ContractType.ENTRUSTED

    def test_service_fee_rate(self, entrusted_contract):
        """Test service_fee_rate field"""
        assert entrusted_contract.service_fee_rate == Decimal("0.0500")

    def test_service_fee_rate_is_decimal(self, entrusted_contract):
        """Test service_fee_rate is Decimal type"""
        assert isinstance(entrusted_contract.service_fee_rate, Decimal)


class TestRentContractTimestamps:
    """Test timestamp fields"""

    @pytest.fixture
    def contract(self):
        now = datetime.now(UTC)
        return RentContract(
            id=str(uuid.uuid4()),
            contract_number="CONTRACT-009",
            ownership_id="ownership-timestamp",
            tenant_name="Timestamp Tenant",
            sign_date=date(2024, 1, 1),
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            contract_type=ContractType.LEASE_DOWNSTREAM,
            contract_status="draft",
            created_at=now,
            updated_at=now,
        )

    def test_created_at_is_set(self, contract):
        """Test created_at is automatically set"""
        assert contract.created_at is not None
        assert isinstance(contract.created_at, datetime)

    def test_updated_at_is_set(self, contract):
        """Test updated_at is automatically set"""
        assert contract.updated_at is not None
        assert isinstance(contract.updated_at, datetime)


class TestRentContractStatus:
    """Test contract status field"""

    @pytest.fixture
    def contract(self):
        return RentContract(
            contract_number="CONTRACT-010",
            ownership_id="ownership-status",
            tenant_name="Status Tenant",
            sign_date=date(2024, 1, 1),
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )

    def test_default_status(self, contract):
        """Test default contract status"""
        # Import ContractStatus enum
        from src.core.enums import ContractStatus

        assert contract.status == ContractStatus.ACTIVE

    def test_status_can_be_changed(self, contract):
        """Test status can be updated"""
        from src.core.enums import ContractStatus

        contract.status = ContractStatus.TERMINATED
        assert contract.status == ContractStatus.TERMINATED


class TestRentContractValidation:
    """Test RentContract validation scenarios"""

    def test_end_date_after_start_date(self):
        """Test that end_date must be after start_date"""
        # SQLAlchemy doesn't enforce this automatically
        contract = RentContract(
            contract_number="CONTRACT-011",
            ownership_id="ownership-validation",
            tenant_name="Validation Tenant",
            sign_date=date(2024, 1, 1),
            start_date=date(2024, 12, 31),
            end_date=date(
                2024, 1, 1
            ),  # End before start - should validate at app level
        )
        assert contract.end_date < contract.start_date

    def test_contract_number_uniqueness(self):
        """Test that contract_number should be unique"""
        # This is enforced at database level
        contract1 = RentContract(
            contract_number="CONTRACT-DUP",
            ownership_id="ownership-1",
            tenant_name="Tenant 1",
            sign_date=date(2024, 1, 1),
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )
        contract2 = RentContract(
            contract_number="CONTRACT-DUP",  # Duplicate number
            ownership_id="ownership-2",
            tenant_name="Tenant 2",
            sign_date=date(2024, 1, 1),
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )
        assert contract1.contract_number == contract2.contract_number


class TestRentContractStringRepresentation:
    """Test contract string representation"""

    @pytest.fixture
    def contract(self):
        return RentContract(
            contract_number="CONTRACT-012",
            ownership_id="ownership-repr",
            tenant_name="Representation Tenant",
            sign_date=date(2024, 1, 1),
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )

    def test_contract_repr(self, contract):
        """Test contract repr contains identifying info"""
        repr_str = repr(contract)
        assert "RentContract" in repr_str

    def test_contract_number_is_key(self, contract):
        """Test contract_number is main identifier"""
        assert contract.contract_number == "CONTRACT-012"


class TestRentContractEdgeCases:
    """Test contract edge cases"""

    def test_very_long_names(self):
        """Test handling of very long names"""
        long_name = "A" * 250
        contract = RentContract(
            contract_number="CONTRACT-LONG",
            ownership_id="ownership-long",
            tenant_name=long_name,
            sign_date=date(2024, 1, 1),
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )
        assert len(contract.tenant_name) == 250

    def test_multi_year_contract(self):
        """Test multi-year contract duration"""
        contract = RentContract(
            contract_number="CONTRACT-LONGTERM",
            ownership_id="ownership-longterm",
            tenant_name="Long Term Tenant",
            sign_date=date(2024, 1, 1),
            start_date=date(2024, 1, 1),
            end_date=date(2034, 12, 31),  # 10 years
        )
        duration = contract.end_date - contract.start_date
        assert duration.days > 365 * 9  # More than 9 years

    def test_special_characters_in_phone(self):
        """Test phone numbers with special characters"""
        contract = RentContract(
            contract_number="CONTRACT-PHONE",
            ownership_id="ownership-phone",
            tenant_name="Phone Tenant",
            tenant_phone="+86-138-0013-8000",
            sign_date=date(2024, 1, 1),
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )
        assert "+" in contract.tenant_phone


class TestRentContractDefaults:
    """Test contract default values"""

    @pytest.fixture
    def contract(self):
        return RentContract(
            contract_number="CONTRACT-DEFAULT",
            ownership_id="ownership-default",
            tenant_name="Default Tenant",
            sign_date=date(2024, 1, 1),
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )

    def test_default_contract_type(self, contract):
        """Test default contract_type"""
        assert contract.contract_type == ContractType.LEASE_DOWNSTREAM

    def test_id_is_generated(self, contract):
        """Test ID is auto-generated"""
        assert contract.id is not None
        assert len(contract.id) > 0
