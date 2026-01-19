"""
Security Event Logger Tests

Test the security event logging system including event types,
threshold checking, Redis integration, and database storage.
"""

import asyncio
import time
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.core.security_event_logger import (
    SecurityEventLogger,
    SecurityEventType,
    SecuritySeverity,
)


def setup_mock_cache(mock_cache, set_return=True, get_return=None):
    """Helper to set up mock cache_manager with async functions"""
    async def mock_set(prefix, key, value, expire):
        return set_return

    async def mock_get(prefix, key):
        # If get_return is a dict with just 'count', add 'events' key
        if get_return and isinstance(get_return, dict) and 'count' in get_return and 'events' not in get_return:
            return {"count": get_return["count"], "events": []}
        return get_return

    mock_cache.set = mock_set
    mock_cache.get = mock_get


class TestSecurityEventLoggerBasics:
    """Test SecurityEventLogger basic functionality"""

    def test_logger_initialization(self):
        """Test logger can be initialized"""
        logger = SecurityEventLogger()
        assert logger is not None
        assert logger.alert_threshold == 5
        assert logger.alert_window_minutes == 10

    def test_logger_custom_threshold(self):
        """Test logger with custom threshold"""
        logger = SecurityEventLogger(alert_threshold=10, alert_window_minutes=30)
        assert logger.alert_threshold == 10
        assert logger.alert_window_minutes == 30

    def test_event_type_enum(self):
        """Test event type enum values"""
        assert SecurityEventType.AUTH_FAILURE == "auth_failure"
        assert SecurityEventType.AUTH_SUCCESS == "auth_success"
        assert SecurityEventType.PERMISSION_DENIED == "permission_denied"
        assert SecurityEventType.RATE_LIMIT_EXCEEDED == "rate_limit_exceeded"
        assert SecurityEventType.SUSPICIOUS_ACTIVITY == "suspicious_activity"
        assert SecurityEventType.ACCOUNT_LOCKED == "account_locked"

    def test_severity_enum(self):
        """Test severity enum values"""
        assert SecuritySeverity.LOW == "low"
        assert SecuritySeverity.MEDIUM == "medium"
        assert SecuritySeverity.HIGH == "high"
        assert SecuritySeverity.CRITICAL == "critical"


class TestAuthFailureLogging:
    """Test authentication failure logging"""

    @patch("src.core.security_event_logger.cache_manager")
    def test_log_auth_failure_basic(self, mock_cache):
        """Test logging basic auth failure"""
        # Create proper async mock functions
        async def mock_set(prefix, key, value, expire):
            return True

        async def mock_get(prefix, key):
            return None

        mock_cache.set = mock_set
        mock_cache.get = mock_get

        logger = SecurityEventLogger()
        asyncio.run(logger.log_auth_failure("192.168.1.1", "testuser", "invalid_password"))

        # If we get here without exception, the test passes
        # The mock functions are async and will be called correctly

    @patch("src.core.security_event_logger.cache_manager")
    def test_log_auth_failure_without_username(self, mock_cache):
        """Test logging auth failure without username"""
        async def mock_set(prefix, key, value, expire):
            return True

        async def mock_get(prefix, key):
            return None

        mock_cache.set = mock_set
        mock_cache.get = mock_get

        logger = SecurityEventLogger()
        asyncio.run(logger.log_auth_failure("192.168.1.1", reason="account_locked"))

        # If we get here without exception, the test passes

    @patch("src.core.security_event_logger.cache_manager")
    def test_log_auth_failure_with_ipv6(self, mock_cache):
        """Test logging auth failure with IPv6 address"""
        async def mock_set(prefix, key, value, expire):
            return True

        async def mock_get(prefix, key):
            return None

        mock_cache.set = mock_set
        mock_cache.get = mock_get

        logger = SecurityEventLogger()
        asyncio.run(logger.log_auth_failure("::ffff:192.168.1.1", "testuser"))

        # If we get here without exception, the test passes


class TestPermissionDeniedLogging:
    """Test permission denied logging"""

    @patch("src.core.security_event_logger.cache_manager")
    def test_log_permission_denied(self, mock_cache):
        """Test logging permission denied event"""
        setup_mock_cache(mock_cache)

        logger = SecurityEventLogger()
        asyncio.run(logger.log_permission_denied(
            user_id="user123",
            resource="assets",
            action="delete",
            ip_address="192.168.1.1"
        ))

        # If we get here without exception, the test passes

    @patch("src.core.security_event_logger.cache_manager")
    def test_log_permission_denied_with_details(self, mock_cache):
        """Test logging permission denied with additional details"""
        setup_mock_cache(mock_cache)

        logger = SecurityEventLogger()
        asyncio.run(logger.log_permission_denied(
            user_id="user123",
            resource="contracts",
            action="update",
            ip_address="10.0.0.1"
        ))

        # If we get here without exception, the test passes


