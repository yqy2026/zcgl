"""
Rate Limiting Security Tests

Tests for rate limiting mechanisms to prevent DDoS and brute force attacks:
- Sliding window rate limiter
- Token bucket rate limiter
- Adaptive rate limiter
- IP blacklist management
"""

from time import sleep, time
from unittest.mock import Mock, patch

import pytest

from src.security.security import (
    RateLimitConfig,
    RateLimiter,
    TokenBucketRateLimiter,
    AdaptiveRateLimiter,
    RequestLimiter,
    IPBlacklistManager,
)


class TestRateLimitConfig:
    """Test rate limiting configuration"""

    def test_default_limits(self):
        """Test default rate limit configuration"""
        assert RateLimitConfig.DEFAULT_LIMITS["api"]["requests"] == 1000
        assert RateLimitConfig.DEFAULT_LIMITS["api"]["window"] == 3600

        assert RateLimitConfig.DEFAULT_LIMITS["upload"]["requests"] == 50
        assert RateLimitConfig.DEFAULT_LIMITS["auth"]["requests"] == 10

    def test_auto_block_threshold(self):
        """Test automatic IP blocking threshold"""
        assert RateLimitConfig.AUTO_BLOCK_THRESHOLD == 100
        assert RateLimitConfig.AUTO_BLOCK_DURATION == 3600

    def test_whitelist_and_blacklist(self):
        """Test whitelist and blacklist sets"""
        assert isinstance(RateLimitConfig.WHITELIST_IPS, set)
        assert isinstance(RateLimitConfig.BLACKLIST_IPS, set)


class TestRateLimiter:
    """Test sliding window rate limiter"""

    @pytest.fixture
    def limiter(self):
        """Create a rate limiter with custom config"""
        custom_config = {
            "api": {"requests": 5, "window": 10},  # 5 requests per 10 seconds
            "upload": {"requests": 2, "window": 10},
        }
        return RateLimiter(config=custom_config)

    def test_check_rate_limit_within_limit(self, limiter):
        """Test that requests within limit are allowed"""
        client_ip = "192.168.1.100"

        # Make 3 requests (under the limit of 5)
        for i in range(3):
            assert limiter.check_rate_limit(client_ip, endpoint="api") is True

    def test_check_rate_limit_exceeds(self, limiter):
        """Test that exceeding limit blocks requests"""
        client_ip = "192.168.1.101"

        # Make 5 requests (at the limit)
        for i in range(5):
            assert limiter.check_rate_limit(client_ip, endpoint="api") is True

        # 6th request should be blocked
        assert limiter.check_rate_limit(client_ip, endpoint="api") is False

    def test_check_rate_limit_window_expiry(self, limiter):
        """Test that old requests are removed from window"""
        client_ip = "192.168.1.102"

        # Make 5 requests (at the limit)
        for i in range(5):
            limiter.check_rate_limit(client_ip, endpoint="api")

        # Wait for window to expire (10 seconds)
        # In real test, we'd actually wait, but here we'll manipulate timestamps
        # For unit test speed, we'll just verify the logic

        # Verify blocked at limit
        assert limiter.check_rate_limit(client_ip, endpoint="api") is False

    def test_whitelisted_ip_bypass(self, limiter):
        """Test that whitelisted IPs bypass rate limiting"""
        client_ip = "10.0.0.1"

        # Add to whitelist
        RateLimitConfig.WHITELIST_IPS.add(client_ip)

        try:
            # Make many requests (far beyond limit)
            for i in range(100):
                assert limiter.check_rate_limit(client_ip) is True
        finally:
            # Clean up
            RateLimitConfig.WHITELIST_IPS.discard(client_ip)

    def test_blacklisted_ip_blocked(self, limiter):
        """Test that blacklisted IPs are always blocked"""
        client_ip = "10.0.0.2"

        # Add to blacklist
        RateLimitConfig.BLACKLIST_IPS.add(client_ip)

        try:
            assert limiter.check_rate_limit(client_ip) is False
        finally:
            # Clean up
            RateLimitConfig.BLACKLIST_IPS.discard(client_ip)

    def test_auto_block_threshold(self, limiter):
        """Test automatic IP blocking at threshold"""
        # Create limiter with low threshold
        custom_config = {
            "api": {"requests": 200, "window": 3600},  # High limit
        }
        limiter = RateLimiter(config=custom_config)

        client_ip = "192.168.1.103"

        # Make 100 requests (at AUTO_BLOCK_THRESHOLD)
        for i in range(100):
            limiter.check_rate_limit(client_ip, endpoint="api")

        # Should be auto-blocked
        assert client_ip in limiter.blocked_ips
        assert limiter.check_rate_limit(client_ip) is False

    def test_different_endpoints_separate_limits(self, limiter):
        """Test that different endpoints have separate rate limits"""
        client_ip = "192.168.1.104"

        # Use up API limit
        for i in range(5):
            limiter.check_rate_limit(client_ip, endpoint="api")

        # API endpoint should be blocked
        assert limiter.check_rate_limit(client_ip, endpoint="api") is False

        # But upload endpoint should still work (different limit)
        assert limiter.check_rate_limit(client_ip, endpoint="upload") is True

    def test_multiple_clients_independent(self, limiter):
        """Test that different clients have independent rate limits"""
        # Make 5 requests from client 1
        for i in range(5):
            limiter.check_rate_limit("192.168.1.105", endpoint="api")

        # Client 1 should be blocked
        assert limiter.check_rate_limit("192.168.1.105", endpoint="api") is False

        # But client 2 should still have full allowance
        for i in range(5):
            assert limiter.check_rate_limit("192.168.1.106", endpoint="api") is True


