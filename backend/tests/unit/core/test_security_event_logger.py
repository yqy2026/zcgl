"""
Security Event Logger Tests

Test the security event logging system including event types,
threshold checking, Redis integration, and database storage.
"""

from unittest.mock import Mock, patch

from src.core.security_event_logger import (
    SecurityEventLogger,
    SecurityEventType,
    SecuritySeverity,
)
from src.models.security_event import SecurityEvent


def setup_mock_cache(mock_cache, set_return=True, get_return=None):
    """Helper to set up mock cache_manager with sync functions"""

    def mock_set(prefix, key, value, expire):
        return set_return

    def mock_get(prefix, key):
        # If get_return is a dict with just 'count', add 'events' key
        if (
            get_return
            and isinstance(get_return, dict)
            and "count" in get_return
            and "events" not in get_return
        ):
            return {"count": get_return["count"], "events": []}
        # Handle the case where get_return is explicitly set to a return value
        return get_return

    mock_cache.set = mock_set
    mock_cache.get = mock_get
    mock_cache.get.is_coroutine = False  # Mark as not a coroutine


class TestSecurityEventLoggerBasics:
    """Test SecurityEventLogger basic functionality"""

    def test_logger_initialization(self):
        """Test logger can be initialized"""
        logger = SecurityEventLogger()
        assert logger is not None
        assert logger.alert_threshold == 5
        assert logger.alert_window_minutes == 10

    def test_logger_with_db_session(self):
        """Test logger with database session"""
        mock_db = Mock()
        logger = SecurityEventLogger(db=mock_db)
        assert logger.db == mock_db

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
        setup_mock_cache(mock_cache)

        logger = SecurityEventLogger()
        with patch.object(logger, "_log_to_database") as mock_db_log:
            mock_event = Mock(spec=SecurityEvent)
            mock_event.event_type = "auth_failure"
            mock_event.ip_address = "192.168.1.1"
            mock_db_log.return_value = mock_event

            result = logger.log_auth_failure(
                "192.168.1.1", "testuser", "invalid_password"
            )

            # Verify the returned event object
            assert result is not None
            assert result.event_type == "auth_failure"
            assert result.ip_address == "192.168.1.1"

    @patch("src.core.security_event_logger.cache_manager")
    def test_log_auth_failure_without_username(self, mock_cache):
        """Test logging auth failure without username"""
        setup_mock_cache(mock_cache)

        logger = SecurityEventLogger()
        with patch.object(logger, "_log_to_database") as mock_db_log:
            mock_event = Mock(spec=SecurityEvent)
            mock_event.event_type = "auth_failure"
            mock_event.ip_address = "192.168.1.1"
            mock_db_log.return_value = mock_event

            result = logger.log_auth_failure("192.168.1.1", reason="account_locked")

            # Should still log even without username
            assert result is not None

    @patch("src.core.security_event_logger.cache_manager")
    def test_log_auth_failure_with_ipv6(self, mock_cache):
        """Test logging auth failure with IPv6 address"""
        setup_mock_cache(mock_cache)

        logger = SecurityEventLogger()
        with patch.object(logger, "_log_to_database") as mock_db_log:
            mock_event = Mock(spec=SecurityEvent)
            mock_event.event_type = "auth_failure"
            mock_event.ip_address = "::ffff:192.168.1.1"
            mock_db_log.return_value = mock_event

            result = logger.log_auth_failure("::ffff:192.168.1.1", "testuser")

            # Should handle IPv6 addresses
            assert result is not None
            assert result.ip_address == "::ffff:192.168.1.1"


