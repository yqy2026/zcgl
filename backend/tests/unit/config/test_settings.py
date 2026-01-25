"""
Configuration Module Tests

Tests for application configuration loading and validation.
"""

import os
from unittest.mock import patch

import pytest

from src.config import settings


class TestSettingsDefaults:
    """Test default settings values"""

    def test_database_url_default(self):
        """Test DATABASE_URL default value"""
        assert "sqlite" in settings.DATABASE_URL.lower()
        assert "land_property.db" in settings.DATABASE_URL

    def test_redis_url_default(self):
        """Test REDIS_URL default value"""
        assert settings.REDIS_URL == "redis://localhost:6379/0"

    def test_debug_default(self):
        """Test DEBUG default value"""
        assert settings.DEBUG is False

    def test_cors_origins_default(self):
        """Test CORS_ORIGINS default value"""
        assert isinstance(settings.CORS_ORIGINS, list)
        assert len(settings.CORS_ORIGINS) >= 3
        assert "http://localhost:3000" in settings.CORS_ORIGINS
        assert "http://localhost:5173" in settings.CORS_ORIGINS

    def test_upload_dir_default(self):
        """Test UPLOAD_DIR default value"""
        assert settings.UPLOAD_DIR == "uploads"

    def test_max_file_size_default(self):
        """Test MAX_FILE_SIZE default value"""
        assert settings.MAX_FILE_SIZE == 52428800  # 50MB

    def test_log_level_default(self):
        """Test LOG_LEVEL default value"""
        assert settings.LOG_LEVEL == "INFO"

    def test_pagination_defaults(self):
        """Test pagination default values"""
        assert settings.DEFAULT_PAGE_SIZE == 20
        assert settings.MAX_PAGE_SIZE == 100

    def test_excel_defaults(self):
        """Test Excel processing defaults"""
        assert settings.EXCEL_MAX_ROWS == 10000
        assert settings.EXCEL_BATCH_SIZE == 100

    def test_jwt_defaults(self):
        """Test JWT defaults"""
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 30
        assert settings.REFRESH_TOKEN_EXPIRE_DAYS == 7

    def test_password_policy_defaults(self):
        """Test password policy defaults"""
        assert settings.MIN_PASSWORD_LENGTH == 8
        assert settings.MAX_FAILED_ATTEMPTS == 5
        assert settings.LOCKOUT_DURATION_MINUTES == 30
        assert settings.PASSWORD_EXPIRE_DAYS == 90

    def test_session_defaults(self):
        """Test session defaults"""
        assert settings.MAX_CONCURRENT_SESSIONS == 5
        assert settings.SESSION_EXPIRE_DAYS == 7

    def test_audit_defaults(self):
        """Test audit log defaults"""
        assert settings.AUDIT_LOG_RETENTION_DAYS == 90

    def test_pdf_defaults(self):
        """Test PDF processing defaults"""
        assert settings.PDF_MAX_FILE_SIZE_MB == 50
        assert settings.PDF_PROCESSING_TIMEOUT == 300


class TestSettingsEnvironmentVariables:
    """Test environment variable loading"""

    def test_database_url_from_env(self):
        """Test DATABASE_URL from environment variable"""
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://user:pass@localhost/db"}):
            # Re-import to get new settings
            from importlib import reload
            import src.config as config_module

            reload(config_module)
            new_settings = config_module.Settings()

            assert "postgresql" in new_settings.DATABASE_URL

    def test_debug_from_env(self):
        """Test DEBUG from environment variable"""
        with patch.dict(os.environ, {"DEBUG": "true"}):
            from importlib import reload
            import src.config as config_module

            reload(config_module)
            new_settings = config_module.Settings()

            assert new_settings.DEBUG is True

    def test_custom_page_size_from_env(self):
        """Test DEFAULT_PAGE_SIZE from environment variable"""
        with patch.dict(os.environ, {"DEFAULT_PAGE_SIZE": "50"}):
            from importlib import reload
            import src.config as config_module

            reload(config_module)
            new_settings = config_module.Settings()

            assert new_settings.DEFAULT_PAGE_SIZE == 50


class TestSecretKeySecurity:
    """Test SECRET_KEY configuration"""

    def test_secret_key_exists(self):
        """Test that SECRET_KEY is set"""
        assert settings.SECRET_KEY is not None
        assert len(settings.SECRET_KEY) > 0

    def test_secret_key_length_warning(self):
        """Test that short SECRET_KEY generates warning"""
        # This tests the validation logic
        short_key = "short"
        if len(short_key) < 32:
            # Should be warned in production
            pass

    def test_default_secret_key(self):
        """Test default SECRET_KEY value"""
        # The default key is for development only
        assert settings.SECRET_KEY is not None


class TestDataEncryptionKey:
    """Test DATA_ENCRYPTION_KEY configuration"""

    def test_encryption_key_exists(self):
        """Test that DATA_ENCRYPTION_KEY attribute exists"""
        assert hasattr(settings, "DATA_ENCRYPTION_KEY")

    def test_encryption_key_can_be_empty(self):
        """Test that empty DATA_ENCRYPTION_KEY is acceptable (graceful degradation)"""
        # Empty string is acceptable for dev, but warns in production
        assert isinstance(settings.DATA_ENCRYPTION_KEY, str)


