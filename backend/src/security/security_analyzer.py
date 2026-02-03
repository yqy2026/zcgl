"""
Request security analyzer.
"""

from __future__ import annotations

import re
from collections import defaultdict
from threading import Lock
from time import time
from typing import Any

from fastapi import Request

from ..core.config import settings
from .logging_security import security_auditor


class SecurityAnalyzer:
    """安全分析器"""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        base_config: dict[str, Any] = {
            "enabled": settings.SECURITY_ANALYZER_ENABLED,
            "enable_ip_block": settings.SECURITY_ANALYZER_ENABLE_IP_BLOCK,
            "max_suspicious_requests": settings.SECURITY_ANALYZER_MAX_SUSPICIOUS_REQUESTS,
            "block_duration": settings.SECURITY_ANALYZER_BLOCK_DURATION,
            "suspicious_patterns": list(settings.SECURITY_ANALYZER_PATTERNS),
        }
        if config:
            base_config.update(config)

        self.config = base_config
        self.enabled = bool(self.config.get("enabled", True))
        self.enable_ip_block = bool(self.config.get("enable_ip_block", True))
        self.max_suspicious_requests = int(
            self.config.get("max_suspicious_requests", 5)
        )
        self.block_duration = int(self.config.get("block_duration", 3600))
        patterns_value = self.config.get("suspicious_patterns", [])
        if isinstance(patterns_value, str):
            self.suspicious_patterns = [
                item.strip() for item in patterns_value.split(",") if item.strip()
            ]
        elif isinstance(patterns_value, list):
            self.suspicious_patterns = [
                str(item).strip() for item in patterns_value if str(item).strip()
            ]
        else:
            self.suspicious_patterns = []
        self.suspicious_ips: dict[str, int] = defaultdict(int)
        self.blocked_ips: dict[str, float] = {}
        self.lock = Lock()

    def analyze_request(self, request: Request) -> bool:
        """分析请求是否安全"""
        if not self.enabled:
            return True

        client_ip = request.client.host if request.client else "unknown"

        # 检查IP是否被封禁
        if self.enable_ip_block:
            with self.lock:
                if client_ip in self.blocked_ips:
                    if time() - self.blocked_ips[client_ip] < self.block_duration:
                        return False
                    del self.blocked_ips[client_ip]

        # 检查请求路径和参数
        request_data = str(request.url) + str(request.query_params)

        # 检查可疑模式
        for pattern in self.suspicious_patterns:
            if re.search(pattern, request_data, re.IGNORECASE):
                self._report_suspicious_activity(client_ip, pattern)
                return False

        return True

    def _report_suspicious_activity(self, ip: str, pattern: str) -> None:
        """报告可疑活动"""
        with self.lock:
            self.suspicious_ips[ip] += 1
            if self.enable_ip_block and (
                self.suspicious_ips[ip] >= self.max_suspicious_requests
            ):
                self._block_ip(ip)

        security_auditor.log_security_event(
            event_type="SUSPICIOUS_REQUEST",
            message=f"Suspicious request pattern detected: {pattern}",
            details={
                "ip": ip,
                "pattern": pattern,
                "suspicious_count": self.suspicious_ips[ip],
            },
        )

    def _block_ip(self, ip: str) -> None:
        """封禁IP"""
        if not self.enable_ip_block:
            return
        block_time = time()
        self.blocked_ips[ip] = block_time
        security_auditor.log_security_event(
            event_type="IP_BLOCKED",
            message=f"IP blocked due to suspicious activity: {ip}",
            details={
                "ip": ip,
                "suspicious_count": self.suspicious_ips[ip],
                "block_time": block_time,
            },
        )

    def report_suspicious_activity(self, key: str) -> None:
        """报告可疑活动"""
        with self.lock:
            self.suspicious_ips[key] += 1
            if self.enable_ip_block and (
                self.suspicious_ips[key] >= self.max_suspicious_requests
            ):
                self._block_ip(key)
