"""
Unit tests for SecretValidator

Tests secret validation logic including:
- Minimum length requirements
- Weak pattern detection
- Example value detection
- Character variety requirements
- Environment secret validation
"""

import pytest

from src.core.secret_validator import (
    SecretValidationError,
    SecretValidator,
    secret_validator,
)


class TestSecretValidator:
    """Test SecretValidator functionality"""

    def test_strong_secret_passes(self):
        """A strong, properly formatted secret should pass validation"""
        strong_secret = "Str0ng!S3cr3t@With#Variat$y2026MoreChars!"
        validator = SecretValidator()
        assert validator.validate(strong_secret) is True

    def test_short_secret_fails(self):
        """Secret shorter than 32 characters should fail"""
        short_secret = "Short123!"
        validator = SecretValidator()
        with pytest.raises(SecretValidationError) as exc_info:
            validator.validate(short_secret)
        assert "too short" in str(exc_info.value).lower()

    def test_weak_pattern_secret_fails(self):
        """Secrets containing weak patterns should fail"""
        validator = SecretValidator()

        weak_secrets = [
            "MySecretKeyIsLongEnoughButHasWeakPattern123456789012!",
            "PleaseChangemeThisIsLongEnoughButHasWeakPattern12345!",
            "ThisPasswordIsLongEnoughButContainsPassword123456789!",
            "AdminKeyIsLongEnoughButContainsAdminPattern123456789!",
        ]

        for secret in weak_secrets:
            with pytest.raises(SecretValidationError) as exc_info:
                validator.validate(secret)
            assert "weak pattern" in str(exc_info.value).lower()

    def test_example_value_fails(self):
        """Secrets that are example values should fail"""
        validator = SecretValidator()

        example_secrets = [
            "your-secret-key-here-this-is-long-enough-1234567890!",
            "change-in-production-with-more-text-here-1234567890!",
            "replace-with-real-secret-this-is-long-1234567890!",
            "example-secret-key-with-enough-length-123456789!",
        ]

        for secret in example_secrets:
            with pytest.raises(SecretValidationError) as exc_info:
                validator.validate(secret)
            assert "example" in str(exc_info.value).lower()

    def test_no_uppercase_fails(self):
        """Secret without uppercase should fail"""
        no_upper = "lowercase123!@#defghijklmnopqrstuvwxyz12345"
        validator = SecretValidator()
        with pytest.raises(SecretValidationError) as exc_info:
            validator.validate(no_upper)
        assert "character variety" in str(exc_info.value).lower()

    def test_no_lowercase_fails(self):
        """Secret without lowercase should fail"""
        no_lower = "UPPERCASE123!@#ABCDEFGHIJKLMNOPQRSTUVWXYZ123"
        validator = SecretValidator()
        with pytest.raises(SecretValidationError) as exc_info:
            validator.validate(no_lower)
        assert "character variety" in str(exc_info.value).lower()

    def test_no_digits_fails(self):
        """Secret without digits should fail"""
        no_digits = "NoDigitsHere!@#$%^&*()_+-=[]{}|;:,.<>?ABCDEFG"
        validator = SecretValidator()
        with pytest.raises(SecretValidationError) as exc_info:
            validator.validate(no_digits)
        assert "character variety" in str(exc_info.value).lower()

    def test_no_special_chars_fails(self):
        """Secret without special characters should fail"""
        no_special = "NoSpecialChars123ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef"
        validator = SecretValidator()
        with pytest.raises(SecretValidationError) as exc_info:
            validator.validate(no_special)
        assert "character variety" in str(exc_info.value).lower()

    def test_multiple_errors_reported(self):
        """All validation errors should be reported together"""
        # Short + weak pattern + no special chars
        bad_secret = "secret123"
        validator = SecretValidator()
        with pytest.raises(SecretValidationError) as exc_info:
            validator.validate(bad_secret)
        error_message = exc_info.value.message.lower()
        assert "too short" in error_message
        assert "weak pattern" in error_message

    def test_suggestion_includes_generated_secret(self):
        """Error should include a suggested strong secret"""
        weak_secret = "weak123"
        validator = SecretValidator()
        with pytest.raises(SecretValidationError) as exc_info:
            validator.validate(weak_secret)
        assert exc_info.value.suggestion is not None
        assert len(exc_info.value.suggestion) > 32

    def test_validate_env_secrets_with_valid_secrets(self):
        """validate_env_secrets should return True with valid secrets"""
        import os

        # Set valid secrets temporarily
        original_secret_key = os.environ.get("SECRET_KEY")
        original_enc_key = os.environ.get("DATA_ENCRYPTION_KEY")

        try:
            os.environ["SECRET_KEY"] = "Valid!S3cr3t@Key#With$All%Types^2026ABC"
            os.environ["DATA_ENCRYPTION_KEY"] = "Another!Valid#Key$For%Data^Encryption&2026"

            validator = SecretValidator()
            assert validator.validate_env_secrets() is True

        finally:
            # Restore original values
            if original_secret_key:
                os.environ["SECRET_KEY"] = original_secret_key
            elif "SECRET_KEY" in os.environ:
                del os.environ["SECRET_KEY"]

            if original_enc_key:
                os.environ["DATA_ENCRYPTION_KEY"] = original_enc_key
            elif "DATA_ENCRYPTION_KEY" in os.environ:
                del os.environ["DATA_ENCRYPTION_KEY"]

    def test_validate_env_secrets_with_missing_secret(self, capsys):
        """validate_env_secrets should fail when SECRET_KEY is missing"""
        import os

        original_secret_key = os.environ.get("SECRET_KEY")
        original_enc_key = os.environ.get("DATA_ENCRYPTION_KEY")

        try:
            del os.environ["SECRET_KEY"]
            os.environ["DATA_ENCRYPTION_KEY"] = "Valid!Data#Encryption$Key%2026ABCDEF"

            validator = SecretValidator()
            result = validator.validate_env_secrets()

            captured = capsys.readouterr()
            assert result is False
            assert "SECRET_KEY is not set" in captured.out

        finally:
            if original_secret_key:
                os.environ["SECRET_KEY"] = original_secret_key
            if original_enc_key:
                os.environ["DATA_ENCRYPTION_KEY"] = original_enc_key

    def test_validate_env_secrets_with_weak_secret(self, capsys):
        """validate_env_secrets should fail with weak secrets"""
        import os

        original_secret_key = os.environ.get("SECRET_KEY")
        original_enc_key = os.environ.get("DATA_ENCRYPTION_KEY")

        try:
            os.environ["SECRET_KEY"] = "weak123"
            os.environ["DATA_ENCRYPTION_KEY"] = "Valid!Data#Encryption$Key%2026ABCDEF"

            validator = SecretValidator()
            result = validator.validate_env_secrets()

            captured = capsys.readouterr()
            assert result is False
            assert "SECRET_KEY validation failed" in captured.out

        finally:
            if original_secret_key:
                os.environ["SECRET_KEY"] = original_secret_key
            if original_enc_key:
                os.environ["DATA_ENCRYPTION_KEY"] = original_enc_key

    def test_singleton_instance(self):
        """secret_validator should be a singleton instance"""
        assert isinstance(secret_validator, SecretValidator)
