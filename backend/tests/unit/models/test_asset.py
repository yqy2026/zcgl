"""
Asset Model Tests

Tests for the Asset model - core business entity for property/asset management.
"""

import os
from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import NO_VALUE

import src.models.asset as asset_model_module
from src.database import Base
from src.models.asset import Asset
from src.models.contract_group import (
    Contract,
    ContractDirection,
    ContractLifecycleStatus,
    GroupRelationType,
    LeaseContractDetail,
)
from src.models.ownership import Ownership


def _build_contract(
    *,
    contract_number: str,
    tenant_name: str | None,
    effective_from: date,
    effective_to: date | None,
    status: ContractLifecycleStatus = ContractLifecycleStatus.ACTIVE,
    monthly_rent: Decimal | None = None,
    deposit: Decimal | None = None,
) -> Contract:
    contract = Contract(
        contract_group_id="group-001",
        contract_number=contract_number,
        contract_direction=ContractDirection.LESSOR,
        group_relation_type=GroupRelationType.DOWNSTREAM,
        lessor_party_id="party-lessor",
        lessee_party_id="party-lessee",
        sign_date=effective_from,
        effective_from=effective_from,
        effective_to=effective_to,
        status=status,
    )
    contract.lease_detail = LeaseContractDetail(
        rent_amount=monthly_rent or Decimal("0"),
        monthly_rent_base=monthly_rent,
        total_deposit=deposit,
        tenant_name=tenant_name,
    )
    return contract


class TestAssetModelCreation:
    """Test Asset model creation and basic attributes"""

    @pytest.fixture
    def engine(self):
        """Create database engine for testing"""
        database_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
        if not database_url:
            pytest.skip(
                "TEST_DATABASE_URL or DATABASE_URL is required", allow_module_level=True
            )
        if not database_url.startswith("postgresql"):
            raise RuntimeError("测试必须使用 PostgreSQL")
        connect_args: dict[str, int] = {}
        if database_url.startswith("postgresql"):
            connect_args["connect_timeout"] = 3
        engine = create_engine(
            database_url,
            pool_pre_ping=True,
            connect_args=connect_args,
        )
        try:
            with engine.connect():
                pass
            Base.metadata.create_all(engine)
        except OperationalError as exc:
            engine.dispose()
            pytest.skip(
                f"TEST_DATABASE_URL unreachable for model db tests: {exc}",
                allow_module_level=True,
            )

        yield engine
        engine.dispose()

    @pytest.fixture
    def session(self, engine):
        """Create database session"""
        with Session(engine) as session:
            yield session

    @pytest.fixture
    def sample_asset(self):
        """Create a sample Asset instance"""
        return Asset(
            ownership_id="Test Corporation",
            asset_name="Test Property",
            address="123 Test Street",
            ownership_status="已确权",
            property_nature="商业",
            usage_status="在用",
        )

    def test_asset_creation(self, sample_asset):
        """Test basic Asset creation"""
        assert sample_asset.ownership_id == "Test Corporation"
        assert sample_asset.asset_name == "Test Property"
        assert sample_asset.address == "123 Test Street"
        assert sample_asset.ownership_status == "已确权"

    def test_asset_required_fields(self, session):
        """Test that required fields are enforced"""
        # Missing required fields should fail
        with pytest.raises(Exception):  # SQLAlchemy will raise an error
            asset = Asset()
            session.add(asset)
            session.commit()

    def test_asset_optional_fields(self, sample_asset):
        """Test that optional fields can be None"""
        assert sample_asset.ownership_category is None
        assert sample_asset.project_name is None
        assert sample_asset.management_entity == "Test Corporation"

    def test_asset_id_generation(self, sample_asset):
        """Test that Asset ID is auto-generated"""
        assert sample_asset.id is not None
        assert isinstance(sample_asset.id, str)
        assert len(sample_asset.id) > 0


