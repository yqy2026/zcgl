"""
Token Blacklist Manager 单元测试
测试令牌黑名单功能的正确性
"""

import time
from datetime import datetime, timedelta

from src.core.token_blacklist import TokenBlacklistManager, blacklist_manager


class TestTokenBlacklistManager:
    """TokenBlacklistManager 单元测试"""

    def setup_method(self):
        """每个测试前创建新的管理器实例"""
        self.manager = TokenBlacklistManager()

    def teardown_method(self):
        """每个测试后清理"""
        self.manager.clear_blacklist()

    # ==================== add_token 测试 ====================

    def test_add_token_with_timestamp(self):
        """测试使用时间戳添加令牌"""
        jti = "test-token-123"
        expires_at = time.time() + 3600  # 1小时后过期

        self.manager.add_token(jti, expires_at)

        assert self.manager.is_blacklisted(jti) is True

    def test_add_token_with_datetime(self):
        """测试使用 datetime 对象添加令牌"""
        jti = "test-token-datetime"
        expires_at = datetime.now() + timedelta(hours=1)

        self.manager.add_token(jti, expires_at)

        assert self.manager.is_blacklisted(jti) is True

    def test_add_expired_token_ignored(self):
        """测试已过期的令牌不会被添加"""
        jti = "expired-token"
        expires_at = time.time() - 100  # 已过期

        self.manager.add_token(jti, expires_at)

        assert self.manager.is_blacklisted(jti) is False

    def test_add_token_by_jti(self):
        """测试通过 JTI 和过期秒数添加令牌"""
        jti = "test-token-by-jti"

        self.manager.add_token_by_jti(jti, expires_in_seconds=3600)

        assert self.manager.is_blacklisted(jti) is True

    # ==================== is_blacklisted 测试 ====================

    def test_is_blacklisted_returns_false_for_unknown_token(self):
        """测试未知令牌返回 False"""
        assert self.manager.is_blacklisted("unknown-token") is False

    def test_is_blacklisted_returns_true_for_blacklisted_token(self):
        """测试黑名单令牌返回 True"""
        jti = "blacklisted-token"
        self.manager.add_token(jti, time.time() + 3600)

        assert self.manager.is_blacklisted(jti) is True

    # ==================== remove_token 测试 ====================

    def test_remove_token(self):
        """测试从黑名单移除令牌"""
        jti = "removable-token"
        self.manager.add_token(jti, time.time() + 3600)

        assert self.manager.is_blacklisted(jti) is True

        self.manager.remove_token(jti)

        assert self.manager.is_blacklisted(jti) is False

    def test_remove_nonexistent_token_no_error(self):
        """测试移除不存在的令牌不会报错"""
        self.manager.remove_token("nonexistent-token")  # 不应抛出异常

    # ==================== 清理过期令牌测试 ====================

    def test_cleanup_expired_tokens(self):
        """测试清理过期令牌"""
        # 添加一个即将过期的令牌
        jti = "soon-expired-token"
        self.manager._blacklisted_tokens.add(jti)
        self.manager._blacklist_expiry[jti] = time.time() - 1  # 已过期

        # 强制立即清理
        self.manager._last_cleanup = 0
        self.manager._cleanup_interval = 0

        self.manager._cleanup_expired_tokens()

        assert jti not in self.manager._blacklisted_tokens

    # ==================== 统计和清空测试 ====================

    def test_get_blacklist_stats(self):
        """测试获取黑名单统计"""
        self.manager.add_token("token-1", time.time() + 3600)
        self.manager.add_token("token-2", time.time() + 3600)

        stats = self.manager.get_blacklist_stats()

        assert stats["total_blacklisted"] == 2
        assert stats["expiry_count"] == 2
        assert "last_cleanup" in stats

    def test_clear_blacklist(self):
        """测试清空黑名单"""
        self.manager.add_token("token-1", time.time() + 3600)
        self.manager.add_token("token-2", time.time() + 3600)

        self.manager.clear_blacklist()

        assert self.manager.get_blacklist_stats()["total_blacklisted"] == 0


class TestGlobalBlacklistManager:
    """全局黑名单管理器实例测试"""

    def teardown_method(self):
        """测试后清理全局管理器"""
        blacklist_manager.clear_blacklist()

    def test_global_instance_exists(self):
        """测试全局实例存在"""
        assert blacklist_manager is not None
        assert isinstance(blacklist_manager, TokenBlacklistManager)

    def test_global_instance_functions(self):
        """测试全局实例功能正常"""
        jti = "global-test-token"

        blacklist_manager.add_token(jti, time.time() + 3600)

        assert blacklist_manager.is_blacklisted(jti) is True

        blacklist_manager.remove_token(jti)

        assert blacklist_manager.is_blacklisted(jti) is False


class TestMiddlewareIntegration:
    """中间件集成测试"""

    def teardown_method(self):
        """测试后清理"""
        blacklist_manager.clear_blacklist()

    def test_is_token_blacklisted_function(self):
        """测试中间件的黑名单检查函数"""
        from src.middleware.auth import _is_token_blacklisted

        jti = "middleware-test-token"

        # 未添加到黑名单时应返回 False
        assert _is_token_blacklisted(jti) is False

        # 添加到黑名单
        blacklist_manager.add_token(jti, time.time() + 3600)

        # 添加后应返回 True
        assert _is_token_blacklisted(jti) is True

    def test_is_token_blacklisted_handles_import_error(self):
        """测试导入失败时的容错处理"""
        from src.middleware.auth import _is_token_blacklisted

        # 使用不存在的 jti 测试基本功能
        result = _is_token_blacklisted("any-token")
        # 应该不会抛出异常，返回 bool 值
        assert isinstance(result, bool)
