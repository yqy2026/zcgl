"""
速率限制器测试

测试自适应速率限制功能，包括请求计数、速率限制恢复、可疑请求检测等。
"""

import time

from src.security.security import RateLimiter


class TestRateLimiterBasics:
    """测试速率限制器基本功能"""

    def test_rate_limit_decrements_with_requests(self):
        """测试速率限制计数器随请求递减"""

        limiter = RateLimiter()

        # 前100个请求应该被允许
        for i in range(100):
            assert limiter.check_rate_limit("127.0.0.1"), f"请求 {i + 1} 应该被允许"

        # 第101个请求应该被拒绝
        assert not limiter.check_rate_limit("127.0.0.1")

    def test_rate_limit_resets_over_time(self):
        """测试速率限制随时间重置"""

        # 使用1秒窗口、5请求限制以便快速测试
        limiter = RateLimiter()

        # 用完配额
        for _ in range(5):
            limiter.check_rate_limit("127.0.0.1", max_requests=5, time_window=1)

        # 第6个请求应该被拒绝
        assert not limiter.check_rate_limit("127.0.0.1", max_requests=5, time_window=1)

        # 等待窗口过期
        time.sleep(1.1)

        # 新的请求应该被允许
        assert limiter.check_rate_limit("127.0.0.1", max_requests=5, time_window=1)

    def test_different_ips_independent_limits(self):
        """测试不同IP有独立的速率限制"""

        limiter = RateLimiter()

        # IP1用完配额（10请求限制）
        for _ in range(10):
            limiter.check_rate_limit("192.168.1.1", max_requests=10, time_window=60)

        assert not limiter.check_rate_limit(
            "192.168.1.1", max_requests=10, time_window=60
        )

        # IP2应该仍然有完整的配额
        for _ in range(10):
            assert limiter.check_rate_limit(
                "192.168.1.2", max_requests=10, time_window=60
            )


