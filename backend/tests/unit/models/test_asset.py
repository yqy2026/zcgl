"""
Asset Model Tests

Tests for the Asset model - core business entity for property/asset management.
"""

import os
from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.database import Base
from src.models.asset import Asset


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
        engine = create_engine(database_url, pool_pre_ping=True)
        Base.metadata.create_all(engine)
        return engine

    @pytest.fixture
    def session(self, engine):
        """Create database session"""
        with Session(engine) as session:
            yield session

    @pytest.fixture
    def sample_asset(self):
        """Create a sample Asset instance"""
        return Asset(
            ownership_entity="Test Corporation",
            property_name="Test Property",
            address="123 Test Street",
            ownership_status="已确权",
            property_nature="商业",
            usage_status="在用",
        )

    def test_asset_creation(self, sample_asset):
        """Test basic Asset creation"""
        assert sample_asset.ownership_entity == "Test Corporation"
        assert sample_asset.property_name == "Test Property"
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
        assert sample_asset.management_entity is None

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
            ownership_entity="Owner",
            property_name="Property",
            address="Address",
            ownership_status="Status",
            property_nature="Nature",
            usage_status="Status",
        )

    def test_string_fields(self, asset):
        """Test string field types"""
        assert isinstance(asset.ownership_entity, str)
        assert isinstance(asset.property_name, str)
        assert isinstance(asset.address, str)

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


class TestAssetAreaFields:
    """Test Asset area-related fields"""

    @pytest.fixture
    def asset_with_areas(self):
        return Asset(
            ownership_entity="Owner",
            property_name="Property",
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
            ownership_entity="Owner",
            property_name="Property",
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
        return Asset(
            ownership_entity="Owner",
            property_name="Property",
            address="Address",
            ownership_status="Status",
            property_nature="Nature",
            usage_status="Status",
            tenant_name="Test Tenant",
            tenant_type="企业",
            lease_contract_number="CONTRACT-001",
            contract_start_date=date(2024, 1, 1),
            contract_end_date=date(2024, 12, 31),
            monthly_rent=Decimal("5000.00"),
            deposit=Decimal("10000.00"),
        )

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

    def test_sublease_default(self, asset_with_contract):
        """Test sublease default value"""
        assert asset_with_contract.is_sublease is False


class TestAssetTimestamps:
    """Test Asset timestamp fields"""

    @pytest.fixture
    def asset(self):
        return Asset(
            ownership_entity="Owner",
            property_name="Property",
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
        assert asset.created_at.tzinfo is not None
        # datetime.now(UTC) creates timezone-aware datetime


class TestAssetManagementFields:
    """Test Asset management-related fields"""

    @pytest.fixture
    def managed_asset(self):
        return Asset(
            ownership_entity="Owner",
            property_name="Property",
            address="Address",
            ownership_status="Status",
            property_nature="Nature",
            usage_status="Status",
            management_entity="Management Corp",
            business_category="零售",
            business_model="直接接收",
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
            ownership_entity="Owner",
            property_name="Property",
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
            ownership_entity="Owner",
            property_name="Property",
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
            ownership_entity="Owner",
            property_name="Property",
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
            ownership_entity="Owner",
            property_name="Property",
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
        """Test that future dates are allowed for contracts"""
        future_date = date(2030, 12, 31)
        asset = Asset(
            ownership_entity="Owner",
            property_name="Property",
            address="Address",
            ownership_status="Status",
            property_nature="Nature",
            usage_status="Status",
            contract_end_date=future_date,
        )
        assert asset.contract_end_date == future_date


class TestAssetRelationships:
    """Test Asset relationships (without database)"""

    @pytest.fixture
    def asset(self):
        return Asset(
            ownership_entity="Owner",
            property_name="Property",
            address="Address",
            ownership_status="Status",
            property_nature="Nature",
            usage_status="Status",
        )

    def test_relationships_exist(self, asset):
        """Test that relationship attributes exist"""
        assert hasattr(asset, "history_records")
        assert hasattr(asset, "documents")
        assert hasattr(asset, "rent_contracts")
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
            ownership_entity="Test Owner",
            property_name="Test Property Name",
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

    def test_property_name_display(self, asset):
        """Test property_name is the main display field"""
        assert asset.property_name == "Test Property Name"


class TestAssetEdgeCases:
    """Test Asset edge cases and boundary conditions"""

    def test_very_long_names(self):
        """Test handling of very long names"""
        long_name = "A" * 300  # Exceeds 200 char limit
        # SQLAlchemy won't truncate automatically
        # This should be validated at application level
        asset = Asset(
            ownership_entity="Owner",
            property_name=long_name,
            address="Address",
            ownership_status="Status",
            property_nature="Nature",
            usage_status="Status",
        )
        assert len(asset.property_name) == 300

    def test_special_characters_in_name(self):
        """Test handling of special characters"""
        asset = Asset(
            ownership_entity="Owner",
            property_name="Property <script>alert('xss')</script>",
            address="Address",
            ownership_status="Status",
            property_nature="Nature",
            usage_status="Status",
        )
        assert "<script>" in asset.property_name

    def test_unicode_characters(self):
        """Test handling of unicode characters"""
        asset = Asset(
            ownership_entity="业主单位",
            property_name="物业名称",
            address="地址",
            ownership_status="状态",
            property_nature="性质",
            usage_status="状态",
        )
        assert asset.ownership_entity == "业主单位"
        assert asset.property_name == "物业名称"


class TestAssetDefaultsAndConstraints:
    """Test Asset default values and constraints"""

    def test_all_required_fields(self):
        """Test that all required fields are identified"""
        required_fields = [
            "ownership_entity",
            "property_name",
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
            ownership_entity="Owner",
            property_name="Property",
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
            ownership_entity="Owner",
            property_name="Property",
            address="Address",
            ownership_status="Status",
            property_nature="Nature",
            usage_status="Status",
        )

        assert asset.version == 1