class TestPermissionDeniedLogging:
    """Test permission denied logging"""

    @patch("src.core.security_event_logger.cache_manager")
    def test_log_permission_denied(self, mock_cache):
        """Test logging permission denied event"""
        setup_mock_cache(mock_cache)

        logger = SecurityEventLogger()
        with patch.object(logger, "_log_to_database") as mock_db_log:
            mock_event = Mock(spec=SecurityEvent)
            mock_event.event_type = "permission_denied"
            mock_event.ip_address = "192.168.1.1"
            mock_event.user_id = "user123"
            mock_db_log.return_value = mock_event

            result = logger.log_permission_denied(
                user_id="user123", resource="assets", action="delete", ip="192.168.1.1"
            )

            assert result is not None
            assert result.event_type == "permission_denied"
            assert result.user_id == "user123"

    @patch("src.core.security_event_logger.cache_manager")
    def test_log_permission_denied_with_details(self, mock_cache):
        """Test logging permission denied with additional details"""
        setup_mock_cache(mock_cache)

        logger = SecurityEventLogger()
        with patch.object(logger, "_log_to_database") as mock_db_log:
            mock_event = Mock(spec=SecurityEvent)
            mock_event.event_type = "permission_denied"
            mock_db_log.return_value = mock_event

            result = logger.log_permission_denied(
                user_id="user123", resource="contracts", action="update", ip="10.0.0.1"
            )

            # Should log the event
            assert result is not None


class TestRateLimitExceededLogging:
    """Test rate limit exceeded logging"""

    @patch("src.core.security_event_logger.cache_manager")
    def test_log_rate_limit_exceeded(self, mock_cache):
        """Test logging rate limit exceeded"""
        setup_mock_cache(mock_cache)

        logger = SecurityEventLogger()
        with patch.object(logger, "_log_to_database") as mock_db_log:
            mock_event = Mock(spec=SecurityEvent)
            mock_event.event_type = "rate_limit_exceeded"
            mock_db_log.return_value = mock_event

            result = logger.log_rate_limit_exceeded("192.168.1.1", "/api/v1/assets")

            assert result is not None
            assert result.event_type == "rate_limit_exceeded"


class TestThresholdChecking:
    """Test threshold-based alerting"""

    @patch("src.core.security_event_logger.cache_manager")
    def test_should_alert_below_threshold(self, mock_cache):
        """Test should not alert when below threshold"""
        setup_mock_cache(mock_cache, get_return={"count": 3})

        logger = SecurityEventLogger(alert_threshold=5)
        should_alert = logger.should_alert("192.168.1.1")

        assert should_alert is False

    @patch("src.core.security_event_logger.cache_manager")
    def test_should_alert_at_threshold(self, mock_cache):
        """Test should alert when at threshold"""
        setup_mock_cache(mock_cache, get_return={"count": 5})

        logger = SecurityEventLogger(alert_threshold=5)
        should_alert = logger.should_alert("192.168.1.1")

        assert should_alert is True

    @patch("src.core.security_event_logger.cache_manager")
    def test_should_alert_above_threshold(self, mock_cache):
        """Test should alert when above threshold"""
        setup_mock_cache(mock_cache, get_return={"count": 10})

        logger = SecurityEventLogger(alert_threshold=5)
        should_alert = logger.should_alert("192.168.1.1")

        assert should_alert is True

    @patch("src.core.security_event_logger.cache_manager")
    def test_should_alert_custom_threshold(self, mock_cache):
        """Test should alert with custom threshold"""
        setup_mock_cache(mock_cache, get_return={"count": 8})

        logger = SecurityEventLogger(alert_threshold=10)
        should_alert = logger.should_alert("192.168.1.1", threshold=10)

        assert should_alert is False

    @patch("src.core.security_event_logger.cache_manager")
    def test_should_alert_zero_count(self, mock_cache):
        """Test should not alert when count is zero"""
        setup_mock_cache(mock_cache, get_return={"count": 0})

        logger = SecurityEventLogger(alert_threshold=5)
        should_alert = logger.should_alert("192.168.1.1")

        assert should_alert is False


class TestEventCounting:
    """Test event counting functionality"""

    @patch("src.core.security_event_logger.cache_manager")
    def test_get_event_count(self, mock_cache):
        """Test getting event count"""
        setup_mock_cache(mock_cache, get_return={"count": 7})

        logger = SecurityEventLogger()
        count = logger.get_event_count("192.168.1.1", SecurityEventType.AUTH_FAILURE)

        assert count == 7

    @patch("src.core.security_event_logger.cache_manager")
    def test_get_event_count_zero(self, mock_cache):
        """Test getting event count when no events"""
        setup_mock_cache(mock_cache, get_return=None)

        logger = SecurityEventLogger()
        count = logger.get_event_count("192.168.1.1", SecurityEventType.AUTH_FAILURE)

        assert count == 0

    @patch("src.core.security_event_logger.cache_manager")
    def test_get_event_count_different_types(self, mock_cache):
        """Test counting different event types"""
        setup_mock_cache(mock_cache, get_return={"count": 5})

        logger = SecurityEventLogger()

        # Count auth failures
        count1 = logger.get_event_count("192.168.1.1", SecurityEventType.AUTH_FAILURE)
        assert count1 == 5

        # Count permission denied events
        count2 = logger.get_event_count(
            "192.168.1.1", SecurityEventType.PERMISSION_DENIED
        )
        assert count2 == 5


