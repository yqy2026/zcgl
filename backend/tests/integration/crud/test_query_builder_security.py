"""
Integration tests for QueryBuilder security enforcement.

Tests actual database queries with whitelist validation.
"""

import pytest

# Import crud module to trigger whitelist registration
import src.crud  # noqa: F401
from src.core.exception_handler import InvalidRequestError
from src.crud.query_builder import QueryBuilder
from src.models.asset import Asset


@pytest.mark.usefixtures("db_tables")
class TestQueryBuilderSecurityIntegration:
    """Integration tests for whitelist enforcement with real queries."""

    def test_safe_filter_query_succeeds(self, db_session):
        """Allowed filter fields should execute successfully."""
        qb = QueryBuilder(Asset)

        # Safe filters
        filters = {
            "ownership_status": "已确权",
            "usage_status": "在用",
            "data_status": "正常",
        }

        # Should not raise any errors
        query = qb.build_query(filters=filters)

        # Verify query is built
        assert query is not None

        # Should be able to execute
        result = db_session.execute(query).scalars().all()
        assert isinstance(result, list)

    def test_range_filter_on_allowed_field_succeeds(self, db_session):
        """Range filters on allowed fields should work."""
        qb = QueryBuilder(Asset)

        # Area fields are allowed for filtering
        filters = {
            "min_actual_property_area": "100",
            "max_actual_property_area": "500",
        }

        query = qb.build_query(filters=filters)
        result = db_session.execute(query).scalars().all()
        assert isinstance(result, list)

    def test_blocked_filter_field_raises_error(self, db_session):
        """Blocked filter fields should raise InvalidRequestError."""
        qb = QueryBuilder(Asset)

        # Try to filter by PII field
        filters = {"manager_name": "Test Manager"}

        # Should raise InvalidRequestError
        with pytest.raises(InvalidRequestError) as exc_info:
            qb.build_query(filters=filters)

        # Error message should be clear
        assert "not allowed" in str(exc_info.value).lower()
        assert "manager_name" in str(exc_info.value)

    def test_blocked_tenant_filter_raises_error(self, db_session):
        """Filtering by tenant name should be blocked."""
        qb = QueryBuilder(Asset)

        filters = {"tenant_name": "Test Tenant"}

        with pytest.raises(InvalidRequestError) as exc_info:
            qb.build_query(filters=filters)

        assert "tenant_name" in str(exc_info.value)
        assert "not allowed" in str(exc_info.value).lower()

    def test_financial_filter_blocked(self, db_session):
        """Financial fields should be blocked for filtering."""
        qb = QueryBuilder(Asset)

        # Try to filter by rent amount (discovery attack)
        filters = {
            "min_monthly_rent": "1000",
            "max_monthly_rent": "5000",
        }

        with pytest.raises(InvalidRequestError) as exc_info:
            qb.build_query(filters=filters)

        assert "monthly_rent" in str(exc_info.value)

    def test_audit_filter_blocked(self, db_session):
        """Filtering by audit trail fields should be blocked."""
        qb = QueryBuilder(Asset)

        # Try to filter by created_by (user discovery)
        filters = {"created_by": "admin"}

        with pytest.raises(InvalidRequestError) as exc_info:
            qb.build_query(filters=filters)

        assert "created_by" in str(exc_info.value)

    def test_search_sanitization(self, db_session):
        """Search should sanitize blocked fields."""
        qb = QueryBuilder(Asset)

        # Include both safe and blocked fields
        search_fields = ["property_name", "manager_name", "address"]

        # Should not raise error - blocked fields skipped silently
        query = qb.build_query(
            search_query="test",
            search_fields=search_fields,
        )

        # Query should succeed
        result = db_session.execute(query).scalars().all()
        assert isinstance(result, list)

    def test_blocked_search_field_skipped(self, db_session):
        """Blocked search fields should be skipped with warning."""

        qb = QueryBuilder(Asset)

        # Only blocked fields
        search_fields = ["manager_name", "tenant_name", "project_phone"]

        # Should log warnings but not raise error
        # Blocked fields are skipped, so query succeeds but no search is applied
        query = qb.build_query(
            search_query="test",
            search_fields=search_fields,
        )
        # Query succeeds but no search is applied (all blocked fields were skipped)
        result = db_session.execute(query).scalars().all()
        assert isinstance(result, list)

    def test_safe_sort_succeeds(self, db_session):
        """Allowed sort fields should work."""
        qb = QueryBuilder(Asset)

        # Safe sort fields
        sort_fields = [
            "created_at",
            "updated_at",
            "property_name",
            "actual_property_area",
        ]

        for sort_field in sort_fields:
            query = qb.build_query(sort_by=sort_field, sort_desc=True)
            result = db_session.execute(query).scalars().all()
            assert isinstance(result, list)

    def test_financial_sort_allowed(self, db_session):
        """Sorting by financial fields should be allowed (for display)."""
        qb = QueryBuilder(Asset)

        # Can sort by rent amounts
        query = qb.build_query(sort_by="monthly_rent", sort_desc=True)
        result = db_session.execute(query).scalars().all()
        assert isinstance(result, list)

        query = qb.build_query(sort_by="deposit", sort_desc=True)
        result = db_session.execute(query).scalars().all()
        assert isinstance(result, list)

    def test_blocked_sort_field_raises_error(self, db_session):
        """Blocked sort fields should raise InvalidRequestError."""
        qb = QueryBuilder(Asset)

        # Try to sort by PII field
        with pytest.raises(InvalidRequestError) as exc_info:
            qb.build_query(sort_by="manager_name")

        assert "not allowed" in str(exc_info.value).lower()
        assert "manager_name" in str(exc_info.value)

    def test_blocked_audit_sort_raises_error(self, db_session):
        """Sorting by audit fields should be blocked."""
        qb = QueryBuilder(Asset)

        with pytest.raises(InvalidRequestError) as exc_info:
            qb.build_query(sort_by="created_by")

        assert "created_by" in str(exc_info.value)

    def test_combined_filter_and_sort(self, db_session):
        """Combined filter and sort should both be validated."""
        qb = QueryBuilder(Asset)

        # Safe filter + safe sort
        query = qb.build_query(
            filters={"ownership_status": "已确权"},
            sort_by="created_at",
            sort_desc=True,
        )

        result = db_session.execute(query).scalars().all()
        assert isinstance(result, list)

    def test_blocked_sort_in_combined_query(self, db_session):
        """Blocked sort should raise error even with safe filters."""
        qb = QueryBuilder(Asset)

        # Safe filter + safe sort (monthly_rent is allowed for sorting, just not filtering)
        query = qb.build_query(
            filters={"ownership_status": "已确权"},
            sort_by="monthly_rent",  # Allowed for sorting (display), blocked for filtering (discovery)
            sort_desc=True,
        )
        result = db_session.execute(query).scalars().all()
        assert isinstance(result, list)

        # Now test with a truly blocked field (manager_name)
        with pytest.raises(InvalidRequestError) as exc_info:
            qb.build_query(
                filters={"ownership_status": "已确权"},
                sort_by="manager_name",  # Blocked for sorting (PII field)
                sort_desc=True,
            )

        assert "manager_name" in str(exc_info.value)

    def test_count_query_with_filters(self, db_session):
        """Count queries should also validate filters."""
        qb = QueryBuilder(Asset)

        # Safe filters
        query = qb.build_count_query(filters={"ownership_status": "已确权"})
        result = db_session.execute(query).scalar()
        assert isinstance(result, int)

    def test_count_query_blocked_filter(self, db_session):
        """Count queries should validate filters too."""
        qb = QueryBuilder(Asset)

        # Blocked filter
        with pytest.raises(InvalidRequestError) as exc_info:
            qb.build_count_query(filters={"manager_name": "Test"})

        assert "manager_name" in str(exc_info.value)

    def test_empty_filters_no_validation(self, db_session):
        """Empty filters should not trigger validation."""
        qb = QueryBuilder(Asset)

        # Empty filter dict
        query = qb.build_query(filters={})
        result = db_session.execute(query).scalars().all()
        assert isinstance(result, list)

    def test_none_filter_values_skipped(self, db_session):
        """None values in filters should be skipped without validation."""
        qb = QueryBuilder(Asset)

        # Filter with None values
        filters = {
            "ownership_status": "已确权",
            "manager_name": None,  # Should be skipped
            "monthly_rent": None,  # Should be skipped
        }

        # Should not raise error because None values are skipped
        query = qb.build_query(filters=filters)
        result = db_session.execute(query).scalars().all()
        assert isinstance(result, list)


