"""
Comprehensive unit tests for field whitelist system.

Tests cover:
- Whitelist configuration validation
- QueryBuilder whitelist integration
- Security scenarios (blocked fields)
- Special cases (sorting allowed, filtering blocked)
"""

from src.crud.field_whitelist import (
    WHITELIST_REGISTRY,
    AssetWhitelist,
    EmptyWhitelist,
    OwnershipWhitelist,
    RentContractWhitelist,
    get_whitelist_for_model,
    register_whitelist,
)


class TestAssetWhitelist:
    """Test Asset model whitelist configuration."""

    def test_safe_filter_fields_allowed(self):
        """Public and internal fields should be allowed for filtering."""
        whitelist = AssetWhitelist()

        # Basic classification fields
        assert whitelist.can_filter("ownership_status")
        assert whitelist.can_filter("property_nature")
        assert whitelist.can_filter("usage_status")
        assert whitelist.can_filter("business_category")
        assert whitelist.can_filter("management_entity")
        assert whitelist.can_filter("is_litigated")
        assert whitelist.can_filter("data_status")

        # Area fields (public metrics)
        assert whitelist.can_filter("actual_property_area")
        assert whitelist.can_filter("rentable_area")
        assert whitelist.can_filter("rented_area")
        assert whitelist.can_filter("cached_occupancy_rate")
        assert whitelist.can_filter("land_area")

        # Boolean flags
        assert whitelist.can_filter("include_in_occupancy_rate")
        assert whitelist.can_filter("is_sublease")

        # References
        assert whitelist.can_filter("manager_party_id")
        assert whitelist.can_filter("owner_party_id")
        assert whitelist.can_filter("ownership_id")
        assert not whitelist.can_filter("project_id")

        # System fields
        assert whitelist.can_filter("version")
        assert whitelist.can_filter("tags")
        assert whitelist.can_filter("created_at")
        assert whitelist.can_filter("updated_at")

    def test_sensitive_filter_fields_blocked(self):
        """Sensitive fields should be blocked for filtering."""
        whitelist = AssetWhitelist()

        # PII fields
        assert not whitelist.can_filter("manager_name")
        assert not whitelist.can_filter("tenant_name")
        assert not whitelist.can_filter("project_phone")

        # Financial fields (blocked for filtering, allowed for sorting)
        assert not whitelist.can_filter("monthly_rent")
        assert not whitelist.can_filter("deposit")

        # Operational intelligence
        assert not whitelist.can_filter("operation_status")
        assert not whitelist.can_filter("lease_contract_number")

        # Audit trail
        assert not whitelist.can_filter("created_by")
        assert not whitelist.can_filter("updated_by")

    def test_search_fields_allowed(self):
        """Public text fields should be searchable."""
        whitelist = AssetWhitelist()

        assert whitelist.can_search("property_name")
        assert whitelist.can_search("address")
        assert whitelist.can_search("project_name")
        assert whitelist.can_search("notes")
        assert whitelist.can_search("property_nature")
        assert whitelist.can_search("usage_status")
        assert whitelist.can_search("ownership_status")
        assert not whitelist.can_search("ownership_entity")

    def test_pii_search_fields_blocked(self):
        """PII fields should not be searchable."""
        whitelist = AssetWhitelist()

        assert not whitelist.can_search("manager_name")
        assert not whitelist.can_search("tenant_name")
        assert not whitelist.can_search("project_phone")

    def test_sort_fields_allowed(self):
        """Sorting should be allowed on display fields."""
        whitelist = AssetWhitelist()

        # Time-based sorting
        assert whitelist.can_sort("created_at")
        assert whitelist.can_sort("updated_at")

        # Numeric sorting
        assert whitelist.can_sort("land_area")
        assert whitelist.can_sort("actual_property_area")
        assert whitelist.can_sort("rentable_area")
        assert whitelist.can_sort("rented_area")
        assert whitelist.can_sort("cached_occupancy_rate")

        # Alphabetic sorting
        assert whitelist.can_sort("property_name")
        assert whitelist.can_sort("project_name")
        assert not whitelist.can_sort("ownership_entity")

    def test_blocked_sort_fields(self):
        """Audit trail and operational fields blocked for sorting."""
        whitelist = AssetWhitelist()

        assert not whitelist.can_sort("manager_name")
        assert not whitelist.can_sort("tenant_name")
        assert not whitelist.can_sort("operation_status")
        assert not whitelist.can_sort("created_by")
        assert not whitelist.can_sort("updated_by")


