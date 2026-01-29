"""
JWT Security Module Tests

Tests for JWT token generation, validation, and security configuration.
Critical for authentication security.
"""

from datetime import UTC, datetime, timedelta

import pytest
from jose.exceptions import JWTError

from src.security.jwt_security import (
    jwt_security,
    validate_current_jwt_config,
)


class TestJWTSecurityConfig:
    """Test JWT security configuration"""

    def test_validate_secret_key_length_valid(self):
        """Test that valid secret key length passes validation"""
        # Generate a secure key
        secure_key = jwt_security.generate_secure_secret()
        result = jwt_security.validate_secret_key(secure_key)

        assert result["is_valid"] is True
        assert len(result["issues"]) == 0
        assert result["strength_score"] >= 3

    def test_validate_secret_key_too_short(self):
        """Test that short secret keys fail validation"""
        short_key = "short"
        result = jwt_security.validate_secret_key(short_key)

        assert result["is_valid"] is False
        assert any("密钥长度不足" in issue for issue in result["issues"])

    def test_validate_secret_key_default_patterns(self):
        """Test that default/insecure keys are detected"""
        default_keys = [
            "dev-secret-key-change-in-production",
            "your-secret-key-change-in-production",
            "secret-key",
        ]

        for key in default_keys:
            result = jwt_security.validate_secret_key(key)
            assert result["is_valid"] is False
            assert any(
                "默认" in issue or "不安全" in issue for issue in result["issues"]
            )

    def test_validate_secret_key_weak_patterns(self):
        """Test that weak key patterns are detected"""
        weak_keys = [
            "mysecret123",
            "testkey456",
            "devpassword",
        ]

        for key in weak_keys:
            result = jwt_security.validate_secret_key(key)
            assert result["is_valid"] is False
            assert any("弱模式" in issue for issue in result["issues"])

    def test_validate_secret_key_complexity(self):
        """Test key complexity scoring"""
        # High complexity key
        complex_key = "Abc123!@#xyzXYZ"
        result = jwt_security.validate_secret_key(complex_key)

        assert result["strength_score"] >= 4

        # Low complexity key
        simple_key = "a" * 40
        result = jwt_security.validate_secret_key(simple_key)

        assert result["strength_score"] < 4
        assert len(result["suggestions"]) > 0

    def test_generate_secure_secret(self):
        """Test secure secret generation"""
        secret1 = jwt_security.generate_secure_secret()
        secret2 = jwt_security.generate_secure_secret()

        # Each call should generate a unique key
        assert secret1 != secret2

        # Should be URL-safe
        assert len(secret1) >= 32

        # Should validate successfully
        result = jwt_security.validate_secret_key(secret1)
        assert result["is_valid"] is True


class TestTokenCreation:
    """Test JWT token creation"""

    def test_create_access_token(self):
        """Test access token creation"""
        payload = {"user_id": 123, "username": "testuser"}
        token = jwt_security.create_token_with_claims(payload, token_type="access")

        assert isinstance(token, str)
        assert len(token) > 0

        # Verify token structure
        parts = token.split(".")
        assert len(parts) == 3  # header.payload.signature

    def test_create_refresh_token(self):
        """Test refresh token creation"""
        payload = {"user_id": 123}
        token = jwt_security.create_token_with_claims(payload, token_type="refresh")

        assert isinstance(token, str)
        assert len(token) > 0

    def test_token_claims_structure(self):
        """Test that token includes required claims"""
        import jwt

        from src.core.config import settings

        payload = {"user_id": 123, "role": "admin"}
        token = jwt_security.create_token_with_claims(payload, token_type="access")

        # Decode and verify claims
        decoded = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[getattr(settings, "ALGORITHM", "HS256")],
        )

        # Check standard claims
        assert "iat" in decoded
        assert "exp" in decoded
        assert "jti" in decoded
        assert "type" in decoded
        assert decoded["type"] == "access"

        # Check custom claims
        assert decoded["user_id"] == 123
        assert decoded["role"] == "admin"

    def test_access_token_expiry(self):
        """Test access token expiration time"""
        import jwt

        from src.core.config import settings

        payload = {"user_id": 123}
        token = jwt_security.create_token_with_claims(payload, token_type="access")

        decoded = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[getattr(settings, "ALGORITHM", "HS256")],
        )

        exp_datetime = datetime.fromtimestamp(decoded["exp"], UTC)
        iat_datetime = datetime.fromtimestamp(decoded["iat"], UTC)

        # Should be approximately 30 minutes (DEFAULT_ACCESS_TOKEN_LIFETIME)
        diff = exp_datetime - iat_datetime
        assert timedelta(minutes=29) <= diff <= timedelta(minutes=31)

    def test_refresh_token_expiry(self):
        """Test refresh token expiration time"""
        import jwt

        from src.core.config import settings

        payload = {"user_id": 123}
        token = jwt_security.create_token_with_claims(payload, token_type="refresh")

        decoded = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[getattr(settings, "ALGORITHM", "HS256")],
        )

        exp_datetime = datetime.fromtimestamp(decoded["exp"], UTC)
        iat_datetime = datetime.fromtimestamp(decoded["iat"], UTC)

        # Should be approximately 7 days (DEFAULT_REFRESH_TOKEN_LIFETIME)
        diff = exp_datetime - iat_datetime
        assert timedelta(days=6, hours=23) <= diff <= timedelta(days=7, hours=1)