@pytest.mark.usefixtures("db_tables")
class TestSecurityAttackScenarios:
    """Test realistic security attack scenarios."""

    def test_user_discovery_attack_blocked(self, db_session):
        """Attempt to discover users via created_by filter should be blocked."""
        qb = QueryBuilder(Asset)

        # Try to enumerate users
        filters = {"created_by": "admin"}

        with pytest.raises(InvalidRequestError) as exc_info:
            qb.build_query(filters=filters)

        assert "created_by" in str(exc_info.value)

    def test_rent_discovery_attack_blocked(self, db_session):
        """Attempt to discover rent ranges should be blocked."""
        qb = QueryBuilder(Asset)

        # Try to find high-rent properties
        filters = {"min_monthly_rent": "10000"}

        with pytest.raises(InvalidRequestError) as exc_info:
            qb.build_query(filters=filters)

        assert "monthly_rent" in str(exc_info.value)

    def test_pii_enumeration_attack_blocked(self, db_session):
        """Attempt to enumerate PII should be blocked."""
        qb = QueryBuilder(Asset)

        # Try various PII fields
        pii_fields = ["manager_name", "tenant_name"]

        for field in pii_fields:
            filters = {field: "test"}
            with pytest.raises(InvalidRequestError) as exc_info:
                qb.build_query(filters=filters)
            assert field in str(exc_info.value)

    def test_field_enumeration_attack_partially_blocked(self, db_session):
        """
        Attempting to enumerate all fields will be partially blocked.

        Note: Some fields are still allowed (public ones), so the query
        will succeed but blocked fields will raise errors.
        """
        qb = QueryBuilder(Asset)

        # Try to filter by a blocked field
        filters = {"manager_name": "test"}

        with pytest.raises(InvalidRequestError):
            qb.build_query(filters=filters)

    def test_data_exfiltration_via_sort_blocked(self, db_session):
        """Attempting to sort by sensitive fields should be blocked."""
        qb = QueryBuilder(Asset)

        # Try to sort by audit trail
        with pytest.raises(InvalidRequestError) as exc_info:
            qb.build_query(sort_by="created_by")

        assert "created_by" in str(exc_info.value)

    def test_contract_discovery_blocked(self, db_session):
        """Attempting to discover contract details should be blocked."""
        from src.models.rent_contract import RentContract

        qb = QueryBuilder(RentContract)

        # Try to filter by tenant name
        filters = {"tenant_name": "test"}

        with pytest.raises(InvalidRequestError) as exc_info:
            qb.build_query(filters=filters)

        assert "tenant_name" in str(exc_info.value)

    def test_phone_discovery_blocked(self, db_session):
        """Attempting to discover phone numbers should be blocked."""
        from src.models.rent_contract import RentContract

        qb = QueryBuilder(RentContract)

        # Try to filter by phone
        filters = {"owner_phone": "13800138000"}

        with pytest.raises(InvalidRequestError) as exc_info:
            qb.build_query(filters=filters)

        assert "owner_phone" in str(exc_info.value)


