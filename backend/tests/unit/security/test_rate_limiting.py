"""
Rate limiting configuration tests.
"""

from src.security.rate_limiting import AdaptiveRateLimiter, RequestLimiter


class TestAdaptiveRateLimiter:
    """自适应限流测试"""

    def test_blocks_when_error_rate_exceeds_threshold(self):
        limiter = AdaptiveRateLimiter({"max_error_rate": 0.2, "reset_seconds": 60})
        key = "203.0.113.20"

        assert limiter.check_rate_limit(key) is True
        limiter.record_error(key)

        assert limiter.check_rate_limit(key) is False

    def test_disabled_allows_requests(self):
        limiter = AdaptiveRateLimiter({"enabled": False})
        assert limiter.check_rate_limit("203.0.113.21") is True


class TestRequestLimiter:
    """请求限制器测试"""

    def test_blocks_after_limit(self):
        limiter = RequestLimiter({"max_requests_per_minute": 2, "reset_seconds": 60})
        key = "user:1"

        assert limiter.check_request_limit(key) is True
        assert limiter.check_request_limit(key) is True
        assert limiter.check_request_limit(key) is False

    def test_disabled_allows_requests(self):
        limiter = RequestLimiter({"enabled": False})
        assert limiter.check_request_limit("user:2") is True