class TestTokenVerification:
    """Test JWT token verification"""

    def test_verify_valid_token(self):
        """Test verification of valid token"""
        payload = {"user_id": 123, "username": "test"}
        token = jwt_security.create_token_with_claims(payload, token_type="access")

        result = jwt_security.verify_token(token)

        assert result["valid"] is True
        assert result["payload"]["user_id"] == 123
        assert result["payload"]["username"] == "test"
        assert result["token_type"] == "access"
        assert "expires_at" in result
        assert "jti" in result

    def test_verify_token_missing_expiration(self):
        """Test that token without expiration fails"""
        import jwt

        from src.core.config import settings

        # Create token without exp claim
        payload = {"user_id": 123}
        token = jwt.encode(
            payload,
            settings.SECRET_KEY,
            algorithm=getattr(settings, "ALGORITHM", "HS256"),
        )

        with pytest.raises(JWTError, match="Token missing expiration time"):
            jwt_security.verify_token(token)

    def test_verify_token_missing_iat(self):
        """Test that token without issued-at time fails"""
        import jwt

        from src.core.config import settings

        # Create token with exp but no iat
        payload = {
            "user_id": 123,
            "exp": (datetime.now(UTC) + timedelta(minutes=30)).timestamp(),
        }
        token = jwt.encode(
            payload,
            settings.SECRET_KEY,
            algorithm=getattr(settings, "ALGORITHM", "HS256"),
        )

        with pytest.raises(JWTError, match="Token missing issued at time"):
            jwt_security.verify_token(token)

    def test_verify_expired_token(self):
        """Test that expired token is rejected"""
        import jwt

        from src.core.config import settings

        # Create expired token
        payload = {
            "user_id": 123,
            "iat": (datetime.now(UTC) - timedelta(hours=2)).timestamp(),
            "exp": (datetime.now(UTC) - timedelta(hours=1)).timestamp(),
            "jti": "test-jti",
            "type": "access",
        }
        token = jwt.encode(
            payload,
            settings.SECRET_KEY,
            algorithm=getattr(settings, "ALGORITHM", "HS256"),
        )

        with pytest.raises(JWTError, match="expired"):
            jwt_security.verify_token(token)

    def test_verify_invalid_signature(self):
        """Test that token with invalid signature fails"""
        # Create token with one key
        token = jwt_security.create_token_with_claims({"user_id": 123})

        # Try to verify with different key
        from src.core.config import settings

        original_key = settings.SECRET_KEY
        settings.SECRET_KEY = "different-secret-key-for-testing"

        try:
            with pytest.raises(JWTError, match="validation failed"):
                jwt_security.verify_token(token)
        finally:
            settings.SECRET_KEY = original_key


class TestTokenSecurityInfo:
    """Test token security information extraction"""

    def test_get_security_info_valid_token(self):
        """Test extracting security info from valid token"""
        payload = {"user_id": 123, "role": "admin"}
        token = jwt_security.create_token_with_claims(payload, token_type="access")

        info = jwt_security.get_token_security_info(token)

        assert info["has_jti"] is True
        assert info["has_exp"] is True
        assert info["has_iat"] is True
        assert info["has_type"] is True
        assert info["token_type"] == "access"
        assert "expires_at" in info
        assert "issued_at" in info
        assert "is_expired" in info
        assert info["is_expired"] is False

    def test_get_security_info_expiry_status(self):
        """Test token expiry detection"""
        import jwt

        from src.core.config import settings

        # Create expired token
        payload = {
            "user_id": 123,
            "iat": (datetime.now(UTC) - timedelta(hours=2)).timestamp(),
            "exp": (datetime.now(UTC) - timedelta(hours=1)).timestamp(),
            "jti": "test-jti",
            "type": "access",
        }
        token = jwt.encode(
            payload,
            settings.SECRET_KEY,
            algorithm=getattr(settings, "ALGORITHM", "HS256"),
        )

        info = jwt_security.get_token_security_info(token)

        assert info["is_expired"] is True
        assert "time_to_expiry" in info

    def test_get_security_info_invalid_token(self):
        """Test security info extraction from invalid token"""
        info = jwt_security.get_token_security_info("invalid.token.here")

        assert "error" in info
        assert info["parse_failed"] is True


class TestConfigurationValidation:
    """Test JWT configuration validation"""

    def test_validate_current_config(self):
        """Test current JWT configuration validation"""
        result = validate_current_jwt_config()

        assert "config_valid" in result
        assert "issues" in result
        assert "recommendations" in result
        assert "secret_key_analysis" in result

        # Secret key analysis should be present
        assert "is_valid" in result["secret_key_analysis"]
        assert "strength_score" in result["secret_key_analysis"]

    def test_recommended_algorithms(self):
        """Test that recommended algorithms list is correct"""
        recommended = jwt_security.RECOMMENDED_ALGORITHMS

        assert "HS256" in recommended
        assert "HS384" in recommended
        assert "HS512" in recommended

    def test_token_lifetime_constants(self):
        """Test token lifetime constants"""
        assert jwt_security.DEFAULT_ACCESS_TOKEN_LIFETIME == timedelta(minutes=30)
        assert jwt_security.DEFAULT_REFRESH_TOKEN_LIFETIME == timedelta(days=7)
        assert jwt_security.MAX_TOKEN_LIFETIME == timedelta(hours=1)

    def test_min_secret_key_length(self):
        """Test minimum secret key length requirement"""
        assert jwt_security.MIN_SECRET_KEY_LENGTH == 32
