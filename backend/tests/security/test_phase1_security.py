"""
Security Tests for Phase 1 - P0 Security Hardening

Tests for:
1. SECRET_KEY validation
2. Field filtering vulnerability protection
3. Encryption status monitoring

Created: 2026-01-17
"""

import pytest
from fastapi import HTTPException

from src.security.field_validator import FieldValidator


class TestFieldFilteringValidation:
    """Test field filtering vulnerability protection"""

    def test_validate_asset_filter_fields_allowed(self):
        """Test that allowed filter fields pass validation"""
        allowed_fields = ["property_name", "ownership_status", "land_area"]

        valid, invalid = FieldValidator.validate_filter_fields(
            "Asset", allowed_fields, raise_on_invalid=False
        )

        assert len(valid) == 3
        assert len(invalid) == 0
        assert set(valid) == set(allowed_fields)

    def test_validate_asset_filter_fields_blocked(self):
        """Test that blocked PII fields are rejected"""
        # manager_name is in blocked_fields
        blocked_fields = ["manager_name", "tenant_name", "project_phone"]

        valid, invalid = FieldValidator.validate_filter_fields(
            "Asset", blocked_fields, raise_on_invalid=False
        )

        assert len(valid) == 0
        assert len(invalid) == 3

    def test_validate_asset_filter_fields_raise_exception(self):
        """Test that invalid fields raise HTTPException in strict mode"""
        with pytest.raises(HTTPException) as exc_info:
            FieldValidator.validate_filter_fields(
                "Asset", ["manager_name"], raise_on_invalid=True
            )

        assert exc_info.value.status_code == 400
        assert "不允许查询字段" in exc_info.value.detail["message"]

    def test_validate_group_by_field_allowed(self):
        """Test that allowed group_by fields pass validation"""
        # ownership_status is in filter_fields whitelist
        is_valid = FieldValidator.validate_group_by_field(
            "Asset", "ownership_status", raise_on_invalid=False
        )

        assert is_valid is True

    def test_validate_group_by_field_blocked(self):
        """Test that blocked fields are rejected for group_by"""
        # manager_name is blocked
        is_valid = FieldValidator.validate_group_by_field(
            "Asset", "manager_name", raise_on_invalid=False
        )

        assert is_valid is False

    def test_validate_group_by_field_raise_exception(self):
        """Test that invalid group_by field raises HTTPException"""
        with pytest.raises(HTTPException) as exc_info:
            FieldValidator.validate_group_by_field(
                "Asset", "manager_name", raise_on_invalid=True
            )

        assert exc_info.value.status_code == 400
        assert "不允许按字段分组" in exc_info.value.detail["message"]

    def test_sanitize_filters(self):
        """Test filter sanitization removes unauthorized fields"""
        filters = {
            "property_name": "测试物业",  # Allowed
            "ownership_status": "已确权",  # Allowed
            "manager_name": "张三",  # Blocked
            "tenant_name": "李四",  # Blocked
        }

        sanitized = FieldValidator.sanitize_filters(
            "Asset", filters, strict=False
        )

        assert "property_name" in sanitized
        assert "ownership_status" in sanitized
        assert "manager_name" not in sanitized
        assert "tenant_name" not in sanitized
        assert len(sanitized) == 2

    def test_sanitize_filters_strict_mode(self):
        """Test that strict mode raises exception on unauthorized fields"""
        filters = {
            "property_name": "测试物业",
            "manager_name": "张三",  # Blocked
        }

        with pytest.raises(HTTPException):
            FieldValidator.sanitize_filters("Asset", filters, strict=True)

    def test_get_allowed_fields(self):
        """Test getting allowed fields for a model"""
        filter_fields = FieldValidator.get_allowed_fields("Asset", "filter")
        search_fields = FieldValidator.get_allowed_fields("Asset", "search")
        sort_fields = FieldValidator.get_allowed_fields("Asset", "sort")

        # Verify some expected fields
        assert "property_name" in filter_fields
        assert "property_name" in search_fields
        assert "property_name" in sort_fields

        # Verify blocked fields are not present
        assert "manager_name" not in filter_fields
        assert "tenant_name" not in filter_fields

    def test_validate_unknown_model(self):
        """Test that unknown model raises ValueError"""
        with pytest.raises(ValueError) as exc_info:
            FieldValidator.validate_filter_fields(
                "UnknownModel", ["field1"], raise_on_invalid=False
            )

        assert "Unknown model" in str(exc_info.value)

    def test_validate_search_fields_allowed(self):
        """Test search field validation for allowed fields"""
        # property_name is in search_fields whitelist
        valid, invalid = FieldValidator.validate_search_fields(
            "Asset", ["property_name", "address"], raise_on_invalid=False
        )

        assert len(valid) == 2
        assert len(invalid) == 0

    def test_validate_search_fields_blocked(self):
        """Test search field validation blocks unauthorized fields"""
        # manager_name is blocked
        valid, invalid = FieldValidator.validate_search_fields(
            "Asset", ["manager_name"], raise_on_invalid=False
        )

        assert len(valid) == 0
        assert len(invalid) == 1

    def test_validate_sort_field_allowed(self):
        """Test sort field validation for allowed fields"""
        is_valid = FieldValidator.validate_sort_field(
            "Asset", "property_name", raise_on_invalid=False
        )

        assert is_valid is True

    def test_validate_sort_field_blocked(self):
        """Test sort field validation blocks unauthorized fields"""
        # manager_name is blocked
        is_valid = FieldValidator.validate_sort_field(
            "Asset", "manager_name", raise_on_invalid=False
        )

        assert is_valid is False


