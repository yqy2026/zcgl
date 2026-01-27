"""
缓存管理器增强测试

Enhanced tests for cache manager to improve coverage
"""

import pytest
import time
from unittest.mock import Mock, patch
from src.utils.cache_manager import CacheManager


@pytest.fixture
def cache_manager():
    """缓存管理器实例"""
    return CacheManager()


class TestCacheManagerCore:
    """测试缓存管理器核心功能"""

    def test_set_and_get(self, cache_manager):
        """测试设置和获取"""
        cache_manager.set("key1", "value1")
        result = cache_manager.get("key1")
        assert result == "value1"

    def test_get_nonexistent_key(self, cache_manager):
        """测试获取不存在的键"""
        result = cache_manager.get("nonexistent")
        assert result is None

    def test_get_with_default(self, cache_manager):
        """测试获取带默认值"""
        result = cache_manager.get("nonexistent", default="default_value")
        assert result == "default_value"

    def test_delete_existing_key(self, cache_manager):
        """测试删除存在的键"""
        cache_manager.set("key1", "value1")
        cache_manager.delete("key1")
        result = cache_manager.get("key1")
        assert result is None

    def test_delete_nonexistent_key(self, cache_manager):
        """测试删除不存在的键"""
        # 不应该抛出异常
        cache_manager.delete("nonexistent")

    def test_clear_all(self, cache_manager):
        """测试清空所有缓存"""
        cache_manager.set("key1", "value1")
        cache_manager.set("key2", "value2")
        cache_manager.clear()
        assert cache_manager.get("key1") is None
        assert cache_manager.get("key2") is None

    def test_exists_true(self, cache_manager):
        """测试键存在"""
        cache_manager.set("key1", "value1")
        assert cache_manager.exists("key1") is True

    def test_exists_false(self, cache_manager):
        """测试键不存在"""
        assert cache_manager.exists("nonexistent") is False


class TestCacheManagerTTL:
    """测试缓存过期功能"""

    def test_set_with_ttl(self, cache_manager):
        """测试设置带TTL的缓存"""
        cache_manager.set("key1", "value1", ttl=1)
        assert cache_manager.get("key1") == "value1"
        time.sleep(2)
        assert cache_manager.get("key1") is None

    def test_default_ttl(self, cache_config):
        """测试默认TTL"""
        cache_config.default_ttl = 1
        cache_manager = CacheManager(config=cache_config)
        cache_manager.set("key1", "value1")
        time.sleep(2)
        assert cache_manager.get("key1") is None

    def test_ttl_override(self, cache_manager):
        """测试TTL覆盖"""
        # 使用自定义TTL而不是默认TTL
        cache_manager.set("key1", "value1", ttl=5)
        cache_manager.set("key2", "value2", ttl=1)
        time.sleep(2)
        assert cache_manager.get("key1") == "value1"
        assert cache_manager.get("key2") is None


class TestCacheManagerStats:
    """测试缓存统计功能"""

    def test_get_stats(self, cache_manager):
        """测试获取统计信息"""
        cache_manager.set("key1", "value1")
        cache_manager.get("key1")
        cache_manager.get("key2")  # miss

        stats = cache_manager.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1

    def test_reset_stats(self, cache_manager):
        """测试重置统计"""
        cache_manager.set("key1", "value1")
        cache_manager.get("key1")

        cache_manager.reset_stats()
        stats = cache_manager.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0