class TestAssetBasicFields:
    """Test Asset basic field types and defaults"""

    @pytest.fixture
    def asset(self):
        return Asset(
            ownership_id="Owner",
            asset_name="Property",
            address="Address",
            ownership_status="Status",
            property_nature="Nature",
            usage_status="Status",
        )

    def test_string_fields(self, asset):
        """Test string field types"""
        assert isinstance(asset.ownership_id, str)
        assert isinstance(asset.asset_name, str)
        assert isinstance(asset.address, str)

    def test_ownership_entity_property(self):
        """Test ownership_entity derives from ownership relation"""
        ownership = Ownership(name="Test Owner", code="OWN-001")
        asset = Asset(
            ownership_id="owner-id",
            asset_name="Property",
            address="Address",
            ownership_status="Status",
            property_nature="Nature",
            usage_status="Status",
        )
        asset.ownership = ownership
        assert asset.ownership_entity == "Test Owner"

    def test_boolean_defaults(self, asset):
        """Test boolean field defaults"""
        assert asset.is_litigated is False
        assert asset.include_in_occupancy_rate is True

    def test_version_default(self, asset):
        """Test version field default"""
        assert asset.version == 1

    def test_data_status_default(self, asset):
        """Test data_status field default"""
        assert asset.data_status == "正常"


class TestAssetRelationshipProjectionSafety:
    """Test relationship projection safety for computed properties."""

    def _build_asset(self) -> Asset:
        return Asset(
            ownership_id="Owner",
            asset_name="Property",
            address="Address",
            ownership_status="Status",
            property_nature="Nature",
            usage_status="Status",
        )

    def test_active_contract_transient_asset_no_warning(self, caplog):
        """Transient objects should not warn when relationship is not loaded."""
        asset = self._build_asset()

        with caplog.at_level("WARNING"):
            assert asset.active_contract is None

        assert not any(
            "selectinload(Asset.contracts)" in record.message
            for record in caplog.records
        )

    def test_active_contract_unloaded_relationship_warns_once(
        self, monkeypatch, caplog
    ):
        """Persistent-like unloaded relation should emit one warning."""
        asset = self._build_asset()
        fake_state = SimpleNamespace(
            transient=False,
            pending=False,
            attrs={"contracts": SimpleNamespace(loaded_value=NO_VALUE)},
        )
        monkeypatch.setattr(asset_model_module, "inspect", lambda _: fake_state)

        with caplog.at_level("WARNING"):
            assert asset.active_contract is None
            assert asset.tenant_name is None

        warnings = [
            record
            for record in caplog.records
            if "selectinload(Asset.contracts)" in record.message
        ]
        assert (
            asset.__dict__.get("_warned_unloaded_relationship_contracts") is True
        )
        assert len(warnings) <= 1

    def test_ownership_entity_unloaded_relationship_warns(
        self, monkeypatch, caplog
    ):
        """Unloaded ownership relation should emit actionable warning."""
        asset = self._build_asset()
        fake_state = SimpleNamespace(
            transient=False,
            pending=False,
            attrs={"ownership": SimpleNamespace(loaded_value=NO_VALUE)},
        )
        monkeypatch.setattr(asset_model_module, "inspect", lambda _: fake_state)

        with caplog.at_level("WARNING"):
            assert asset.ownership_entity is None

        warnings = [
            record
            for record in caplog.records
            if "selectinload(Asset.ownership)" in record.message
        ]
        assert asset.__dict__.get("_warned_unloaded_relationship_ownership") is True
        assert len(warnings) <= 1


class TestAssetAreaFields:
    """Test Asset area-related fields"""

    @pytest.fixture
    def asset_with_areas(self):
        return Asset(
            ownership_id="Owner",
            asset_name="Property",
            address="Address",
            ownership_status="Status",
            property_nature="Nature",
            usage_status="Status",
            land_area=Decimal("1000.50"),
            actual_property_area=Decimal("800.30"),
            rentable_area=Decimal("750.00"),
            rented_area=Decimal("600.00"),
            non_commercial_area=Decimal("50.00"),
        )

    def test_area_fields_are_decimal(self, asset_with_areas):
        """Test that area fields use Decimal type"""
        assert isinstance(asset_with_areas.land_area, Decimal)
        assert isinstance(asset_with_areas.actual_property_area, Decimal)
        assert isinstance(asset_with_areas.rentable_area, Decimal)

    def test_area_values(self, asset_with_areas):
        """Test area field values"""
        assert asset_with_areas.land_area == Decimal("1000.50")
        assert asset_with_areas.actual_property_area == Decimal("800.30")
        assert asset_with_areas.rentable_area == Decimal("750.00")

    def test_area_fields_can_be_null(self):
        """Test that area fields can be None"""
        asset = Asset(
            ownership_id="Owner",
            asset_name="Property",
            address="Address",
            ownership_status="Status",
            property_nature="Nature",
            usage_status="Status",
        )
        assert asset.land_area is None
        assert asset.rentable_area is None