class TestRentContractWhitelist:
    """Test RentContract whitelist configuration."""

    def test_safe_fields_allowed(self):
        """Safe contract fields should be accessible."""
        whitelist = RentContractWhitelist()

        assert whitelist.can_filter("contract_status")
        assert whitelist.can_filter("start_date")
        assert whitelist.can_filter("end_date")
        assert whitelist.can_filter("payment_cycle")
        assert whitelist.can_search("contract_number")
        assert whitelist.can_sort("start_date")

    def test_phone_fields_blocked(self):
        """Encrypted phone fields should not be discoverable."""
        whitelist = RentContractWhitelist()

        # Phone fields should be blocked for all operations
        assert not whitelist.can_filter("owner_phone")
        assert not whitelist.can_filter("tenant_phone")
        assert not whitelist.can_search("owner_phone")
        assert not whitelist.can_search("tenant_phone")
        assert not whitelist.can_sort("owner_phone")
        assert not whitelist.can_sort("tenant_phone")

    def test_tenant_name_blocked(self):
        """Tenant name is business-sensitive, should be blocked."""
        whitelist = RentContractWhitelist()

        assert not whitelist.can_filter("tenant_name")
        assert not whitelist.can_search("tenant_name")

    def test_financial_sorting_allowed(self):
        """Financial fields can be sorted but not filtered."""
        whitelist = RentContractWhitelist()

        # Sorting allowed for display
        assert whitelist.can_sort("monthly_rent_base")
        assert whitelist.can_sort("total_deposit")


class TestEmptyWhitelist:
    """Test strict whitelist (future default)."""

    def test_blocks_all_fields(self):
        """Empty whitelist blocks all fields."""
        whitelist = EmptyWhitelist()

        assert not whitelist.can_filter("any_field")
        assert not whitelist.can_search("any_field")
        assert not whitelist.can_sort("any_field")


class TestWhitelistRegistry:
    """Test whitelist registration and lookup."""

    def test_register_and_retrieve_whitelist(self):
        """Should be able to register and retrieve whitelists."""

        # Create a mock model class
        class MockModel:
            __name__ = "MockModel"

        # Create a custom whitelist
        custom_whitelist = AssetWhitelist()

        # Register it
        register_whitelist(MockModel, custom_whitelist)

        # Retrieve it
        retrieved = get_whitelist_for_model(MockModel)

        # Should be the same instance
        assert retrieved is custom_whitelist

    def test_unregistered_model_returns_empty(self):
        """Models without whitelists should get EmptyWhitelist (security-first)."""

        # Create a mock model class (not registered)
        class UnregisteredModel:
            __name__ = "UnregisteredModel"

        # Should return EmptyWhitelist (deny all fields)
        whitelist = get_whitelist_for_model(UnregisteredModel)
        assert isinstance(whitelist, EmptyWhitelist)
        # Verify it blocks all fields
        assert not whitelist.can_filter("any_field")
        assert not whitelist.can_search("any_field")
        assert not whitelist.can_sort("any_field")

    def test_ownership_model_uses_ownership_whitelist(self):
        """Ownership model should use dedicated whitelist."""
        from src.models.ownership import Ownership

        # Ownership should have explicit whitelist (no empty-whitelist fallback).
        whitelist = get_whitelist_for_model(Ownership)
        assert isinstance(whitelist, OwnershipWhitelist)
        assert whitelist.can_filter("is_active")
        assert whitelist.can_search("name")
        assert whitelist.can_sort("created_at")

    def test_registry_isolation(self):
        """Registry should maintain separate entries per model."""
        # Save original registry state
        original_registry = dict(WHITELIST_REGISTRY)

        try:
            # Clear registry for clean test
            WHITELIST_REGISTRY.clear()

            class Model1:
                __name__ = "Model1"

            class Model2:
                __name__ = "Model2"

            whitelist1 = AssetWhitelist()
            whitelist2 = RentContractWhitelist()

            register_whitelist(Model1, whitelist1)
            register_whitelist(Model2, whitelist2)

            assert get_whitelist_for_model(Model1) is whitelist1
            assert get_whitelist_for_model(Model2) is whitelist2
        finally:
            # Restore original registry
            WHITELIST_REGISTRY.clear()
            for model, whitelist in original_registry.items():
                WHITELIST_REGISTRY[model] = whitelist


