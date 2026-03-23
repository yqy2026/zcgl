"""
Request Security Tests

Tests for request security utilities including:
- Input sanitization
- Email/phone validation
- URL safety checking
- Field validation against whitelist
"""

from unittest.mock import Mock, patch

import pytest

from src.core.exception_handler import InvalidRequestError
from src.security.security import (
    MODEL_REGISTRY,
    FieldValidator,
    RequestSecurity,
)


class TestInputSanitization:
    """Test input sanitization"""

    @pytest.fixture
    def sanitizer(self):
        return RequestSecurity()

    def test_sanitize_normal_string(self, sanitizer):
        """Test sanitizing normal strings"""
        result = sanitizer.sanitize_input("Hello World")
        assert result == "Hello World"

    def test_sanitize_null_bytes(self, sanitizer):
        """Test removal of null bytes"""
        result = sanitizer.sanitize_input("Hello\x00World")
        assert result == "HelloWorld"
        assert "\x00" not in result

    def test_sanitize_control_characters(self, sanitizer):
        """Test removal of control characters"""
        # Various control characters
        result = sanitizer.sanitize_input("Text\x01\x02\x03Here")
        assert "\x01" not in result
        assert "\x02" not in result
        assert "\x03" not in result

    def test_sanitize_whitespace(self, sanitizer):
        """Test whitespace trimming"""
        result = sanitizer.sanitize_input("  Hello World  ")
        assert result == "Hello World"

    def test_sanitize_non_string(self, sanitizer):
        """Test that non-strings are returned as-is"""
        result = sanitizer.sanitize_input(12345)
        assert result == 12345

        result = sanitizer.sanitize_input(None)
        assert result is None

    def test_sanitize_malicious_input(self, sanitizer):
        """Test sanitization of potentially malicious input"""
        malicious = "Normal\x00Text\x1b[31mRed"
        result = sanitizer.sanitize_input(malicious)

        assert "\x00" not in result
        assert "NormalText" in result


class TestEmailValidation:
    """Test email validation"""

    @pytest.fixture
    def validator(self):
        return RequestSecurity()

    def test_valid_emails(self, validator):
        """Test that valid emails pass validation"""
        valid_emails = [
            "user@example.com",
            "test.user@domain.co.uk",
            "user+tag@example.org",
            "user_name@test-domain.com",
            "123user@example.com",
        ]

        for email in valid_emails:
            assert validator.validate_email(email) is True

    def test_invalid_emails(self, validator):
        """Test that invalid emails fail validation"""
        invalid_emails = [
            "plainaddress",
            "@missingusername.com",
            "username@",
            "username@.com",
            "username@com",
            "username..name@example.com",
            "username@example..com",
            "username@-example.com",
            "username@example-.com",
        ]

        for email in invalid_emails:
            assert validator.validate_email(email) is False

    def test_email_case_insensitive(self, validator):
        """Test that email validation is case-insensitive"""
        assert validator.validate_email("USER@EXAMPLE.COM") is True
        assert validator.validate_email("User@Example.COM") is True


class TestPhoneValidation:
    """Test phone number validation"""

    @pytest.fixture
    def validator(self):
        return RequestSecurity()

    def test_valid_phones(self, validator):
        """Test that valid Chinese phone numbers pass"""
        valid_phones = [
            "13123456789",
            "15123456789",
            "18123456789",
            "19123456789",
        ]

        for phone in valid_phones:
            assert validator.validate_phone(phone) is True

    def test_invalid_phones(self, validator):
        """Test that invalid phone numbers fail"""
        invalid_phones = [
            "12345678901",  # Starts with 1, but second digit is 2
            "1312345678",  # Too short
            "131234567890",  # Too long
            "23123456789",  # Wrong first digit
            "abcdefghijk",  # Not numeric
            "131-2345-6789",  # Contains dashes
        ]

        for phone in invalid_phones:
            assert validator.validate_phone(phone) is False

    def test_phone_starts_with_1(self, validator):
        """Test that phone must start with 1"""
        assert validator.validate_phone("13123456789") is True
        assert validator.validate_phone("23123456789") is False


class TestURLSafety:
    """Test URL safety validation"""

    @pytest.fixture
    def validator(self):
        return RequestSecurity()

    def test_safe_urls(self, validator):
        """Test that safe URLs pass validation"""
        safe_urls = [
            "https://example.com",
            "http://example.com/path",
            "https://example.com?query=value",
            "https://subdomain.example.com",
        ]

        for url in safe_urls:
            assert validator.is_safe_url(url) is True

    def test_missing_protocol(self, validator):
        """Test that URLs without protocol are rejected"""
        unsafe_urls = [
            "example.com",
            "//example.com",
            "ftp://example.com",
            "javascript:alert('xss')",
        ]

        for url in unsafe_urls:
            assert validator.is_safe_url(url) is False

    def test_dangerous_characters(self, validator):
        """Test that URLs with dangerous characters are rejected"""
        dangerous_urls = [
            "https://example.com/<script>",
            "https://example.com/user?id=1' OR '1'='1",
            "https://example.com/page#<>",
            "https://example.com/path|command",
        ]

        for url in dangerous_urls:
            assert validator.is_safe_url(url) is False

    def test_javascript_protocol(self, validator):
        """Test that javascript: protocol is blocked"""
        js_urls = [
            "javascript:alert('XSS')",
            "JAVASCRIPT:alert('XSS')",
            "Javascript:alert('XSS')",
        ]

        for url in js_urls:
            assert validator.is_safe_url(url) is False

    def test_data_protocol(self, validator):
        """Test that data: URLs are rejected"""
        assert (
            validator.is_safe_url("data:text/html,<script>alert('XSS')</script>")
            is False
        )