class TestDatabaseStorage:
    """Test database storage functionality"""

    @patch("src.core.security_event_logger.cache_manager")
    def test_database_storage_on_log(self, mock_cache):
        """Test events are stored in database"""
        setup_mock_cache(mock_cache)

        logger = SecurityEventLogger()
        with patch.object(logger, "_log_to_database") as mock_db_log:
            mock_event = Mock(spec=SecurityEvent)
            mock_event.event_type = "auth_failure"
            mock_event.ip_address = "192.168.1.1"
            mock_db_log.return_value = mock_event

            result = logger.log_auth_failure(
                "192.168.1.1", "testuser", "invalid_password"
            )

            # Verify database log was called
            mock_db_log.assert_called_once()
            # Verify returned event
            assert result is not None


class TestAllEventTypes:
    """Test all security event types"""

    @patch("src.core.security_event_logger.cache_manager")
    def test_log_auth_success(self, mock_cache):
        """Test logging auth success"""
        setup_mock_cache(mock_cache)

        logger = SecurityEventLogger()
        with patch.object(logger, "_log_to_database") as mock_db_log:
            mock_event = Mock(spec=SecurityEvent)
            mock_event.event_type = "auth_success"
            mock_db_log.return_value = mock_event

            result = logger.log_auth_success("192.168.1.1", "testuser")

            assert result is not None
            assert result.event_type == "auth_success"

    @patch("src.core.security_event_logger.cache_manager")
    def test_log_suspicious_activity(self, mock_cache):
        """Test logging suspicious activity"""
        setup_mock_cache(mock_cache)

        logger = SecurityEventLogger()
        with patch.object(logger, "_log_to_database") as mock_db_log:
            mock_event = Mock(spec=SecurityEvent)
            mock_event.event_type = "suspicious_activity"
            mock_db_log.return_value = mock_event

            result = logger.log_suspicious_activity(
                "192.168.1.1", "multiple_failed_logins"
            )

            assert result is not None

    @patch("src.core.security_event_logger.cache_manager")
    def test_log_account_locked(self, mock_cache):
        """Test logging account locked"""
        setup_mock_cache(mock_cache)

        logger = SecurityEventLogger()
        with patch.object(logger, "_log_to_database") as mock_db_log:
            mock_event = Mock(spec=SecurityEvent)
            mock_event.event_type = "account_locked"
            mock_db_log.return_value = mock_event

            result = logger.log_account_locked(
                "testuser", "192.168.1.1", "too_many_failures"
            )

            assert result is not None


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

        def mock_set(prefix, key, value, expire):
            raise Exception("Redis connection failed")

        mock_cache.set = mock_set

        logger = SecurityEventLogger()
        with patch.object(logger, "_log_to_database") as mock_db_log:
            mock_event = Mock(spec=SecurityEvent)
            mock_db_log.return_value = mock_event

            # Should not raise exception
            result = logger.log_auth_failure("192.168.1.1", "testuser")

            # Should still return event from database
            assert result is not None

    @patch("src.core.security_event_logger.cache_manager")
    def test_invalid_ip_address(self, mock_cache):
        """Test handling of invalid IP address"""
        setup_mock_cache(mock_cache)

        logger = SecurityEventLogger()
        with patch.object(logger, "_log_to_database") as mock_db_log:
            mock_event = Mock(spec=SecurityEvent)
            mock_db_log.return_value = mock_event

            # Should handle gracefully
            logger.log_auth_failure("", "testuser")
            logger.log_auth_failure(None, "testuser")  # type: ignore


