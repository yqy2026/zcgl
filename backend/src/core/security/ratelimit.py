"""
增强的速率限制器
提供基于令牌桶算法的请求频率限制功能
"""

import time
import logging
from collections import defaultdict
from typing import Dict, Tuple
from threading import Lock

from ..config_manager import get_config
from ..logging_security import security_auditor

logger = logging.getLogger(__name__)


class TokenBucketRateLimiter:
    """基于令牌桶算法的速率限制器"""
    
    def __init__(self):
        self.buckets: Dict[str, Tuple[float, float]] = defaultdict(lambda: (0.0, 0.0))  # (tokens, last_time)
        self.lock = Lock()
        self.config = get_config("rate_limit", {})
        
    def _get_bucket_config(self, key: str) -> Tuple[float, float]:
        """
        获取桶配置
        
        Args:
            key: 限制键
            
        Returns:
            Tuple[float, float]: (容量, 令牌生成速率)
        """
        # 根据不同的键类型设置不同的限制
        if ":pdf_import" in key:
            # PDF导入: 每分钟最多5个请求，桶容量为10
            return (10.0, 5.0 / 60.0)  # 容量10, 每秒生成5/60个令牌
        elif ":excel" in key:
            # Excel操作: 每分钟最多10个请求，桶容量为20
            return (20.0, 10.0 / 60.0)
        elif ":post" in key:
            # POST请求: 每分钟最多30个请求，桶容量为50
            return (50.0, 30.0 / 60.0)
        else:
            # 默认: 每分钟最多100个请求，桶容量为200
            return (200.0, 100.0 / 60.0)
    
    def check_rate_limit(self, key: str) -> bool:
        """
        检查请求是否超过频率限制
        
        Args:
            key: 限制键（如IP地址或用户ID）
            
        Returns:
            bool: 是否允许请求
        """
        with self.lock:
            current_time = time.time()
            tokens, last_time = self.buckets[key]
            
            # 获取桶配置
            capacity, rate = self._get_bucket_config(key)
            
            # 计算新增的令牌数
            tokens += (current_time - last_time) * rate
            tokens = min(tokens, capacity)  # 不能超过桶容量
            
            if tokens >= 1.0:
                # 有足够的令牌，消耗一个令牌
                tokens -= 1.0
                self.buckets[key] = (tokens, current_time)
                return True
            else:
                # 没有足够的令牌，拒绝请求
                self.buckets[key] = (tokens, current_time)
                security_auditor.log_security_event(
                    event_type="RATE_LIMIT_EXCEEDED",
                    message=f"Rate limit exceeded for {key}",
                    details={
                        "key": key,
                        "available_tokens": tokens,
                        "bucket_capacity": capacity,
                        "token_rate": rate,
                    },
                )
                return False
    
    def get_remaining_tokens(self, key: str) -> float:
        """
        获取剩余令牌数
        
        Args:
            key: 限制键
            
        Returns:
            float: 剩余令牌数
        """
        with self.lock:
            current_time = time.time()
            tokens, last_time = self.buckets[key]
            
            # 获取桶配置
            capacity, rate = self._get_bucket_config(key)
            
            # 计算新增的令牌数
            tokens += (current_time - last_time) * rate
            tokens = min(tokens, capacity)  # 不能超过桶容量
            
            return tokens


class AdaptiveRateLimiter:
    """自适应速率限制器"""
    
    def __init__(self):
        self.token_bucket = TokenBucketRateLimiter()
        self.suspicious_ips = defaultdict(int)  # 记录可疑IP的违规次数
        self.blocked_ips = {}  # 记录被临时封禁的IP
        self.config = get_config("adaptive_rate_limit", {})
        
    def check_rate_limit(self, key: str, is_suspicious: bool = False) -> bool:
        """
        检查请求是否超过频率限制（自适应）
        
        Args:
            key: 限制键（如IP地址或用户ID）
            is_suspicious: 是否为可疑请求
            
        Returns:
            bool: 是否允许请求
        """
        # 检查IP是否被封禁
        if self._is_ip_blocked(key):
            return False
            
        # 如果是可疑请求，增加违规计数
        if is_suspicious:
            self.suspicious_ips[key] += 1
            # 如果违规次数过多，临时封禁
            if self.suspicious_ips[key] >= self.config.get("max_suspicious_requests", 5):
                self._block_ip(key)
                return False
        
        # 使用令牌桶算法检查速率限制
        return self.token_bucket.check_rate_limit(key)
    
    def _is_ip_blocked(self, ip: str) -> bool:
        """检查IP是否被封禁"""
        if ip in self.blocked_ips:
            block_time = self.blocked_ips[ip]
            # 封禁时间默认为1小时
            block_duration = self.config.get("block_duration", 3600)
            if time.time() - block_time < block_duration:
                return True
            else:
                # 解除封禁
                del self.blocked_ips[ip]
                if ip in self.suspicious_ips:
                    del self.suspicious_ips[ip]
        return False
    
    def _block_ip(self, ip: str):
        """封禁IP"""
        self.blocked_ips[ip] = time.time()
        security_auditor.log_security_event(
            event_type="IP_BLOCKED",
            message=f"IP blocked due to suspicious activity: {ip}",
            details={
                "ip": ip,
                "suspicious_count": self.suspicious_ips[ip],
                "block_time": time.time(),
            },
        )
    
    def report_suspicious_activity(self, key: str):
        """报告可疑活动"""
        self.suspicious_ips[key] += 1
        if self.suspicious_ips[key] >= self.config.get("max_suspicious_requests", 5):
            self._block_ip(key)


# 全局实例
token_bucket_limiter = TokenBucketRateLimiter()
adaptive_limiter = AdaptiveRateLimiter()


if __name__ == "__main__":
    # 测试速率限制器
    limiter = TokenBucketRateLimiter()
    
    # 测试基本功能
    test_key = "127.0.0.1:test"
    allowed_count = 0
    for i in range(20):
        if limiter.check_rate_limit(test_key):
            allowed_count += 1
        time.sleep(0.1)  # 100ms间隔
    
    print(f"Allowed {allowed_count} requests out of 20")