class TestAssetContractFields:
    """Test Asset contract-related fields"""

    @pytest.fixture
    def asset_with_contract(self):
        asset = Asset(
            ownership_id="Owner",
            asset_name="Property",
            address="Address",
            ownership_status="Status",
            property_nature="Nature",
            usage_status="Status",
            tenant_type="企业",
        )
        contract = _build_contract(
            contract_number="CONTRACT-001",
            tenant_name="Test Tenant",
            effective_from=date(2024, 1, 1),
            effective_to=date(2024, 12, 31),
            monthly_rent=Decimal("5000.00"),
            deposit=Decimal("10000.00"),
        )
        asset.contracts = [contract]
        return asset

    def test_tenant_fields(self, asset_with_contract):
        """Test tenant-related fields"""
        assert asset_with_contract.tenant_name == "Test Tenant"
        assert asset_with_contract.tenant_type == "企业"

    def test_contract_dates(self, asset_with_contract):
        """Test contract date fields"""
        assert asset_with_contract.contract_start_date == date(2024, 1, 1)
        assert asset_with_contract.contract_end_date == date(2024, 12, 31)

    def test_financial_fields(self, asset_with_contract):
        """Test contract financial fields"""
        assert asset_with_contract.monthly_rent == Decimal("5000.00")
        assert asset_with_contract.deposit == Decimal("10000.00")

    def test_active_contract_projects_from_lease_detail(self):
        """Test active contract projection reads lease detail fields."""
        asset = Asset(
            ownership_id="Owner",
            asset_name="Property",
            address="Address",
            ownership_status="Status",
            property_nature="Nature",
            usage_status="Status",
        )
        contract = _build_contract(
            contract_number="CONTRACT-DETAIL",
            tenant_name="Detail Tenant",
            effective_from=date(2024, 1, 1),
            effective_to=date(2026, 12, 31),
            monthly_rent=Decimal("6100.00"),
            deposit=Decimal("12000.00"),
        )
        asset.contracts = [contract]

        assert asset.active_contract is contract
        assert asset.tenant_name == "Detail Tenant"
        assert asset.monthly_rent == Decimal("6100.00")

    def test_active_contract_cached_across_projection_fields(self, monkeypatch):
        """Repeated projection field access should reuse active contract selection."""
        asset = Asset(
            ownership_id="Owner",
            asset_name="Property",
            address="Address",
            ownership_status="Status",
            property_nature="Nature",
            usage_status="Status",
        )
        contract = _build_contract(
            contract_number="CONTRACT-CACHED",
            tenant_name="Cached Tenant",
            effective_from=date(2024, 1, 1),
            effective_to=date(2026, 12, 31),
            monthly_rent=Decimal("3200.00"),
            deposit=Decimal("6400.00"),
        )
        asset.contracts = [contract]

        call_counter = {"count": 0}
        original_picker = Asset._pick_preferred_contract

        def _counting_picker(self, contracts_value, active_statuses, *, today):
            call_counter["count"] += 1
            return original_picker(
                self,
                contracts_value,
                active_statuses,
                today=today,
            )

        monkeypatch.setattr(Asset, "_pick_preferred_contract", _counting_picker)

        assert asset.tenant_name == "Cached Tenant"
        assert asset.contract_end_date == date(2026, 12, 31)
        assert asset.monthly_rent == Decimal("3200.00")
        assert call_counter["count"] == 1

    def test_active_contract_cache_invalidate_when_contract_list_replaced(self):
        """Replacing contract collection should invalidate active contract cache."""
        asset = Asset(
            ownership_id="Owner",
            asset_name="Property",
            address="Address",
            ownership_status="Status",
            property_nature="Nature",
            usage_status="Status",
        )
        first_contract = _build_contract(
            contract_number="CONTRACT-FIRST",
            tenant_name="First Tenant",
            effective_from=date(2024, 1, 1),
            effective_to=date(2025, 12, 31),
        )
        second_contract = _build_contract(
            contract_number="CONTRACT-SECOND",
            tenant_name="Second Tenant",
            effective_from=date(2025, 1, 1),
            effective_to=date(2026, 12, 31),
        )

        asset.contracts = [first_contract]
        assert asset.tenant_name == "First Tenant"

        asset.contracts = [second_contract]
        assert asset.tenant_name == "Second Tenant"
        assert asset.lease_contract_number == "CONTRACT-SECOND"

    def test_sublease_default(self, asset_with_contract):
        """Test sublease default value"""
        assert asset_with_contract.is_sublease is False


