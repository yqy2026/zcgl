"""
Rate limiting utilities.
"""

from __future__ import annotations

from collections import defaultdict, deque
from threading import Lock
from time import time
from typing import Any

from .logging_security import security_auditor

class RateLimitConfig:
    """速率限制配置"""

    # 默认限制配置
    DEFAULT_LIMITS = {
        "api": {"requests": 1000, "window": 3600},  # 1000次/小时
        "upload": {"requests": 50, "window": 3600},  # 50次/小时
        "auth": {"requests": 10, "window": 300},  # 10次/5分钟
        "search": {"requests": 100, "window": 3600},  # 100次/小时
    }

    # IP白名单（无限制）
    WHITELIST_IPS: set[str] = set()

    # IP黑名单（完全封禁）
    BLACKLIST_IPS: set[str] = set()

    # 自动封禁阈值
    AUTO_BLOCK_THRESHOLD = 100

    # 自动封禁持续时间（秒）
    AUTO_BLOCK_DURATION = 3600


class RateLimiter:
    """基础速率限制器"""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or RateLimitConfig.DEFAULT_LIMITS
        self.request_times: dict[str, deque[float]] = defaultdict(deque)
        self.blocked_ips: dict[str, float] = {}
        self.lock = Lock()

    def _get_limit_config(self, endpoint: str) -> dict[str, int]:
        """获取端点限制配置"""
        return self.config.get(endpoint, self.config["api"])

    def check_rate_limit(self, client_ip: str, endpoint: str = "api") -> bool:
        """检查速率限制"""
        if client_ip in RateLimitConfig.WHITELIST_IPS:
            return True

        if client_ip in RateLimitConfig.BLACKLIST_IPS:
            return False

        current_time = time()

        with self.lock:
            # 检查自动封禁
            if client_ip in self.blocked_ips:
                if (
                    current_time - self.blocked_ips[client_ip]
                    < RateLimitConfig.AUTO_BLOCK_DURATION
                ):
                    return False
                else:
                    del self.blocked_ips[client_ip]

            # 获取限制配置
            limit_config = self._get_limit_config(endpoint)
            max_requests = limit_config["requests"]
            window = limit_config["window"]

            # 清理过期请求记录
            request_queue = self.request_times[client_ip]
            while request_queue and current_time - request_queue[0] > window:
                request_queue.popleft()

            # 检查是否超过限制
            if len(request_queue) >= max_requests:
                # 检查是否需要自动封禁
                if len(request_queue) >= RateLimitConfig.AUTO_BLOCK_THRESHOLD:
                    self.blocked_ips[client_ip] = current_time
                    security_auditor.log_security_event(
                        event_type="IP_AUTO_BLOCKED",
                        message=f"IP auto-blocked due to excessive requests: {client_ip}",
                        details={
                            "ip": client_ip,
                            "request_count": len(request_queue),
                            "threshold": RateLimitConfig.AUTO_BLOCK_THRESHOLD,
                        },
                    )
                return False

            # 记录请求
            request_queue.append(current_time)
            return True


class TokenBucketRateLimiter:
    """令牌桶限流器"""

    def __init__(self, rate: float = 10.0, capacity: int = 100) -> None:
        self.rate = rate  # 令牌生成速率 (tokens/sec)
        self.capacity = capacity  # 桶容量
        self.tokens: float = float(capacity)  # 当前令牌数
        self.last_update = time()
        self.lock = Lock()

    def allow_request(self) -> bool:
        """检查是否允许请求"""
        with self.lock:
            now = time()
            # 计算新增令牌
            elapsed = now - self.last_update
            new_tokens = elapsed * self.rate
            self.tokens = min(self.capacity, self.tokens + new_tokens)
            self.last_update = now

            if self.tokens >= 1:
                self.tokens -= 1
                return True

            return False


class AdaptiveRateLimiter:
    """自适应速率限制器"""

    def __init__(self) -> None:
        self.config: dict[str, Any] = {}  # TODO: 未来可添加自适应限流配置
        self.request_stats: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"count": 0, "errors": 0, "last_reset": time()}
        )
        self.lock = Lock()

    def check_rate_limit(self, client_ip: str, is_suspicious: bool = False) -> bool:
        """基于错误率的自适应限流"""
        with self.lock:
            stats = self.request_stats[client_ip]
            current_time = time()

            # 每分钟重置统计
            if current_time - stats["last_reset"] > 60:
                stats["count"] = 0
                stats["errors"] = 0
                stats["last_reset"] = current_time

            stats["count"] += 1

            # 计算错误率
            error_rate = stats["errors"] / stats["count"] if stats["count"] > 0 else 0

            # 如果错误率过高，限制请求
            if is_suspicious:
                max_error_rate = self.config.get("suspicious_max_error_rate", 0.1)
            else:
                max_error_rate = self.config.get("max_error_rate", 0.3)
            if error_rate > max_error_rate:
                return False

            return True

    def record_error(self, client_ip: str) -> None:
        """记录错误"""
        with self.lock:
            self.request_stats[client_ip]["errors"] += 1


class RequestLimiter:
    """请求限制器"""

    def __init__(self) -> None:
        self.config: dict[str, Any] = {}  # TODO: 未来可添加请求限制配置
        self.request_counts: dict[str, dict[str, float]] = defaultdict(
            lambda: {"count": 0.0, "last_reset": time()}
        )
        self.lock = Lock()

    def check_request_limit(self, key: str) -> bool:
        """检查请求限制"""
        with self.lock:
            current_time = time()
            request_info = self.request_counts[key]

            # 每分钟重置
            if current_time - request_info["last_reset"] > 60:
                request_info["count"] = 0
                request_info["last_reset"] = current_time

            request_info["count"] += 1

            # 获取限制配置
            max_requests_raw = self.config.get("max_requests_per_minute", 100)
            max_requests = (
                float(max_requests_raw)
                if isinstance(max_requests_raw, (int, float))
                else 100.0
            )

            return request_info["count"] <= max_requests

token_bucket_limiter = TokenBucketRateLimiter()
adaptive_limiter = AdaptiveRateLimiter()