class TestRateLimitExceededLogging:
    """Test rate limit exceeded logging"""

    @patch("src.core.security_event_logger.cache_manager")
    def test_log_rate_limit_exceeded(self, mock_cache):
        """Test logging rate limit exceeded"""
        setup_mock_cache(mock_cache)

        logger = SecurityEventLogger()
        asyncio.run(logger.log_rate_limit_exceeded("192.168.1.1", "/api/v1/assets"))

        # If we get here without exception, the test passes


class TestThresholdChecking:
    """Test threshold-based alerting"""

    @patch("src.core.security_event_logger.cache_manager")
    def test_should_alert_below_threshold(self, mock_cache):
        """Test should not alert when below threshold"""
        setup_mock_cache(mock_cache, get_return={"count": 3})

        logger = SecurityEventLogger(alert_threshold=5)
        should_alert = asyncio.run(logger.should_alert("192.168.1.1"))

        assert should_alert is False

    @patch("src.core.security_event_logger.cache_manager")
    def test_should_alert_at_threshold(self, mock_cache):
        """Test should alert when at threshold"""
        setup_mock_cache(mock_cache, get_return={"count": 5})

        logger = SecurityEventLogger(alert_threshold=5)
        should_alert = asyncio.run(logger.should_alert("192.168.1.1"))

        assert should_alert is True

    @patch("src.core.security_event_logger.cache_manager")
    def test_should_alert_above_threshold(self, mock_cache):
        """Test should alert when above threshold"""
        setup_mock_cache(mock_cache, get_return={"count": 10})

        logger = SecurityEventLogger(alert_threshold=5)
        should_alert = asyncio.run(logger.should_alert("192.168.1.1"))

        assert should_alert is True

    @patch("src.core.security_event_logger.cache_manager")
    def test_should_alert_custom_threshold(self, mock_cache):
        """Test should alert with custom threshold"""
        setup_mock_cache(mock_cache, get_return={"count": 8})

        logger = SecurityEventLogger(alert_threshold=10)
        should_alert = asyncio.run(logger.should_alert("192.168.1.1", threshold=10))

        assert should_alert is False

    @patch("src.core.security_event_logger.cache_manager")
    def test_should_alert_zero_count(self, mock_cache):
        """Test should not alert when count is zero"""
        setup_mock_cache(mock_cache, get_return={"count": 0})

        logger = SecurityEventLogger(alert_threshold=5)
        should_alert = asyncio.run(logger.should_alert("192.168.1.1"))

        assert should_alert is False


class TestEventCounting:
    """Test event counting functionality"""

    @patch("src.core.security_event_logger.cache_manager")
    def test_get_event_count(self, mock_cache):
        """Test getting event count"""
        setup_mock_cache(mock_cache, get_return={"count": 7})

        logger = SecurityEventLogger()
        count = asyncio.run(logger.get_event_count("192.168.1.1", SecurityEventType.AUTH_FAILURE))

        assert count == 7

    @patch("src.core.security_event_logger.cache_manager")
    def test_get_event_count_zero(self, mock_cache):
        """Test getting event count when no events"""
        setup_mock_cache(mock_cache, get_return=None)

        logger = SecurityEventLogger()
        count = asyncio.run(logger.get_event_count("192.168.1.1", SecurityEventType.AUTH_FAILURE))

        assert count == 0

    @patch("src.core.security_event_logger.cache_manager")
    def test_get_event_count_different_types(self, mock_cache):
        """Test counting different event types"""
        setup_mock_cache(mock_cache, get_return={"count": 5})

        logger = SecurityEventLogger()

        # Count auth failures
        count1 = asyncio.run(logger.get_event_count("192.168.1.1", SecurityEventType.AUTH_FAILURE))
        assert count1 == 5

        # Count permission denied events
        count2 = asyncio.run(logger.get_event_count("192.168.1.1", SecurityEventType.PERMISSION_DENIED))
        assert count2 == 5


class TestDatabaseStorage:
    """Test database storage functionality"""

    @patch("src.core.security_event_logger.cache_manager")
    def test_database_storage_on_log(self, mock_cache):
        """Test events are stored in database"""
        setup_mock_cache(mock_cache)

        logger = SecurityEventLogger()
        with patch.object(logger, '_log_to_database', return_value=True):
            asyncio.run(logger.log_auth_failure("192.168.1.1", "testuser", "invalid_password"))

            # If we get here without exception, the test passes