class TestProductionConfigValidation:
    """Test production configuration validation"""

    def test_weak_secret_key_patterns_detected(self):
        """Test that weak SECRET_KEY patterns are detected"""
        from src.core.jwt_security import jwt_security

        weak_keys = [
            "EMERGENCY-ONLY-REPLACE-WITH-ENV-SECRET-KEY-NOW",
            "dev-secret-key-DO-NOT-USE-IN-PRODUCTION",
            "test-key-for-development",
        ]

        for weak_key in weak_keys:
            result = jwt_security.validate_secret_key(weak_key)
            assert result["is_valid"] is False
            assert len(result["issues"]) > 0

    def test_strong_secret_key_passes_validation(self):
        """Test that strong SECRET_KEY passes validation"""
        from src.core.jwt_security import jwt_security

        # Generate a strong key
        strong_key = jwt_security.generate_secure_secret()

        result = jwt_security.validate_secret_key(strong_key)
        assert result["is_valid"] is True
        assert len(result["issues"]) == 0

    def test_short_secret_key_rejected(self):
        """Test that short SECRET_KEY is rejected"""
        from src.core.jwt_security import jwt_security

        short_key = "short"

        result = jwt_security.validate_secret_key(short_key)
        assert result["is_valid"] is False
        assert any("长度不足" in issue for issue in result["issues"])


class TestEncryptionMonitoring:
    """Test encryption status monitoring (API endpoint tested separately)"""

    def test_encryption_key_manager_initialization(self):
        """Test that EncryptionKeyManager initializes correctly"""
        from src.core.encryption import EncryptionKeyManager

        key_manager = EncryptionKeyManager()

        # Should initialize without errors
        assert key_manager is not None
        assert hasattr(key_manager, "is_available")
        assert hasattr(key_manager, "get_version")

    def test_encryption_key_manager_no_key(self, monkeypatch):
        """Test encryption manager behavior when no key is set"""
        from src.core.encryption import EncryptionKeyManager

        # Clear the encryption key
        monkeypatch.setenv("DATA_ENCRYPTION_KEY", "")

        key_manager = EncryptionKeyManager()

        assert key_manager.is_available() is False
        assert key_manager.get_key() is None


# Integration Tests (require test database)
@pytest.mark.integration
class TestSecurityIntegration:
    """Integration tests for security features"""

    def test_statistics_endpoint_blocks_unauthorized_group_by(self, client, auth_headers):
        """Test that /statistics/asset-distribution blocks unauthorized group_by"""
        # Try to group by blocked field
        response = client.get(
            "/api/v1/statistics/asset-distribution?group_by=manager_name",
            headers=auth_headers
        )

        assert response.status_code == 400
        assert "不允许按字段分组" in response.json()["detail"]["message"]

    def test_statistics_endpoint_allows_authorized_group_by(self, client, auth_headers):
        """Test that /statistics/asset-distribution allows authorized group_by"""
        # Try to group by allowed field
        response = client.get(
            "/api/v1/statistics/asset-distribution?group_by=ownership_status",
            headers=auth_headers
        )

        # Should succeed (or fail for other reasons, not field validation)
        assert response.status_code != 400 or "不允许按字段分组" not in str(response.json())

    def test_encryption_status_endpoint(self, client, admin_auth_headers):
        """Test encryption status endpoint"""
        response = client.get(
            "/api/v1/monitoring/encryption-status",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert "encryption_enabled" in data
        assert "encryption_algorithm" in data
        assert "protected_fields" in data
        assert "total_protected_fields" in data

        # Verify protected fields structure
        protected_fields = data["protected_fields"]
        assert "Organization" in protected_fields
        assert "RentContract" in protected_fields
        assert "Contact" in protected_fields
        assert "Asset" in protected_fields