class TestQueryBuilderIntegration:
    """Test QueryBuilder whitelist integration (unit level)."""

    def test_querybuilder_loads_whitelist(self):
        """QueryBuilder should load whitelist on initialization."""
        from src.crud.field_whitelist import AssetWhitelist, register_whitelist
        from src.crud.query_builder import QueryBuilder
        from src.models.asset import Asset

        # Explicitly register whitelist for this test
        register_whitelist(Asset, AssetWhitelist())

        # Create QueryBuilder - it should use the registered whitelist
        qb = QueryBuilder(Asset)

        # Should have a whitelist
        assert qb.whitelist is not None

        # Should be the registered AssetWhitelist
        assert isinstance(qb.whitelist, AssetWhitelist)

    def test_querybuilder_logs_empty_whitelist_info(self, caplog):
        """QueryBuilder should log info when using EmptyWhitelist."""
        import logging

        from src.crud.query_builder import QueryBuilder

        # Create a mock model without whitelist
        class UnregisteredModel:
            __name__ = "UnregisteredModel"

        # Should log info
        with caplog.at_level(logging.INFO):
            QueryBuilder(UnregisteredModel)

        # Check info was logged
        assert any("EMPTY whitelist" in record.message for record in caplog.records)


class TestSecurityScenarios:
    """Test security-related scenarios."""

    def test_cannot_filter_pii(self):
        """Should not be able to filter by PII fields."""
        whitelist = AssetWhitelist()

        # Try all PII fields
        pii_fields = ["manager_name", "tenant_name", "project_phone"]

        for field in pii_fields:
            assert not whitelist.can_filter(field), (
                f"PII field '{field}' should be blocked for filtering"
            )

    def test_cannot_discover_financial_data(self):
        """Should not be able to filter by financial data."""
        whitelist = AssetWhitelist()

        # Financial fields should be blocked for filtering
        # (to prevent rent range discovery attacks)
        assert not whitelist.can_filter("monthly_rent")
        assert not whitelist.can_filter("deposit")

        # Also blocked for sorting (financial data now sourced from active contract)
        assert not whitelist.can_sort("monthly_rent")
        assert not whitelist.can_sort("deposit")

    def test_cannot_audit_user_activity(self):
        """Should not be able to filter by audit trail fields."""
        whitelist = AssetWhitelist()

        # Audit fields should be blocked
        assert not whitelist.can_filter("created_by")
        assert not whitelist.can_filter("updated_by")
        assert not whitelist.can_search("created_by")
        assert not whitelist.can_sort("created_by")

    def test_cannot_enumerate_phone_numbers(self):
        """Should not be able to enumerate phone numbers."""
        whitelist = RentContractWhitelist()

        # Phone fields should be completely blocked
        assert not whitelist.can_filter("owner_phone")
        assert not whitelist.can_filter("tenant_phone")
        assert not whitelist.can_search("owner_phone")
        assert not whitelist.can_search("tenant_phone")
        assert not whitelist.can_sort("owner_phone")
        assert not whitelist.can_sort("tenant_phone")

    def test_cannot_discover_operational_status(self):
        """Operational intelligence should be protected."""
        whitelist = AssetWhitelist()

        # Operation status is business-sensitive
        assert not whitelist.can_filter("operation_status")
        assert not whitelist.can_search("operation_status")
        assert not whitelist.can_sort("operation_status")