class TestFieldValidator:
    """Test field validator against whitelist"""

    @pytest.fixture
    def validator(self):
        return FieldValidator()

    def test_model_registry(self):
        """Test that model registry is configured"""
        assert "Asset" in MODEL_REGISTRY
        assert "Contract" in MODEL_REGISTRY
        assert "Organization" in MODEL_REGISTRY
        assert "Contact" in MODEL_REGISTRY

    def test_get_model_class_valid(self, validator):
        """Test getting valid model class"""
        from src.models.asset import Asset

        model_class = validator._get_model_class("Asset")
        assert model_class == Asset

    def test_get_model_class_legacy_contract_alias_retired(self, validator):
        """Legacy contract model alias should be rejected."""
        legacy_model_name = "Rent" + "Contract"

        with pytest.raises(InvalidRequestError, match="未知的模型"):
            validator._get_model_class(legacy_model_name)

    def test_get_model_class_invalid(self, validator):
        """Test that invalid model raises error"""
        with pytest.raises(InvalidRequestError, match="未知的模型"):
            validator._get_model_class("InvalidModel")

    @patch("src.security.security.get_whitelist_for_model")
    def test_validate_field_allowed(self, mock_get_whitelist, validator):
        """Test validating allowed field"""

        # Mock whitelist to allow field
        mock_whitelist = Mock()
        mock_whitelist.can_filter.return_value = True
        mock_get_whitelist.return_value = mock_whitelist

        result = validator.validate_field("Asset", "name", raise_on_invalid=False)
        assert result is True

    @patch("src.security.security.get_whitelist_for_model")
    def test_validate_field_blocked(self, mock_get_whitelist, validator):
        """Test that blocked field raises error"""

        # Mock whitelist to deny field
        mock_whitelist = Mock()
        mock_whitelist.can_filter.return_value = False
        mock_get_whitelist.return_value = mock_whitelist

        with pytest.raises(InvalidRequestError, match="不允许按字段查询"):
            validator.validate_field("Asset", "blocked_field")

    @patch("src.security.security.get_whitelist_for_model")
    def test_validate_field_no_exception(self, mock_get_whitelist, validator):
        """Test validating field without raising exception"""
        mock_whitelist = Mock()
        mock_whitelist.can_filter.return_value = False
        mock_get_whitelist.return_value = mock_whitelist

        result = validator.validate_field(
            "Asset", "blocked_field", raise_on_invalid=False
        )
        assert result is False

    @patch("src.security.security.get_whitelist_for_model")
    def test_validate_filter_fields_mixed(self, mock_get_whitelist, validator):
        """Test validating multiple filter fields"""
        mock_whitelist = Mock()
        mock_whitelist.can_filter.side_effect = lambda field: field in [
            "name",
            "status",
        ]
        mock_get_whitelist.return_value = mock_whitelist

        valid, invalid = validator.validate_filter_fields(
            "Asset", ["name", "status", "blocked_field"], raise_on_invalid=False
        )

        assert valid == ["name", "status"]
        assert invalid == ["blocked_field"]

    @patch("src.security.security.get_whitelist_for_model")
    def test_validate_sort_field(self, mock_get_whitelist, validator):
        """Test validating sort field"""
        mock_whitelist = Mock()
        mock_whitelist.can_sort.return_value = True
        mock_get_whitelist.return_value = mock_whitelist

        result = validator.validate_sort_field(
            "Asset", "created_at", raise_on_invalid=False
        )
        assert result is True

    @patch("src.security.security.get_whitelist_for_model")
    def test_validate_search_field(self, mock_get_whitelist, validator):
        """Test validating search field"""
        mock_whitelist = Mock()
        mock_whitelist.can_search.return_value = True
        mock_get_whitelist.return_value = mock_whitelist

        result = validator.validate_search_field(
            "Asset", "name", raise_on_invalid=False
        )
        assert result is True

    @patch("src.security.security.get_whitelist_for_model")
    def test_validate_group_by_field(self, mock_get_whitelist, validator):
        """Test validating group by field"""
        mock_whitelist = Mock()
        mock_whitelist.can_filter.return_value = True
        mock_get_whitelist.return_value = mock_whitelist

        result = validator.validate_group_by_field(
            "Asset", "status", raise_on_invalid=False
        )
        assert result is True

    @patch("src.security.security.get_whitelist_for_model")
    def test_sanitize_filters(self, mock_get_whitelist, validator):
        """Test filter sanitization"""
        mock_whitelist = Mock()
        mock_whitelist.can_filter.side_effect = lambda field: field in [
            "name",
            "status",
        ]
        mock_get_whitelist.return_value = mock_whitelist

        filters = {
            "name": "Test",
            "status": "active",
            "blocked_field": "value",
        }

        sanitized = validator.sanitize_filters("Asset", filters, strict=False)

        assert sanitized == {"name": "Test", "status": "active"}
        assert "blocked_field" not in sanitized

    @patch("src.security.security.get_whitelist_for_model")
    def test_sanitize_filters_strict(self, mock_get_whitelist, validator):
        """Test filter sanitization in strict mode"""
        mock_whitelist = Mock()
        mock_whitelist.can_filter.side_effect = lambda field: field == "name"
        mock_get_whitelist.return_value = mock_whitelist

        filters = {
            "name": "Test",
            "blocked_field": "value",
        }

        with pytest.raises(InvalidRequestError):
            validator.sanitize_filters("Asset", filters, strict=True)

    @patch("src.security.security.get_whitelist_for_model")
    def test_get_allowed_fields_filter(self, mock_get_whitelist, validator):
        """Test getting allowed filter fields"""
        mock_whitelist = Mock()
        mock_whitelist.filter_fields = {"name", "status", "created_at"}
        mock_get_whitelist.return_value = mock_whitelist

        fields = validator.get_allowed_fields("Asset", "filter")

        assert isinstance(fields, list)
        assert "name" in fields
        assert "status" in fields

    @patch("src.security.security.get_whitelist_for_model")
    def test_get_allowed_fields_search(self, mock_get_whitelist, validator):
        """Test getting allowed search fields"""
        mock_whitelist = Mock()
        mock_whitelist.search_fields = {"name", "description"}
        mock_get_whitelist.return_value = mock_whitelist

        fields = validator.get_allowed_fields("Asset", "search")

        assert "name" in fields
        assert "description" in fields

    @patch("src.security.security.get_whitelist_for_model")
    def test_get_allowed_fields_sort(self, mock_get_whitelist, validator):
        """Test getting allowed sort fields"""
        mock_whitelist = Mock()
        mock_whitelist.sort_fields = {"created_at", "name"}
        mock_get_whitelist.return_value = mock_whitelist

        fields = validator.get_allowed_fields("Asset", "sort")

        assert "created_at" in fields
        assert "name" in fields

    def test_get_allowed_fields_invalid_type(self, validator):
        """Test that invalid field type raises error"""
        with patch(
            "src.security.security.get_whitelist_for_model"
        ) as mock_get_whitelist:
            mock_whitelist = Mock()
            mock_get_whitelist.return_value = mock_whitelist

            with pytest.raises(InvalidRequestError, match="未知的字段类型"):
                validator.get_allowed_fields("Asset", "invalid_type")


