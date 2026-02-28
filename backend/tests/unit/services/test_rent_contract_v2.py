"""
V2 Contract Features - Unit Tests

Tests for V2-specific contract functionality:
- Contract types (upstream/downstream/entrusted)
- Multi-asset association
- Contract renewal with deposit transfer
- Contract termination with refund/deduction
- Service fee calculation for entrusted contracts
"""

from datetime import date
from decimal import Decimal

import pytest

from src.schemas.rent_contract import (
    ContractType,
    PaymentCycle,
    RentContractCreate,
    RentTermCreate,
)

# ==================== Fixtures ====================


@pytest.fixture
def default_term():
    """Default valid rent term for 2026"""
    return RentTermCreate(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        monthly_rent=Decimal("10000"),
    )


# ==================== Contract Type Tests ====================


class TestContractTypes:
    """Test contract type distinctions (V2 core feature)"""

    def test_create_upstream_contract_schema(self, default_term):
        """TC-CON-001: Create upstream lease contract schema"""
        contract_in = RentContractCreate(
            contract_number="UP2026001",
            contract_type=ContractType.LEASE_UPSTREAM,
            tenant_name="运营方公司",
            asset_ids=["asset_001", "asset_002"],
            ownership_id="ownership_001",
            sign_date=date(2026, 1, 1),
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            payment_cycle=PaymentCycle.QUARTERLY,
            rent_terms=[default_term],
        )

        assert contract_in.contract_type == ContractType.LEASE_UPSTREAM
        assert contract_in.payment_cycle == PaymentCycle.QUARTERLY
        assert len(contract_in.asset_ids) == 2

    def test_create_downstream_with_upstream_reference(self, default_term):
        """TC-CON-002: Create downstream contract linked to upstream"""
        contract_in = RentContractCreate(
            contract_number="DN2026001",
            contract_type=ContractType.LEASE_DOWNSTREAM,
            upstream_contract_id="upstream_001",
            tenant_name="终端租户A",
            tenant_usage="零售商铺",
            asset_ids=["asset_001"],
            ownership_id="ownership_001",
            sign_date=date(2026, 1, 1),
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            payment_cycle=PaymentCycle.MONTHLY,
            rent_terms=[default_term],
        )

        assert contract_in.contract_type == ContractType.LEASE_DOWNSTREAM
        assert contract_in.upstream_contract_id == "upstream_001"
        assert contract_in.tenant_usage == "零售商铺"

    def test_create_entrusted_contract_with_service_fee(self, default_term):
        """TC-CON-003: Create entrusted contract with service fee rate"""
        contract_in = RentContractCreate(
            contract_number="EN2026001",
            contract_type=ContractType.ENTRUSTED,
            service_fee_rate=Decimal("0.0500"),
            tenant_name="权属方委托",
            asset_ids=["asset_001"],
            ownership_id="ownership_001",
            sign_date=date(2026, 1, 1),
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            rent_terms=[default_term],
        )

        assert contract_in.contract_type == ContractType.ENTRUSTED
        assert contract_in.service_fee_rate == Decimal("0.0500")


# ==================== Multi-Asset Tests ====================


class TestMultiAssetContracts:
    """Test multi-asset association (V2 feature)"""

    def test_contract_with_multiple_assets(self, default_term):
        """TC-CON-006: Contract associated with multiple assets"""
        contract_in = RentContractCreate(
            contract_number="MA2026001",
            contract_type=ContractType.LEASE_DOWNSTREAM,
            tenant_name="多资产租户",
            asset_ids=["asset_001", "asset_002", "asset_003"],
            ownership_id="ownership_001",
            sign_date=date(2026, 1, 1),
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            rent_terms=[default_term],
        )

        assert len(contract_in.asset_ids) == 3
        assert "asset_001" in contract_in.asset_ids
        assert "asset_002" in contract_in.asset_ids
        assert "asset_003" in contract_in.asset_ids


# ==================== Payment Cycle Tests ====================


class TestPaymentCycle:
    """Test payment cycle handling (V2 feature)"""

    def test_payment_cycle_enum_values(self):
        """Verify payment cycle enum values"""
        assert PaymentCycle.MONTHLY.value == "monthly"
        assert PaymentCycle.QUARTERLY.value == "quarterly"
        assert PaymentCycle.SEMI_ANNUAL.value == "semi_annual"
        assert PaymentCycle.ANNUAL.value == "annual"

    def test_contract_with_annual_payment(self, default_term):
        """Test contract with annual payment cycle"""
        contract_in = RentContractCreate(
            contract_number="AN2026001",
            contract_type=ContractType.LEASE_UPSTREAM,
            tenant_name="年付租户",
            asset_ids=["asset_001"],
            ownership_id="ownership_001",
            sign_date=date(2026, 1, 1),
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            payment_cycle=PaymentCycle.ANNUAL,
            rent_terms=[default_term],
        )

        assert contract_in.payment_cycle == PaymentCycle.ANNUAL