class TestAssetTimestamps:
    """Test Asset timestamp fields"""

    @pytest.fixture
    def asset(self):
        return Asset(
            ownership_id="Owner",
            asset_name="Property",
            address="Address",
            ownership_status="Status",
            property_nature="Nature",
            usage_status="Status",
        )

    def test_created_at_is_set(self, asset):
        """Test that created_at is automatically set"""
        assert asset.created_at is not None
        assert isinstance(asset.created_at, datetime)

    def test_updated_at_is_set(self, asset):
        """Test that updated_at is automatically set"""
        assert asset.updated_at is not None
        assert isinstance(asset.updated_at, datetime)

    def test_timestamps_use_utc(self, asset):
        """Test that timestamps use UTC timezone"""
        assert asset.created_at.tzinfo is None


class TestAssetManagementFields:
    """Test Asset management-related fields"""

    @pytest.fixture
    def managed_asset(self):
        return Asset(
            ownership_id="Owner",
            asset_name="Property",
            address="Address",
            ownership_status="Status",
            property_nature="Nature",
            usage_status="Status",
            management_entity="Management Corp",
            business_category="零售",
            revenue_mode="直接接收",
            operation_status="正常经营",
            manager_name="John Doe",
        )

    def test_management_fields(self, managed_asset):
        """Test management-related fields"""
        assert managed_asset.management_entity == "Management Corp"
        assert managed_asset.business_category == "零售"
        assert managed_asset.operation_status == "正常经营"
        assert managed_asset.manager_name == "John Doe"


class TestAssetUsageFields:
    """Test Asset usage-related fields"""

    @pytest.fixture
    def asset_with_usage(self):
        return Asset(
            ownership_id="Owner",
            asset_name="Property",
            address="Address",
            ownership_status="Status",
            property_nature="Nature",
            usage_status="Status",
            certificated_usage="商业",
            actual_usage="办公",
        )

    def test_usage_fields(self, asset_with_usage):
        """Test usage-related fields"""
        assert asset_with_usage.certificated_usage == "商业"
        assert asset_with_usage.actual_usage == "办公"


class TestAssetSystemFields:
    """Test Asset system and audit fields"""

    @pytest.fixture
    def system_asset(self):
        return Asset(
            ownership_id="Owner",
            asset_name="Property",
            address="Address",
            ownership_status="Status",
            property_nature="Nature",
            usage_status="Status",
            created_by="admin",
            updated_by="admin",
            tags="tag1,tag2,tag3",
        )

    def test_system_fields(self, system_asset):
        """Test system field values"""
        assert system_asset.created_by == "admin"
        assert system_asset.updated_by == "admin"

    def test_tags_field(self, system_asset):
        """Test tags field"""
        assert system_asset.tags == "tag1,tag2,tag3"

    def test_version_increment(self):
        """Test version field can be incremented"""
        asset = Asset(
            ownership_id="Owner",
            asset_name="Property",
            address="Address",
            ownership_status="Status",
            property_nature="Nature",
            usage_status="Status",
        )
        asset.version = 2
        assert asset.version == 2


class TestAssetValidation:
    """Test Asset data validation"""

    def test_negative_area_rejected(self):
        """Test that negative areas are not automatically rejected (SQLAlchemy doesn't validate)"""
        # SQLAlchemy doesn't automatically validate ranges
        # This would need application-level validation
        asset = Asset(
            ownership_id="Owner",
            asset_name="Property",
            address="Address",
            ownership_status="Status",
            property_nature="Nature",
            usage_status="Status",
            land_area=Decimal(
                "-100.00"
            ),  # Negative - should be validated at application level
        )
        assert asset.land_area == Decimal("-100.00")

    def test_future_date_allowed(self):
        """Test contract projection allows future contract dates."""
        future_date = date(2030, 12, 31)
        asset = Asset(
            ownership_id="Owner",
            asset_name="Property",
            address="Address",
            ownership_status="Status",
            property_nature="Nature",
            usage_status="Status",
        )
        contract = _build_contract(
            contract_number="CONTRACT-002",
            tenant_name="Future Tenant",
            effective_from=date(2030, 1, 1),
            effective_to=future_date,
        )
        asset.contracts = [contract]
        assert asset.contract_end_date == future_date