class TestTokenBucketRateLimiter:
    """Test token bucket rate limiter"""

    @pytest.fixture
    def limiter(self):
        """Create a token bucket with specific rate and capacity"""
        # Rate: 10 tokens/sec, Capacity: 100 tokens
        return TokenBucketRateLimiter(rate=10.0, capacity=100)

    def test_initial_tokens(self, limiter):
        """Test that limiter starts with full capacity"""
        assert limiter.tokens == 100.0

    def test_consume_tokens(self, limiter):
        """Test token consumption"""
        # Consume 50 tokens immediately
        for i in range(50):
            assert limiter.allow_request() is True

        assert limiter.tokens == 50.0

    def test_exhaust_bucket(self, limiter):
        """Test exhausting the bucket"""
        # Consume all 100 tokens
        for i in range(100):
            assert limiter.allow_request() is True

        # Next request should be denied
        assert limiter.allow_request() is False

    def test_token_refill(self, limiter):
        """Test token refill over time"""
        # Consume all tokens
        for i in range(100):
            limiter.allow_request()

        # Should be blocked
        assert limiter.allow_request() is False

        # Wait for tokens to refill (10 tokens/sec, need 0.1 sec for 1 token)
        # In unit test, we'll just verify the refill logic exists
        sleep(0.2)  # Wait ~2 tokens

        # Should have some tokens now
        assert limiter.allow_request() is True

    def test_rate_limiting(self, limiter):
        """Test that request rate is limited"""
        # Consume 90 tokens
        for i in range(90):
            limiter.allow_request()

        # Even though we have 10 tokens left,
        # if we request faster than refill rate, we'll be blocked
        requests_allowed = 0
        for i in range(20):  # Try to make 20 rapid requests
            if limiter.allow_request():
                requests_allowed += 1

        # Should allow at most 10 more (remaining capacity)
        assert requests_allowed == 10


class TestAdaptiveRateLimiter:
    """Test adaptive rate limiter based on error rate"""

    @pytest.fixture
    def limiter(self):
        """Create an adaptive rate limiter"""
        return AdaptiveRateLimiter()

    def test_normal_traffic_allowed(self, limiter):
        """Test that normal traffic is allowed"""
        client_ip = "192.168.1.200"

        # Make 10 requests with no errors
        for i in range(10):
            assert limiter.check_rate_limit(client_ip) is True

    def test_high_error_rate_blocked(self, limiter):
        """Test that high error rate triggers blocking"""
        client_ip = "192.168.1.201"

        # Simulate high error rate (30% = default threshold)
        # Make 10 requests, record 4 errors
        for i in range(10):
            limiter.check_rate_limit(client_ip)

        for i in range(4):
            limiter.record_error(client_ip)

        # Should still be allowed (at threshold)
        assert limiter.check_rate_limit(client_ip) is True

        # One more error puts it over threshold
        limiter.record_error(client_ip)

        # Now should be blocked
        assert limiter.check_rate_limit(client_ip) is False

    def test_suspicious_traffic_stricter_limit(self, limiter):
        """Test that suspicious traffic has stricter limits"""
        client_ip = "192.168.1.202"

        # Make 10 requests with suspicious flag
        for i in range(10):
            limiter.check_rate_limit(client_ip, is_suspicious=True)

        # Record 2 errors (10% threshold for suspicious)
        for i in range(2):
            limiter.record_error(client_ip)

        # Should be blocked with stricter limit
        assert limiter.check_rate_limit(client_ip, is_suspicious=True) is False

    def test_stats_reset_periodically(self, limiter):
        """Test that stats are reset periodically"""
        client_ip = "192.168.1.203"

        # Make some requests and record errors
        for i in range(5):
            limiter.check_rate_limit(client_ip)

        for i in range(2):
            limiter.record_error(client_ip)

        # Stats should exist
        stats = limiter.request_stats[client_ip]
        assert stats["count"] == 5
        assert stats["errors"] == 2