# ==================== Schema Validation Tests ====================


class TestSchemaValidation:
    """Test V2 schema validation rules"""

    def test_contract_type_enum_default(self, default_term):
        """Default contract type should be downstream"""
        contract_in = RentContractCreate(
            tenant_name="测试租户",
            ownership_id="ownership_001",
            sign_date=date(2026, 1, 1),
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            rent_terms=[default_term],
        )

        assert contract_in.contract_type == ContractType.LEASE_DOWNSTREAM

    def test_service_fee_rate_validation(self, default_term):
        """Service fee rate should be between 0 and 1"""
        contract_in = RentContractCreate(
            contract_type=ContractType.ENTRUSTED,
            service_fee_rate=Decimal("0.15"),  # 15%
            tenant_name="委托方",
            ownership_id="ownership_001",
            sign_date=date(2026, 1, 1),
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            rent_terms=[default_term],
        )

        assert contract_in.service_fee_rate == Decimal("0.15")

    def test_tenant_usage_field(self, default_term):
        """Downstream contract should accept tenant_usage"""
        contract_in = RentContractCreate(
            contract_type=ContractType.LEASE_DOWNSTREAM,
            tenant_name="终端租户",
            tenant_usage="餐饮用途",
            ownership_id="ownership_001",
            sign_date=date(2026, 1, 1),
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            rent_terms=[default_term],
        )

        assert contract_in.tenant_usage == "餐饮用途"

    def test_rent_terms_required(self):
        """Rent terms validation - cannot be empty"""
        with pytest.raises(ValueError, match="租金条款不能为空"):
            RentContractCreate(
                tenant_name="测试租户",
                ownership_id="ownership_001",
                sign_date=date(2026, 1, 1),
                start_date=date(2026, 1, 1),
                end_date=date(2026, 12, 31),
                rent_terms=[],  # Empty - should fail
            )

    def test_owner_party_id_without_ownership_id_is_allowed(self, default_term):
        """Create schema should allow owner_party-only payloads; ownership bridge happens server-side."""
        contract_in = RentContractCreate(
            tenant_name="测试租户",
            owner_party_id="party_001",
            sign_date=date(2026, 1, 1),
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            rent_terms=[default_term],
        )

        assert contract_in.owner_party_id == "party_001"
        assert contract_in.ownership_id is None

    def test_tiered_rent_terms(self):
        """Test tiered (stepped) rent terms"""
        terms = [
            RentTermCreate(
                start_date=date(2026, 1, 1),
                end_date=date(2026, 6, 30),
                monthly_rent=Decimal("10000"),
            ),
            RentTermCreate(
                start_date=date(2026, 6, 30),
                end_date=date(2026, 12, 31),
                monthly_rent=Decimal("10500"),  # 5% increase
            ),
        ]

        contract_in = RentContractCreate(
            tenant_name="阶梯租金租户",
            ownership_id="ownership_001",
            sign_date=date(2026, 1, 1),
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            rent_terms=terms,
        )

        assert len(contract_in.rent_terms) == 2
        assert contract_in.rent_terms[0].monthly_rent == Decimal("10000")
        assert contract_in.rent_terms[1].monthly_rent == Decimal("10500")


# ==================== Contract Type Enum Tests ====================


class TestContractTypeEnum:
    """Test contract type enum values"""

    def test_contract_type_enum_values(self):
        """Verify contract type enum values"""
        assert ContractType.LEASE_UPSTREAM.value == "lease_upstream"
        assert ContractType.LEASE_DOWNSTREAM.value == "lease_downstream"
        assert ContractType.ENTRUSTED.value == "entrusted"

    def test_all_contract_types_supported(self, default_term):
        """All contract types should be valid"""
        for ct in [
            ContractType.LEASE_UPSTREAM,
            ContractType.LEASE_DOWNSTREAM,
            ContractType.ENTRUSTED,
        ]:
            contract = RentContractCreate(
                contract_type=ct,
                tenant_name="测试",
                ownership_id="ownership_001",
                sign_date=date(2026, 1, 1),
                start_date=date(2026, 1, 1),
                end_date=date(2026, 12, 31),
                rent_terms=[default_term],
            )
            assert contract.contract_type == ct