class TestSecurityEdgeCases:
    """Test edge cases and security scenarios"""

    @pytest.fixture
    def validator(self):
        return RequestSecurity()

    def test_sql_injection_pattern_in_email(self, validator):
        """Test that SQL injection patterns are caught in email validation"""
        malicious_emails = [
            "user' OR '1'='1@example.com",
            "user'; DROP TABLE users;--@example.com",
            "user@example.com' OR '1'='1",
        ]

        # Email validation should reject these
        for email in malicious_emails:
            assert validator.validate_email(email) is False

    def test_xss_in_url(self, validator):
        """Test that XSS patterns are blocked in URLs"""
        xss_urls = [
            "https://example.com/<script>alert('XSS')</script>",
            "https://example.com/onclick=alert(1)",
            "javascript:alert(document.cookie)",
        ]

        for url in xss_urls:
            assert validator.is_safe_url(url) is False

    def test_header_injection_in_input(self, validator):
        """Test that header injection is prevented"""
        malicious_inputs = [
            "text\r\nX-Injected-Header: value",
            "text\nSet-Cookie: malicious=true",
            "text\rX-Injected: value",
        ]

        for input_str in malicious_inputs:
            sanitized = validator.sanitize_input(input_str)
            # Control characters should be removed
            assert "\r" not in sanitized
            assert "\n" not in sanitized

    def test_unicode_security(self, validator):
        """Test handling of unicode characters"""
        # Should allow legitimate unicode
        assert (
            validator.validate_email("用户@example.com") is False
        )  # No unicode in local part
        assert (
            validator.validate_email("user@例え.com") is True
        )  # Unicode in domain is OK

        # Should sanitize null bytes in unicode
        result = validator.sanitize_input("文本\x00更多文本")
        assert "\x00" not in result