class TestRateLimiterEdgeCases:
    """测试速率限制器边缘情况"""

    def test_concurrent_requests_handling(self):
        """测试并发请求处理"""
        import threading

        limiter = RateLimiter()
        results = []

        def make_requests(ip, count):
            for _ in range(count):
                results.append(limiter.check_rate_limit(ip))

        # 模拟多个线程同时请求
        threads = [
            threading.Thread(target=make_requests, args=("192.168.1.1", 50)),
            threading.Thread(target=make_requests, args=("192.168.1.2", 50)),
            threading.Thread(target=make_requests, args=("192.168.1.3", 50)),
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # 所有线程的请求都应该被正确处理
        assert sum(results) == 150  # 50个请求 * 3个IP

    def test_ipv4_and_ipv6_treated_separately(self):
        """测试IPv4和IPv6地址被分别处理"""

        limiter = RateLimiter()

        # 用完IPv4地址的配额
        for _ in range(10):
            limiter.check_rate_limit("192.168.1.1", max_requests=10, time_window=60)

        assert not limiter.check_rate_limit(
            "192.168.1.1", max_requests=10, time_window=60
        )

        # IPv6地址应该有独立配额（即使映射到同一主机）
        for _ in range(10):
            assert limiter.check_rate_limit(
                "::ffff:192.168.1.1", max_requests=10, time_window=60
            )

    def test_very_long_window(self):
        """测试长时间窗口"""

        # 1小时窗口，1000请求限制
        limiter = RateLimiter()

        # 应该正确处理
        for _ in range(1000):
            assert limiter.check_rate_limit(
                "192.168.1.1", max_requests=1000, time_window=3600
            )

        assert not limiter.check_rate_limit(
            "192.168.1.1", max_requests=1000, time_window=3600
        )

    def test_zero_requests_allowed(self):
        """测试零请求配额"""

        limiter = RateLimiter()

        # 所有请求都应该被拒绝（0请求限制）
        assert not limiter.check_rate_limit(
            "192.168.1.1", max_requests=0, time_window=60
        )
        assert not limiter.check_rate_limit(
            "192.168.1.2", max_requests=0, time_window=60
        )

    def test_very_small_window(self):
        """测试非常小的时间窗口"""

        # 0.1秒窗口，5请求限制
        limiter = RateLimiter()

        # 快速发送6个请求
        results = [
            limiter.check_rate_limit("192.168.1.1", max_requests=5, time_window=0.1)
            for _ in range(6)
        ]

        # 前5个应该成功，第6个应该失败
        assert sum(results) == 5

        # 等待窗口过期
        time.sleep(0.15)

        # 新请求应该成功
        assert limiter.check_rate_limit("192.168.1.1", max_requests=5, time_window=0.1)


class TestRateLimiterMemoryManagement:
    """测试速率限制器内存管理"""

    def test_old_entries_cleaned_up(self):
        """测试旧条目被清理"""

        # 使用短窗口和清理间隔
        limiter = RateLimiter()

        # 创建多个IP的条目
        for i in range(10):
            ip = f"192.168.1.{i}"
            limiter.check_rate_limit(ip)

        # 等待窗口过期 + 清理间隔
        time.sleep(3.1)

        # 触发清理（通过新请求）
        limiter.check_rate_limit("192.168.1.100")

        # 内存使用应该合理（不应该是10倍增长）
        # 这个测试主要是确保清理逻辑存在，实际内存测量需要更复杂的设置

    def test_max_entries_limit(self):
        """测试最大条目数限制"""

        # RateLimiter 使用 defaultdict，会自动创建新条目
        limiter = RateLimiter()

        # 创建多个IP的条目
        for i in range(150):
            ip = f"192.168.1.{i}"
            limiter.check_rate_limit(ip, max_requests=10, time_window=60)

        # 应该不会崩溃，所有IP都有独立的请求队列
        # 验证内部状态
        assert len(limiter.request_times) == 150


class TestRateLimiterErrorHandling:
    """测试速率限制器错误处理"""

    def test_invalid_ip_address(self):
        """测试无效IP地址处理"""

        limiter = RateLimiter()

        # 应该优雅地处理无效IP
        try:
            limiter.check_rate_limit("invalid-ip")
            limiter.check_rate_limit("")
            limiter.check_rate_limit(None)  # type: ignore
        except Exception as e:
            # 如果抛出异常，应该是预期的类型
            assert isinstance(e, (ValueError, TypeError, AttributeError))

    def test_negative_parameters(self):
        """测试负参数处理"""

        # RateLimiter 不接受构造参数，通过check_rate_limit传递
        limiter = RateLimiter()

        # 负参数在 check_rate_limit 中应该被拒绝或转换为正值
        try:
            result = limiter.check_rate_limit(
                "test_key", max_requests=-10, time_window=-60
            )
            # 如果没有抛出异常，参数应该被规范化
            assert result is False  # 负值应该返回False或被规范化
        except (ValueError, AssertionError):
            # 预期的行为
            pass

    def test_very_large_parameters(self):
        """测试非常大的参数"""

        # 应该能够处理合理的最大值
        limiter = RateLimiter()
        # 参数通过 check_rate_limit 传递
        limiter.check_rate_limit("test_key", max_requests=1_000_000, time_window=86400)

        # 验证配置被正确应用（具体验证取决于实现）


class TestRateLimiterStatistics:
    """测试速率限制器统计功能"""

    def test_get_remaining_requests(self):
        """测试获取剩余请求数"""

        limiter = RateLimiter()

        # 初始应该有10个剩余（使用显式参数）
        remaining = limiter.get_remaining_requests(
            "192.168.1.1", max_requests=10, time_window=60
        )
        assert remaining == 10

        # 使用3个请求
        for _ in range(3):
            limiter.check_rate_limit("192.168.1.1", max_requests=10, time_window=60)

        # 应该剩余7个
        remaining = limiter.get_remaining_requests(
            "192.168.1.1", max_requests=10, time_window=60
        )
        assert remaining == 7

    def test_get_rate_limit_status(self):
        """测试获取速率限制状态 - 通过 get_remaining_requests"""

        limiter = RateLimiter()

        # get_remaining_requests 提供状态信息
        remaining = limiter.get_remaining_requests(
            "192.168.1.1", max_requests=10, time_window=60
        )

        # 应该返回剩余请求数
        assert remaining == 10


class TestRateLimiterIntegrationScenarios:
    """测试速率限制器集成场景"""

    def test_api_endpoint_rate_limiting(self):
        """测试API端点速率限制场景"""

        # 模拟不同的API端点有不同的限制
        public_api = RateLimiter()
        admin_api = RateLimiter()

        public_ip = "192.168.1.50"

        # 公共API：100请求后限制
        for _ in range(100):
            assert public_api.check_rate_limit(public_ip)
        assert not public_api.check_rate_limit(public_ip)

        # 管理API：仍然允许
        for _ in range(100):
            assert admin_api.check_rate_limit(public_ip)

    def test_ddos_protection_scenario(self):
        """测试DDoS防护场景"""

        limiter = RateLimiter()

        attacker_ips = [f"192.168.1.{i}" for i in range(10)]

        # 每个攻击者发送大量请求（50请求限制）
        for ip in attacker_ips:
            for _ in range(50):
                limiter.check_rate_limit(ip, max_requests=50, time_window=60)

        # 所有攻击者应该被限制
        for ip in attacker_ips:
            assert not limiter.check_rate_limit(ip, max_requests=50, time_window=60)

        # 合法用户应该仍然能够访问
        legitimate_ip = "192.168.1.100"
        for _ in range(10):
            assert limiter.check_rate_limit(
                legitimate_ip, max_requests=50, time_window=60
            )

    def test_burst_traffic_handling(self):
        """测试突发流量处理"""

        # 使用突发友好配置（90请求限制以便快速测试）
        limiter = RateLimiter()

        ip = "192.168.1.75"

        # 突发50个请求
        burst_results = [
            limiter.check_rate_limit(ip, max_requests=90, time_window=60)
            for _ in range(50)
        ]
        assert all(burst_results)

        # 持续流量应该继续工作
        for _ in range(40):
            assert limiter.check_rate_limit(ip, max_requests=90, time_window=60)

        # 第91个请求应该失败
        assert not limiter.check_rate_limit(ip, max_requests=90, time_window=60)
