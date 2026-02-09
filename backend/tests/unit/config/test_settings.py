"""
Configuration Module Tests

Tests for application configuration loading and validation.
"""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from src.core.config import Settings

STRONG_SECRET = "aB3xK7mN9pQ2rS5tU8vW1xY4zZ6bC8dE0fG2hI4jK6!@#$%^&*"


def build_settings(overrides=None, clear=True):
    env = {
        "SECRET_KEY": STRONG_SECRET,
        "PYDANTIC_SETTINGS_IGNORE_DOT_ENV": "1",
    }
    if overrides:
        env.update(overrides)
    with patch.dict(os.environ, env, clear=clear):
        return Settings()


class TestSettingsDefaults:
    """Test default settings values"""

    def test_database_url_default(self):
        settings = build_settings()
        assert settings.DATABASE_URL == ""

    def test_redis_defaults(self):
        settings = build_settings()
        assert settings.REDIS_ENABLED is False
        assert settings.REDIS_HOST is None
        assert settings.REDIS_PORT == 6379
        assert settings.REDIS_DB == 0

    def test_debug_default(self):
        settings = build_settings()
        assert settings.DEBUG is True

    def test_cors_origins_default(self):
        settings = build_settings()
        assert isinstance(settings.CORS_ORIGINS, list)
        assert "http://localhost:5173" in settings.CORS_ORIGINS

    def test_upload_dir_default(self):
        settings = build_settings()
        assert settings.UPLOAD_DIR == "./uploads"

    def test_max_file_size_default(self):
        settings = build_settings()
        assert settings.MAX_FILE_SIZE == 50 * 1024 * 1024

    def test_log_level_default(self):
        settings = build_settings()
        assert settings.LOG_LEVEL == "INFO"

    def test_pagination_defaults(self):
        settings = build_settings()
        assert settings.DEFAULT_PAGE_SIZE == 20
        assert settings.MAX_PAGE_SIZE == 100


class TestSettingsEnvironmentVariables:
    """Test environment variable loading"""

    def test_database_url_from_env(self):
        settings = build_settings(
            {"DATABASE_URL": "postgresql+psycopg://user:pass@localhost/db"}
        )
        assert "postgresql" in settings.DATABASE_URL

    def test_debug_from_env(self):
        settings = build_settings({"DEBUG": "true"})
        assert settings.DEBUG is True

    def test_custom_page_size_from_env(self):
        settings = build_settings({"DEFAULT_PAGE_SIZE": "50"})
        assert settings.DEFAULT_PAGE_SIZE == 50

    def test_redis_password_required_in_production_when_enabled(self):
        with pytest.raises(ValidationError):
            build_settings(
                {
                    "ENVIRONMENT": "production",
                    "REDIS_ENABLED": "true",
                    "REDIS_HOST": "localhost",
                }
            )

    def test_redis_password_optional_in_development_when_enabled(self):
        settings = build_settings(
            {
                "ENVIRONMENT": "development",
                "REDIS_ENABLED": "true",
                "REDIS_HOST": "localhost",
            }
        )
        assert settings.REDIS_ENABLED is True
        assert settings.REDIS_PASSWORD is None


class TestSecretKeySecurity:
    """Test SECRET_KEY configuration"""

    def test_secret_key_required(self):
        with patch.dict(
            os.environ, {"PYDANTIC_SETTINGS_IGNORE_DOT_ENV": "1"}, clear=True
        ):
            with pytest.raises(ValidationError):
                Settings()

    def test_secret_key_length_validation(self):
        with patch.dict(
            os.environ,
            {
                "SECRET_KEY": "short",
                "PYDANTIC_SETTINGS_IGNORE_DOT_ENV": "1",
            },
            clear=True,
        ):
            with pytest.raises(ValidationError):
                Settings()


class TestDataEncryptionKey:
    """Test DATA_ENCRYPTION_KEY configuration"""

    def test_encryption_key_optional(self):
        settings = build_settings()
        assert settings.DATA_ENCRYPTION_KEY is None or isinstance(
            settings.DATA_ENCRYPTION_KEY, str
        )


class TestConfigurationTypes:
    """Test configuration value types"""

    def test_string_settings(self):
        settings = build_settings()
        assert isinstance(settings.DATABASE_URL, str)
        assert isinstance(settings.LOG_LEVEL, str)

    def test_int_settings(self):
        settings = build_settings()
        assert isinstance(settings.MAX_FILE_SIZE, int)
        assert isinstance(settings.DEFAULT_PAGE_SIZE, int)
        assert isinstance(settings.MAX_PAGE_SIZE, int)
        assert isinstance(settings.ACCESS_TOKEN_EXPIRE_MINUTES, int)
        assert isinstance(settings.REFRESH_TOKEN_EXPIRE_DAYS, int)

    def test_bool_settings(self):
        settings = build_settings()
        assert isinstance(settings.DEBUG, bool)
        assert isinstance(settings.REDIS_ENABLED, bool)

    def test_list_settings(self):
        settings = build_settings()
        assert isinstance(settings.CORS_ORIGINS, list)


class TestConfigurationConstraints:
    """Test configuration constraints and validations"""

    def test_page_size_constraints(self):
        settings = build_settings()
        assert settings.DEFAULT_PAGE_SIZE < settings.MAX_PAGE_SIZE

    def test_password_policy_constraints(self):
        settings = build_settings()
        assert settings.MIN_PASSWORD_LENGTH >= 8
        assert settings.MAX_FAILED_ATTEMPTS >= 3

    def test_session_constraints(self):
        settings = build_settings()
        assert settings.MAX_CONCURRENT_SESSIONS >= 1
        assert settings.SESSION_EXPIRE_DAYS >= 1

    def test_retention_days(self):
        settings = build_settings()
        assert settings.AUDIT_LOG_RETENTION_DAYS >= 30
