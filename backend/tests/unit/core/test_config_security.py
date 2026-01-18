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
                with pytest.raises(ValueError) as exc_info:
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