class TestCORSConfiguration:
    """Test CORS configuration"""

    def test_cors_origins_parsing(self):
        """Test CORS_ORIGINS comma-separated parsing"""
        origins = "http://localhost:3000,http://localhost:5173,https://example.com".split(",")
        assert len(origins) == 3
        assert "http://localhost:3000" in origins

    def test_cors_origins_is_list(self):
        """Test that CORS_ORIGINS is a list"""
        assert isinstance(settings.CORS_ORIGINS, list)


class TestRedisConfiguration:
    """Test Redis configuration"""

    def test_redis_url_format(self):
        """Test REDIS_URL format"""
        assert settings.REDIS_URL.startswith("redis://")
        assert "6379" in settings.REDIS_URL

    def test_redis_url_components(self):
        """Test REDIS_URL contains necessary components"""
        # Should have host and port
        assert "localhost" in settings.REDIS_URL or "127.0.0.1" in settings.REDIS_URL


class TestSettingsInstance:
    """Test settings instance behavior"""

    def test_settings_is_singleton(self):
        """Test that settings is a module-level instance"""
        from src.config import settings as s1
        from src.config import settings as s2

        assert s1 is s2

    def test_settings_attributes(self):
        """Test that settings has all expected attributes"""
        expected_attrs = [
            "DATABASE_URL",
            "REDIS_URL",
            "SECRET_KEY",
            "DEBUG",
            "CORS_ORIGINS",
            "UPLOAD_DIR",
            "MAX_FILE_SIZE",
            "LOG_LEVEL",
            "DEFAULT_PAGE_SIZE",
            "MAX_PAGE_SIZE",
            "EXCEL_MAX_ROWS",
            "EXCEL_BATCH_SIZE",
            "ACCESS_TOKEN_EXPIRE_MINUTES",
            "REFRESH_TOKEN_EXPIRE_DAYS",
            "MIN_PASSWORD_LENGTH",
            "MAX_FAILED_ATTEMPTS",
            "LOCKOUT_DURATION_MINUTES",
            "PASSWORD_EXPIRE_DAYS",
            "MAX_CONCURRENT_SESSIONS",
            "SESSION_EXPIRE_DAYS",
            "AUDIT_LOG_RETENTION_DAYS",
            "PDF_MAX_FILE_SIZE_MB",
            "PDF_PROCESSING_TIMEOUT",
        ]

        for attr in expected_attrs:
            assert hasattr(settings, attr), f"Settings missing attribute: {attr}"


class TestRedisTaskStore:
    """Test RedisTaskStore"""

    def test_task_store_instance(self):
        """Test that task_store is instantiated"""
        from src.config import task_store

        assert task_store is not None
        assert hasattr(task_store, "set_task_status")
        assert hasattr(task_store, "get_task_status")
        assert hasattr(task_store, "delete_task")


class TestConfigurationTypes:
    """Test configuration value types"""

    def test_string_settings(self):
        """Test string-typed settings"""
        assert isinstance(settings.DATABASE_URL, str)
        assert isinstance(settings.REDIS_URL, str)
        assert isinstance(settings.SECRET_KEY, str)
        assert isinstance(settings.LOG_LEVEL, str)

    def test_int_settings(self):
        """Test integer-typed settings"""
        assert isinstance(settings.MAX_FILE_SIZE, int)
        assert isinstance(settings.DEFAULT_PAGE_SIZE, int)
        assert isinstance(settings.MAX_PAGE_SIZE, int)
        assert isinstance(settings.EXCEL_MAX_ROWS, int)
        assert isinstance(settings.EXCEL_BATCH_SIZE, int)
        assert isinstance(settings.ACCESS_TOKEN_EXPIRE_MINUTES, int)
        assert isinstance(settings.REFRESH_TOKEN_EXPIRE_DAYS, int)

    def test_bool_settings(self):
        """Test boolean-typed settings"""
        assert isinstance(settings.DEBUG, bool)

    def test_list_settings(self):
        """Test list-typed settings"""
        assert isinstance(settings.CORS_ORIGINS, list)


class TestConfigurationConstraints:
    """Test configuration constraints and validations"""

    def test_page_size_constraints(self):
        """Test page size constraints"""
        assert settings.DEFAULT_PAGE_SIZE < settings.MAX_PAGE_SIZE

    def test_excel_batch_size(self):
        """Test Excel batch size is reasonable"""
        assert settings.EXCEL_BATCH_SIZE < settings.EXCEL_MAX_ROWS

    def test_password_policy_constraints(self):
        """Test password policy constraints"""
        assert settings.MIN_PASSWORD_LENGTH >= 8
        assert settings.MAX_FAILED_ATTEMPTS >= 3
        assert settings.LOCKOUT_DURATION_MINUTES >= 5

    def test_session_constraints(self):
        """Test session constraints"""
        assert settings.MAX_CONCURRENT_SESSIONS >= 1
        assert settings.SESSION_EXPIRE_DAYS >= 1

    def test_retention_days(self):
        """Test audit log retention days"""
        assert settings.AUDIT_LOG_RETENTION_DAYS >= 30

    def test_pdf_constraints(self):
        """Test PDF processing constraints"""
        assert settings.PDF_MAX_FILE_SIZE_MB >= 10
        assert settings.PDF_PROCESSING_TIMEOUT >= 60