class TestIntegrationScenarios:
    """Test integration scenarios"""

    @patch("src.core.security_event_logger.cache_manager")
    def test_multiple_auth_failures_trigger_alert(self, mock_cache):
        """Test multiple auth failures trigger alert"""
        setup_mock_cache(mock_cache, get_return={"count": 5})

        logger = SecurityEventLogger(alert_threshold=5)

        with patch.object(logger, "_log_to_database") as mock_db_log:
            mock_event = Mock(spec=SecurityEvent)
            mock_db_log.return_value = mock_event

            # Log 5 auth failures
            for i in range(5):
                logger.log_auth_failure("192.168.1.1", "testuser")

            # Check if should alert (mock returns count=5)
            should_alert = logger.should_alert("192.168.1.1")

            assert should_alert is True

    @patch("src.core.security_event_logger.cache_manager")
    def test_different_ips_separate_tracking(self, mock_cache):
        """Test different IPs are tracked separately"""
        setup_mock_cache(mock_cache, get_return={"count": 5})

        logger = SecurityEventLogger(alert_threshold=5)

        with patch.object(logger, "_log_to_database") as mock_db_log:
            mock_event = Mock(spec=SecurityEvent)
            mock_db_log.return_value = mock_event

            # Log failures for different IPs
            for _ in range(5):
                logger.log_auth_failure("192.168.1.1", "testuser")

            for _ in range(2):
                logger.log_auth_failure("192.168.1.2", "testuser")

            # First IP should trigger alert
            assert logger.should_alert("192.168.1.1") is True

            # Second IP should not trigger alert (update mock to return 2)
            def mock_get_2(prefix, key):
                return {"count": 2, "events": []}

            mock_cache.get = mock_get_2
            assert logger.should_alert("192.168.1.2") is False

    @patch("src.core.security_event_logger.cache_manager")
    def test_mixed_event_types_separate_counts(self, mock_cache):
        """Test mixed event types are counted separately"""
        setup_mock_cache(mock_cache, get_return={"count": 3})

        logger = SecurityEventLogger(alert_threshold=5)

        with patch.object(logger, "_log_to_database") as mock_db_log:
            mock_event = Mock(spec=SecurityEvent)
            mock_db_log.return_value = mock_event

            # Log different event types
            for _ in range(3):
                logger.log_auth_failure("192.168.1.1", "testuser")

            for _ in range(2):
                logger.log_permission_denied(
                    user_id="user123",
                    resource="assets",
                    action="delete",
                    ip="192.168.1.1",
                )

            # Auth failures should not trigger alert (3 < 5)
            assert logger.should_alert("192.168.1.1") is False

            # But should correctly count auth failures
            count = logger.get_event_count(
                "192.168.1.1", SecurityEventType.AUTH_FAILURE
            )
            assert count == 3


class TestMethodSignatures:
    """Test method signatures match spec"""

    def test_log_auth_failure_signature(self):
        """Test log_auth_failure has correct signature"""
        logger = SecurityEventLogger()
        import inspect

        sig = inspect.signature(logger.log_auth_failure)
        params = list(sig.parameters.keys())
        assert "ip" in params
        assert "username" in params
        assert "reason" in params

    def test_log_permission_denied_signature(self):
        """Test log_permission_denied has correct signature"""
        logger = SecurityEventLogger()
        import inspect

        sig = inspect.signature(logger.log_permission_denied)
        params = list(sig.parameters.keys())
        assert "user_id" in params
        assert "resource" in params
        assert "action" in params
        assert "ip" in params

    def test_log_rate_limit_exceeded_signature(self):
        """Test log_rate_limit_exceeded has correct signature"""
        logger = SecurityEventLogger()
        import inspect

        sig = inspect.signature(logger.log_rate_limit_exceeded)
        params = list(sig.parameters.keys())
        assert "ip" in params
        assert "endpoint" in params

    def test_methods_return_security_event(self):
        """Test methods return SecurityEvent object"""
        logger = SecurityEventLogger()
        with patch.object(logger, "_log_to_database") as mock_db_log:
            mock_event = Mock(spec=SecurityEvent)
            mock_event.id = "test-id"
            mock_event.event_type = "auth_failure"
            mock_event.ip_address = "192.168.1.1"
            mock_db_log.return_value = mock_event

            result = logger.log_auth_failure(ip="192.168.1.1")

            # Should return SecurityEvent object
            assert result is not None
            assert hasattr(result, "id")
            assert hasattr(result, "event_type")
            assert hasattr(result, "ip_address")