class TestWhitelistCompliance:
    """Test that all models comply with whitelist requirements."""

    def test_asset_has_whitelist(self):
        """Asset model should have a whitelist registered."""
        from src.crud.field_whitelist import EmptyWhitelist, get_whitelist_for_model

        whitelist = get_whitelist_for_model(Asset)

        # Should not be EmptyWhitelist (should have explicit whitelist)
        assert not isinstance(whitelist, EmptyWhitelist), (
            "Asset should have explicit whitelist, not empty"
        )

    def test_rent_contract_has_whitelist(self):
        """RentContract model should have a whitelist registered."""
        from src.crud.field_whitelist import (
            EmptyWhitelist,
            get_whitelist_for_model,
        )
        from src.models.rent_contract import RentContract

        whitelist = get_whitelist_for_model(RentContract)
        assert not isinstance(whitelist, EmptyWhitelist), (
            "RentContract should have explicit whitelist"
        )

    def test_ownership_has_whitelist(self):
        """Ownership model should have a whitelist registered."""
        from src.crud.field_whitelist import (
            EmptyWhitelist,
            get_whitelist_for_model,
        )
        from src.models.ownership import Ownership  # Ownership lives in models/ownership.py

        whitelist = get_whitelist_for_model(Ownership)
        assert not isinstance(whitelist, EmptyWhitelist), (
            "Ownership should have explicit whitelist"
        )
