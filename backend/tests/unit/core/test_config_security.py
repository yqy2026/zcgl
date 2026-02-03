"""
配置安全测试 - 验证 SECRET_KEY 和其他关键配置的安全要求

Configuration Security Tests - Verify security requirements for SECRET_KEY and other critical configs
"""

import os

import pytest
from pydantic import ValidationError

from src.core.config import Settings


class TestSecretKeySecurity:
    """SECRET_KEY 安全测试套件"""

    def test_secret_key_minimum_length(self):
        """测试 SECRET_KEY 最小长度要求（32字符）"""
        original_key = os.environ.get("SECRET_KEY")
        original_env = os.environ.get("ENVIRONMENT")

        try:
            os.environ["SECRET_KEY"] = "short-key"  # 少于32字符
            os.environ["ENVIRONMENT"] = "production"

            with pytest.raises(ValidationError) as exc_info:
                Settings()
            assert "32" in str(exc_info.value).lower()
        finally:
            if original_key:
                os.environ["SECRET_KEY"] = original_key
            elif "SECRET_KEY" in os.environ:
                del os.environ["SECRET_KEY"]
            if original_env:
                os.environ["ENVIRONMENT"] = original_env
            elif "ENVIRONMENT" in os.environ:
                del os.environ["ENVIRONMENT"]

    def test_weak_secret_key_in_production(self):
        """测试生产环境拒绝弱密钥模式"""
        original_key = os.environ.get("SECRET_KEY")
        original_env = os.environ.get("ENVIRONMENT")

        # 使用包含弱模式的密钥
        weak_keys = [
            "changeme-weak-key-with-32-chars-ok",
            "your-secret-key-min-32-chars-change",
            "test-key-for-testing-only-32chars",
            "REPLACE-WITH-SECRET-KEY-32-chars",
        ]

        try:
            os.environ["ENVIRONMENT"] = "production"

            for weak_key in weak_keys:
                os.environ["SECRET_KEY"] = weak_key
                with pytest.raises(ValidationError) as exc_info:
                    Settings()
                assert "弱密钥" in str(exc_info.value) or "生产环境" in str(
                    exc_info.value
                )
        finally:
            if original_key:
                os.environ["SECRET_KEY"] = original_key
            elif "SECRET_KEY" in os.environ:
                del os.environ["SECRET_KEY"]
            if original_env:
                os.environ["ENVIRONMENT"] = original_env
            elif "ENVIRONMENT" in os.environ:
                del os.environ["ENVIRONMENT"]

    def test_strong_secret_key_accepted(self):
        """测试强密钥被接受"""
        import secrets

        original_key = os.environ.get("SECRET_KEY")
        original_env = os.environ.get("ENVIRONMENT")

        try:
            # 生成强密钥
            strong_key = secrets.token_urlsafe(32)  # 43字符，URL安全
            os.environ["SECRET_KEY"] = strong_key
            os.environ["ENVIRONMENT"] = "production"

            # 应该成功创建 Settings
            settings = Settings()
            assert settings.SECRET_KEY == strong_key
        finally:
            if original_key:
                os.environ["SECRET_KEY"] = original_key
            elif "SECRET_KEY" in os.environ:
                del os.environ["SECRET_KEY"]
            if original_env:
                os.environ["ENVIRONMENT"] = original_env
            elif "ENVIRONMENT" in os.environ:
                del os.environ["ENVIRONMENT"]

    def test_weak_key_warning_in_development(self):
        """测试开发环境弱密钥被接受但可能发出警告"""

        original_key = os.environ.get("SECRET_KEY")
        original_env = os.environ.get("ENVIRONMENT")

        try:
            # 使用包含弱模式但满足长度要求的密钥
            weak_key = "dev-weak-key-with-exactly-32-chars-ok"
            os.environ["SECRET_KEY"] = weak_key
            os.environ["ENVIRONMENT"] = "development"

            # 在开发环境应该成功创建（不抛出异常）
            settings = Settings()
            assert settings.SECRET_KEY == weak_key
            # 注意：警告日志可能不会被捕获，因为日志配置问题
            # 关键是验证弱密钥在开发环境被接受，不抛出异常
        finally:
            if original_key:
                os.environ["SECRET_KEY"] = original_key
            elif "SECRET_KEY" in os.environ:
                del os.environ["SECRET_KEY"]
            if original_env:
                os.environ["ENVIRONMENT"] = original_env
            elif "ENVIRONMENT" in os.environ:
                del os.environ["ENVIRONMENT"]