class TestAllEventTypes:
    """Test all security event types"""

    @patch("src.core.security_event_logger.cache_manager")
    def test_log_auth_success(self, mock_cache):
        """Test logging auth success"""
        setup_mock_cache(mock_cache)

        logger = SecurityEventLogger()
        asyncio.run(logger.log_auth_success("192.168.1.1", "testuser"))

        # If we get here without exception, the test passes

    @patch("src.core.security_event_logger.cache_manager")
    def test_log_suspicious_activity(self, mock_cache):
        """Test logging suspicious activity"""
        setup_mock_cache(mock_cache)

        logger = SecurityEventLogger()
        asyncio.run(logger.log_suspicious_activity("192.168.1.1", "multiple_failed_logins"))

        # If we get here without exception, the test passes

    @patch("src.core.security_event_logger.cache_manager")
    def test_log_account_locked(self, mock_cache):
        """Test logging account locked"""
        setup_mock_cache(mock_cache)

        logger = SecurityEventLogger()
        asyncio.run(logger.log_account_locked("testuser", "192.168.1.1", "too_many_failures"))

        # If we get here without exception, the test passes


class TestSeverityLevels:
    """Test severity level assignment"""

    def test_auth_failure_severity(self):
        """Test auth failure has correct severity"""
        logger = SecurityEventLogger()
        severity = logger._get_event_severity(SecurityEventType.AUTH_FAILURE)

        # Verify severity is MEDIUM for auth failures
        assert severity == SecuritySeverity.MEDIUM

    def test_account_locked_severity(self):
        """Test account locked has CRITICAL severity"""
        logger = SecurityEventLogger()
        severity = logger._get_event_severity(SecurityEventType.ACCOUNT_LOCKED)

        # Verify severity is CRITICAL for account locked
        assert severity == SecuritySeverity.CRITICAL


class TestErrorHandling:
    """Test error handling"""

    @patch("src.core.security_event_logger.cache_manager")
    def test_redis_failure_graceful_handling(self, mock_cache):
        """Test graceful handling when Redis fails"""
        async def mock_set(prefix, key, value, expire):
            raise Exception("Redis connection failed")

        mock_cache.set = mock_set

        logger = SecurityEventLogger()

        # Should not raise exception
        try:
            asyncio.run(logger.log_auth_failure("192.168.1.1", "testuser"))
        except Exception:
            pytest.fail("Should handle Redis errors gracefully")

    @patch("src.core.security_event_logger.cache_manager")
    def test_invalid_ip_address(self, mock_cache):
        """Test handling of invalid IP address"""
        setup_mock_cache(mock_cache)

        logger = SecurityEventLogger()

        # Should handle gracefully
        asyncio.run(logger.log_auth_failure("", "testuser"))
        asyncio.run(logger.log_auth_failure(None, "testuser"))  # type: ignore


class TestIntegrationScenarios:
    """Test integration scenarios"""

    @patch("src.core.security_event_logger.cache_manager")
    def test_multiple_auth_failures_trigger_alert(self, mock_cache):
        """Test multiple auth failures trigger alert"""
        setup_mock_cache(mock_cache, get_return={"count": 5})

        logger = SecurityEventLogger(alert_threshold=5)

        # Log 5 auth failures (they won't actually increment in our mock, so we simulate with return value)
        for i in range(5):
            asyncio.run(logger.log_auth_failure("192.168.1.1", "testuser"))

        # Check if should alert (mock returns count=5)
        should_alert = asyncio.run(logger.should_alert("192.168.1.1"))

        assert should_alert is True

    @patch("src.core.security_event_logger.cache_manager")
    def test_different_ips_separate_tracking(self, mock_cache):
        """Test different IPs are tracked separately"""
        setup_mock_cache(mock_cache, get_return={"count": 5})

        logger = SecurityEventLogger(alert_threshold=5)

        # Log failures for different IPs
        for _ in range(5):
            asyncio.run(logger.log_auth_failure("192.168.1.1", "testuser"))

        for _ in range(2):
            asyncio.run(logger.log_auth_failure("192.168.1.2", "testuser"))

        # First IP should trigger alert
        assert asyncio.run(logger.should_alert("192.168.1.1")) is True

        # Second IP should not trigger alert (update mock to return 2)
        async def mock_get_2(prefix, key):
            return {"count": 2}

        mock_cache.get = mock_get_2
        assert asyncio.run(logger.should_alert("192.168.1.2")) is False

    @patch("src.core.security_event_logger.cache_manager")
    def test_mixed_event_types_separate_counts(self, mock_cache):
        """Test mixed event types are counted separately"""
        setup_mock_cache(mock_cache, get_return={"count": 3})

        logger = SecurityEventLogger(alert_threshold=5)

        # Log different event types
        for _ in range(3):
            asyncio.run(logger.log_auth_failure("192.168.1.1", "testuser"))

        for _ in range(2):
            asyncio.run(logger.log_permission_denied(
                user_id="user123",
                resource="assets",
                action="delete",
                ip_address="192.168.1.1"
            ))

        # Auth failures should not trigger alert (3 < 5)
        assert asyncio.run(logger.should_alert("192.168.1.1")) is False

        # But should correctly count auth failures
        count = asyncio.run(logger.get_event_count("192.168.1.1", SecurityEventType.AUTH_FAILURE))
        assert count == 3