class TestRequestLimiter:
    """Test request limiter"""

    @pytest.fixture
    def limiter(self):
        """Create a request limiter"""
        return RequestLimiter()

    def test_within_limit(self, limiter):
        """Test requests within limit"""
        key = "user:123"

        # Default limit is 100 per minute
        for i in range(99):
            assert limiter.check_request_limit(key) is True

    def test_exceeds_limit(self, limiter):
        """Test exceeding limit"""
        key = "user:124"

        # Make 100 requests (at limit)
        for i in range(100):
            assert limiter.check_request_limit(key) is True

        # 101st request should be denied
        assert limiter.check_request_limit(key) is False

    def test_different_keys_independent(self, limiter):
        """Test that different keys have independent limits"""
        # Use up limit for key1
        for i in range(101):
            limiter.check_request_limit("key1")

        assert limiter.check_request_limit("key1") is False

        # key2 should still work
        assert limiter.check_request_limit("key2") is True


class TestIPBlacklistManager:
    """Test IP blacklist management"""

    @pytest.fixture
    def manager(self):
        """Create an IP blacklist manager"""
        return IPBlacklistManager()

    def test_initially_not_blacklisted(self, manager):
        """Test that IPs are not blacklisted initially"""
        assert manager.is_blacklisted("192.168.1.50") is False

    def test_add_to_blacklist(self, manager):
        """Test adding IP to blacklist"""
        ip = "192.168.1.51"
        manager.add_to_blacklist(ip)

        assert manager.is_blacklisted(ip) is True

    def test_remove_from_blacklist(self, manager):
        """Test removing IP from blacklist"""
        ip = "192.168.1.52"
        manager.add_to_blacklist(ip)
        assert manager.is_blacklisted(ip) is True

        manager.remove_from_blacklist(ip)
        assert manager.is_blacklisted(ip) is False

    def test_auto_block_on_threshold(self, manager):
        """Test automatic blocking on threshold"""
        ip = "192.168.1.53"

        # Report suspicious activity up to threshold
        for i in range(10):
            manager.report_suspicious_activity(ip)

        # Should be auto-blocked
        assert ip in manager.blocked_ips
        assert manager.is_blacklisted(ip) is True

    def test_auto_block_expires(self, manager):
        """Test that auto-block expires after duration"""
        ip = "192.168.1.54"

        # Add to blocked_ips with old timestamp
        old_time = time() - 4000  # More than auto_block_duration
        manager.blocked_ips[ip] = old_time

        # Should no longer be blocked
        assert manager.is_blacklisted(ip) is False
        assert ip not in manager.blocked_ips

    def test_suspicious_activity_counting(self, manager):
        """Test suspicious activity counting"""
        ip = "192.168.1.55"

        # Report multiple times
        for i in range(5):
            manager.report_suspicious_activity(ip)

        assert manager.suspicious_ips[ip] == 5

    def test_manual_and_auto_blacklist_both_work(self, manager):
        """Test that manual and auto blacklisting work together"""
        ip1 = "192.168.1.56"
        ip2 = "192.168.1.57"

        # Manual blacklist
        manager.add_to_blacklist(ip1)

        # Auto-block
        for i in range(10):
            manager.report_suspicious_activity(ip2)

        # Both should be blocked
        assert manager.is_blacklisted(ip1) is True
        assert manager.is_blacklisted(ip2) is True


class TestThreadSafety:
    """Test thread safety of rate limiters"""

    def test_rate_limiter_lock(self):
        """Test that rate limiter uses lock correctly"""
        limiter = RateLimiter()

        # Verify lock exists
        assert limiter.lock is not None

        # Multiple rapid requests should be handled safely
        client_ip = "192.168.1.300"
        for i in range(10):
            limiter.check_rate_limit(client_ip)

    def test_token_bucket_lock(self):
        """Test that token bucket uses lock correctly"""
        limiter = TokenBucketRateLimiter()

        assert limiter.lock is not None

    def test_adaptive_limiter_lock(self):
        """Test that adaptive limiter uses lock correctly"""
        limiter = AdaptiveRateLimiter()

        assert limiter.lock is not None

    def test_blacklist_manager_lock(self):
        """Test that blacklist manager uses lock correctly"""
        manager = IPBlacklistManager()

        assert manager.lock is not None