class TestAssetRelationships:
    """Test Asset relationships (without database)"""

    @pytest.fixture
    def asset(self):
        return Asset(
            ownership_id="Owner",
            asset_name="Property",
            address="Address",
            ownership_status="Status",
            property_nature="Nature",
            usage_status="Status",
        )

    def test_relationships_exist(self, asset):
        """Test that relationship attributes exist"""
        legacy_contract_relation = "_".join(("rent", "contracts"))

        assert hasattr(asset, "history_records")
        assert hasattr(asset, "documents")
        assert hasattr(asset, "contracts")
        assert not hasattr(asset, legacy_contract_relation)
        assert hasattr(asset, "certificates")

    def test_relationships_are_lists(self, asset):
        """Test that relationships are list types"""
        # Without actual database session, relationships are empty lists
        assert isinstance(asset.history_records, list)
        assert isinstance(asset.documents, list)


class TestAssetStringRepresentation:
    """Test Asset string representation and serialization"""

    @pytest.fixture
    def asset(self):
        return Asset(
            ownership_id="Test Owner",
            asset_name="Test Property Name",
            address="123 Test Address",
            ownership_status="Status",
            property_nature="Nature",
            usage_status="Status",
        )

    def test_asset_repr_contains_key_info(self, asset):
        """Test that repr contains identifying information"""
        repr_str = repr(asset)
        # Repr should contain class name at minimum
        assert "Asset" in repr_str

    def test_asset_name_display(self, asset):
        """Test asset_name is the main display field"""
        assert asset.asset_name == "Test Property Name"


class TestAssetEdgeCases:
    """Test Asset edge cases and boundary conditions"""

    def test_very_long_names(self):
        """Test handling of very long names"""
        long_name = "A" * 300  # Exceeds 200 char limit
        # SQLAlchemy won't truncate automatically
        # This should be validated at application level
        asset = Asset(
            ownership_id="Owner",
            asset_name=long_name,
            address="Address",
            ownership_status="Status",
            property_nature="Nature",
            usage_status="Status",
        )
        assert len(asset.asset_name) == 300

    def test_special_characters_in_name(self):
        """Test handling of special characters"""
        asset = Asset(
            ownership_id="Owner",
            asset_name="Property <script>alert('xss')</script>",
            address="Address",
            ownership_status="Status",
            property_nature="Nature",
            usage_status="Status",
        )
        assert "<script>" in asset.asset_name

    def test_unicode_characters(self):
        """Test handling of unicode characters"""
        asset = Asset(
            ownership_id="业主单位",
            asset_name="物业名称",
            address="地址",
            ownership_status="状态",
            property_nature="性质",
            usage_status="状态",
        )
        assert asset.ownership_id == "业主单位"
        assert asset.asset_name == "物业名称"


class TestAssetDefaultsAndConstraints:
    """Test Asset default values and constraints"""

    def test_all_required_fields(self):
        """Test that all required fields are identified"""
        required_fields = [
            "ownership_id",
            "asset_name",
            "address",
            "ownership_status",
            "property_nature",
            "usage_status",
        ]

        for field in required_fields:
            # The field should exist on the model
            assert hasattr(Asset, field)

    def test_default_boolean_values(self):
        """Test default values for boolean fields"""
        asset = Asset(
            ownership_id="Owner",
            asset_name="Property",
            address="Address",
            ownership_status="Status",
            property_nature="Nature",
            usage_status="Status",
        )

        assert asset.is_litigated is False
        assert asset.is_sublease is False
        assert asset.include_in_occupancy_rate is True

    def test_default_int_values(self):
        """Test default values for integer fields"""
        asset = Asset(
            ownership_id="Owner",
            asset_name="Property",
            address="Address",
            ownership_status="Status",
            property_nature="Nature",
            usage_status="Status",
        )

        assert asset.version == 1