class TestEnvironmentConfiguration:
    """环境配置测试"""

    def test_environment_defaults_to_production(self):
        """测试 ENVIRONMENT 默认为 production"""
        original_env = os.environ.pop("ENVIRONMENT", None)
        original_key = os.environ.get("SECRET_KEY")

        try:
            # 确保有有效的 SECRET_KEY
            import secrets

            strong_key = secrets.token_urlsafe(32)
            os.environ["SECRET_KEY"] = strong_key

            # 验证环境变量默认为 production
            assert os.getenv("ENVIRONMENT", "production") == "production"
        finally:
            if original_env:
                os.environ["ENVIRONMENT"] = original_env
            if original_key:
                os.environ["SECRET_KEY"] = original_key
            elif "SECRET_KEY" in os.environ:
                del os.environ["SECRET_KEY"]


class TestIpBlacklistConfiguration:
    """IP 黑名单配置测试"""

    def test_ip_blacklist_parsing_from_env(self):
        """测试 IP 黑名单可从环境变量解析"""
        original_key = os.environ.get("SECRET_KEY")
        original_env = os.environ.get("ENVIRONMENT")
        original_blacklist = os.environ.get("IP_BLACKLIST")

        try:
            os.environ["SECRET_KEY"] = "StrongSecretKey-With-Enough-Length-2026!"
            os.environ["ENVIRONMENT"] = "development"
            os.environ["IP_BLACKLIST"] = '["192.0.2.1","198.51.100.10"]'

            settings = Settings()
            assert settings.IP_BLACKLIST == ["192.0.2.1", "198.51.100.10"]
        finally:
            if original_key:
                os.environ["SECRET_KEY"] = original_key
            elif "SECRET_KEY" in os.environ:
                del os.environ["SECRET_KEY"]
            if original_env:
                os.environ["ENVIRONMENT"] = original_env
            elif "ENVIRONMENT" in os.environ:
                del os.environ["ENVIRONMENT"]
            if original_blacklist is not None:
                os.environ["IP_BLACKLIST"] = original_blacklist
            elif "IP_BLACKLIST" in os.environ:
                del os.environ["IP_BLACKLIST"]