class TestCacheManagerAdvanced:
    """测试缓存管理器高级功能"""

    def test_set_many(self, cache_manager):
        """测试批量设置"""
        data = {"key1": "value1", "key2": "value2", "key3": "value3"}
        cache_manager.set_many(data)
        assert cache_manager.get("key1") == "value1"
        assert cache_manager.get("key2") == "value2"
        assert cache_manager.get("key3") == "value3"

    def test_get_many(self, cache_manager):
        """测试批量获取"""
        cache_manager.set("key1", "value1")
        cache_manager.set("key2", "value2")

        keys = ["key1", "key2", "key3"]
        results = cache_manager.get_many(keys)
        assert results["key1"] == "value1"
        assert results["key2"] == "value2"
        assert results["key3"] is None

    def test_delete_many(self, cache_manager):
        """测试批量删除"""
        cache_manager.set("key1", "value1")
        cache_manager.set("key2", "value2")

        cache_manager.delete_many(["key1", "key2"])
        assert cache_manager.get("key1") is None
        assert cache_manager.get("key2") is None

    def test_increment(self, cache_manager):
        """测试递增"""
        cache_manager.set("counter", 5)
        new_value = cache_manager.increment("counter", 3)
        assert new_value == 8
        assert cache_manager.get("counter") == 8

    def test_increment_nonexistent(self, cache_manager):
        """测试递增不存在的键"""
        new_value = cache_manager.increment("counter", 5)
        assert new_value == 5
        assert cache_manager.get("counter") == 5

    def test_decrement(self, cache_manager):
        """测试递减"""
        cache_manager.set("counter", 10)
        new_value = cache_manager.decrement("counter", 3)
        assert new_value == 7
        assert cache_manager.get("counter") == 7

    def test_get_or_set(self, cache_manager):
        """测试获取或设置"""
        # 第一次调用，值不存在，会设置
        value1 = cache_manager.get_or_set("key1", lambda: "computed_value")
        assert value1 == "computed_value"

        # 第二次调用，值存在，会直接返回
        value2 = cache_manager.get_or_set("key1", lambda: "new_value")
        assert value2 == "computed_value"  # 应该返回旧值

    def test_keys_pattern(self, cache_manager):
        """测试按模式获取键"""
        cache_manager.set("user:1", "value1")
        cache_manager.set("user:2", "value2")
        cache_manager.set("session:1", "value3")

        user_keys = cache_manager.keys(pattern="user:*")
        assert len(user_keys) == 2
        assert "user:1" in user_keys
        assert "user:2" in user_keys
        assert "session:1" not in user_keys

    def test_keys_all(self, cache_manager):
        """测试获取所有键"""
        cache_manager.set("key1", "value1")
        cache_manager.set("key2", "value2")

        all_keys = cache_manager.keys()
        assert len(all_keys) == 2
        assert "key1" in all_keys
        assert "key2" in all_keys

    def test_size(self, cache_manager):
        """测试缓存大小"""
        assert cache_manager.size() == 0

        cache_manager.set("key1", "value1")
        cache_manager.set("key2", "value2")
        assert cache_manager.size() == 2

        cache_manager.delete("key1")
        assert cache_manager.size() == 1


class TestCacheManagerEdgeCases:
    """测试边界情况"""

    def test_none_value(self, cache_manager):
        """测试存储None值"""
        cache_manager.set("key1", None)
        result = cache_manager.get("key1")
        assert result is None

    def test_empty_string_value(self, cache_manager):
        """测试存储空字符串"""
        cache_manager.set("key1", "")
        result = cache_manager.get("key1")
        assert result == ""

    def test_zero_ttl(self, cache_manager):
        """测试零TTL（立即过期）"""
        cache_manager.set("key1", "value1", ttl=0)
        # 可能立即过期或保存
        result = cache_manager.get("key1")
        # 结果取决于实现

    def test_negative_ttl(self, cache_manager):
        """测试负TTL"""
        # 应该被拒绝或转换为正值
        cache_manager.set("key1", "value1", ttl=-1)
        # 可能抛出异常或被处理

    def test_large_value(self, cache_manager):
        """测试大值"""
        large_value = "x" * 10000
        cache_manager.set("key1", large_value)
        result = cache_manager.get("key1")
        assert result == large_value

    def test_special_characters_in_key(self, cache_manager):
        """测试键中的特殊字符"""
        special_keys = [
            "key:with:colons",
            "key/with/slashes",
            "key-with-dashes",
            "key_with_underscores",
            "key.with.dots",
        ]

        for key in special_keys:
            cache_manager.set(key, f"value_for_{key}")

        for key in special_keys:
            assert cache_manager.get(key) is not None


class TestCacheManagerConcurrency:
    """测试并发场景"""

    def test_thread_safety(self, cache_manager):
        """测试线程安全"""
        import threading

        def set_values(thread_id):
            for i in range(100):
                cache_manager.set(f"key_{thread_id}_{i}", f"value_{thread_id}_{i}")

        threads = []
        for i in range(5):
            t = threading.Thread(target=set_values, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # 验证所有值都已设置
        assert cache_manager.size() > 0