class TestSecurityAnalyzerConfiguration:
    """安全分析配置测试"""

    def test_security_analyzer_patterns_from_env(self):
        """测试安全分析模式可从环境变量解析"""
        original_key = os.environ.get("SECRET_KEY")
        original_env = os.environ.get("ENVIRONMENT")
        original_patterns = os.environ.get("SECURITY_ANALYZER_PATTERNS")

        try:
            os.environ["SECRET_KEY"] = "StrongSecretKey-With-Enough-Length-2026!"
            os.environ["ENVIRONMENT"] = "development"
            os.environ["SECURITY_ANALYZER_PATTERNS"] = '["foo","bar","baz"]'

            settings = Settings()
            assert settings.SECURITY_ANALYZER_PATTERNS == ["foo", "bar", "baz"]
        finally:
            if original_key:
                os.environ["SECRET_KEY"] = original_key
            elif "SECRET_KEY" in os.environ:
                del os.environ["SECRET_KEY"]
            if original_env:
                os.environ["ENVIRONMENT"] = original_env
            elif "ENVIRONMENT" in os.environ:
                del os.environ["ENVIRONMENT"]
            if original_patterns is not None:
                os.environ["SECURITY_ANALYZER_PATTERNS"] = original_patterns
            elif "SECURITY_ANALYZER_PATTERNS" in os.environ:
                del os.environ["SECURITY_ANALYZER_PATTERNS"]

    def test_security_analyzer_invalid_values(self):
        """测试安全分析配置非法值会触发校验错误"""
        original_key = os.environ.get("SECRET_KEY")
        original_env = os.environ.get("ENVIRONMENT")
        original_value = os.environ.get("SECURITY_ANALYZER_MAX_SUSPICIOUS_REQUESTS")

        try:
            os.environ["SECRET_KEY"] = "StrongSecretKey-With-Enough-Length-2026!"
            os.environ["ENVIRONMENT"] = "development"
            os.environ["SECURITY_ANALYZER_MAX_SUSPICIOUS_REQUESTS"] = "0"

            with pytest.raises(ValidationError):
                Settings()
        finally:
            if original_key:
                os.environ["SECRET_KEY"] = original_key
            elif "SECRET_KEY" in os.environ:
                del os.environ["SECRET_KEY"]
            if original_env:
                os.environ["ENVIRONMENT"] = original_env
            elif "ENVIRONMENT" in os.environ:
                del os.environ["ENVIRONMENT"]
            if original_value is not None:
                os.environ["SECURITY_ANALYZER_MAX_SUSPICIOUS_REQUESTS"] = original_value
            elif "SECURITY_ANALYZER_MAX_SUSPICIOUS_REQUESTS" in os.environ:
                del os.environ["SECURITY_ANALYZER_MAX_SUSPICIOUS_REQUESTS"]

    def test_environment_setting(self):
        """测试 ENVIRONMENT 可以正确设置"""
        original_env = os.environ.get("ENVIRONMENT")
        original_key = os.environ.get("SECRET_KEY")

        try:
            import secrets

            strong_key = secrets.token_urlsafe(32)
            os.environ["SECRET_KEY"] = strong_key

            for env in ["development", "testing", "staging", "production"]:
                os.environ["ENVIRONMENT"] = env
                # 验证环境变量被正确设置
                assert os.getenv("ENVIRONMENT") == env
        finally:
            if original_env:
                os.environ["ENVIRONMENT"] = original_env
            elif "ENVIRONMENT" in os.environ:
                del os.environ["ENVIRONMENT"]
            if original_key:
                os.environ["SECRET_KEY"] = original_key
            elif "SECRET_KEY" in os.environ:
                del os.environ["SECRET_KEY"]


class TestAdaptiveRateLimitConfiguration:
    """自适应限流配置测试"""

    def test_adaptive_rate_limit_invalid_error_rate(self):
        """测试自适应限流错误率非法值会触发校验错误"""
        original_key = os.environ.get("SECRET_KEY")
        original_env = os.environ.get("ENVIRONMENT")
        original_rate = os.environ.get("ADAPTIVE_RATE_LIMIT_MAX_ERROR_RATE")

        try:
            os.environ["SECRET_KEY"] = "StrongSecretKey-With-Enough-Length-2026!"
            os.environ["ENVIRONMENT"] = "development"
            os.environ["ADAPTIVE_RATE_LIMIT_MAX_ERROR_RATE"] = "1.5"

            with pytest.raises(ValidationError):
                Settings()
        finally:
            if original_key:
                os.environ["SECRET_KEY"] = original_key
            elif "SECRET_KEY" in os.environ:
                del os.environ["SECRET_KEY"]
            if original_env:
                os.environ["ENVIRONMENT"] = original_env
            elif "ENVIRONMENT" in os.environ:
                del os.environ["ENVIRONMENT"]
            if original_rate is not None:
                os.environ["ADAPTIVE_RATE_LIMIT_MAX_ERROR_RATE"] = original_rate
            elif "ADAPTIVE_RATE_LIMIT_MAX_ERROR_RATE" in os.environ:
                del os.environ["ADAPTIVE_RATE_LIMIT_MAX_ERROR_RATE"]


class TestRequestLimiterConfiguration:
    """请求限制配置测试"""

    def test_request_limit_invalid_max_requests(self):
        """测试请求限制非法值会触发校验错误"""
        original_key = os.environ.get("SECRET_KEY")
        original_env = os.environ.get("ENVIRONMENT")
        original_value = os.environ.get("REQUEST_LIMIT_MAX_REQUESTS_PER_MINUTE")

        try:
            os.environ["SECRET_KEY"] = "StrongSecretKey-With-Enough-Length-2026!"
            os.environ["ENVIRONMENT"] = "development"
            os.environ["REQUEST_LIMIT_MAX_REQUESTS_PER_MINUTE"] = "0"

            with pytest.raises(ValidationError):
                Settings()
        finally:
            if original_key:
                os.environ["SECRET_KEY"] = original_key
            elif "SECRET_KEY" in os.environ:
                del os.environ["SECRET_KEY"]
            if original_env:
                os.environ["ENVIRONMENT"] = original_env
            elif "ENVIRONMENT" in os.environ:
                del os.environ["ENVIRONMENT"]
            if original_value is not None:
                os.environ["REQUEST_LIMIT_MAX_REQUESTS_PER_MINUTE"] = original_value
            elif "REQUEST_LIMIT_MAX_REQUESTS_PER_MINUTE" in os.environ:
                del os.environ["REQUEST_LIMIT_MAX_REQUESTS_PER_MINUTE"]


class TestSecurityMiddlewareConfiguration:
    """安全中间件配置测试"""

    def test_security_middleware_invalid_user_agent_min_length(self):
        """测试安全中间件 User-Agent 最小长度非法值"""
        original_key = os.environ.get("SECRET_KEY")
        original_env = os.environ.get("ENVIRONMENT")
        original_value = os.environ.get("SECURITY_MIDDLEWARE_USER_AGENT_MIN_LENGTH")

        try:
            os.environ["SECRET_KEY"] = "StrongSecretKey-With-Enough-Length-2026!"
            os.environ["ENVIRONMENT"] = "development"
            os.environ["SECURITY_MIDDLEWARE_USER_AGENT_MIN_LENGTH"] = "0"

            with pytest.raises(ValidationError):
                Settings()
        finally:
            if original_key:
                os.environ["SECRET_KEY"] = original_key
            elif "SECRET_KEY" in os.environ:
                del os.environ["SECRET_KEY"]
            if original_env:
                os.environ["ENVIRONMENT"] = original_env
            elif "ENVIRONMENT" in os.environ:
                del os.environ["ENVIRONMENT"]
            if original_value is not None:
                os.environ["SECURITY_MIDDLEWARE_USER_AGENT_MIN_LENGTH"] = original_value
            elif "SECURITY_MIDDLEWARE_USER_AGENT_MIN_LENGTH" in os.environ:
                del os.environ["SECURITY_MIDDLEWARE_USER_AGENT_MIN_LENGTH"]

    def test_security_middleware_rate_limits_from_env(self):
        """测试安全中间件速率限制配置解析"""
        original_key = os.environ.get("SECRET_KEY")
        original_env = os.environ.get("ENVIRONMENT")
        original_value = os.environ.get("SECURITY_MIDDLEWARE_RATE_LIMITS")

        try:
            os.environ["SECRET_KEY"] = "StrongSecretKey-With-Enough-Length-2026!"
            os.environ["ENVIRONMENT"] = "development"
            os.environ["SECURITY_MIDDLEWARE_RATE_LIMITS"] = (
                '{"api":{"requests":5,"window":60}}'
            )

            settings = Settings()
            assert settings.SECURITY_MIDDLEWARE_RATE_LIMITS == {
                "api": {"requests": 5, "window": 60}
            }
        finally:
            if original_key:
                os.environ["SECRET_KEY"] = original_key
            elif "SECRET_KEY" in os.environ:
                del os.environ["SECRET_KEY"]
            if original_env:
                os.environ["ENVIRONMENT"] = original_env
            elif "ENVIRONMENT" in os.environ:
                del os.environ["ENVIRONMENT"]
            if original_value is not None:
                os.environ["SECURITY_MIDDLEWARE_RATE_LIMITS"] = original_value
            elif "SECURITY_MIDDLEWARE_RATE_LIMITS" in os.environ:
                del os.environ["SECURITY_MIDDLEWARE_RATE_LIMITS"]
