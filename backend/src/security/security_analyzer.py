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

from .logging_security import security_auditor

class SecurityAnalyzer:
    """安全分析器"""

    def __init__(self) -> None:
        self.config: dict[str, Any] = {}  # TODO: 未来可添加安全分析配置
        self.suspicious_patterns = [
            r"<script",
            r"javascript:",
            r"vbscript:",
            r"onload=",
            r"onerror=",
            r"document\.cookie",
            r"eval\(",
            r"alert\(",
            r"window\.",
            r"select\s+.*\s+from",
            r"union\s+select",
            r"drop\s+table",
            r"delete\s+from",
            r"insert\s+into",
            r"update\s+.*\s+set",
        ]
        self.suspicious_ips: dict[str, int] = defaultdict(int)
        self.blocked_ips: dict[str, float] = {}
        self.lock = Lock()

    def analyze_request(self, request: Request) -> bool:
        """分析请求是否安全"""
        client_ip = request.client.host if request.client else "unknown"

        # 检查IP是否被封禁
        if client_ip in self.blocked_ips:
            if time() - self.blocked_ips[client_ip] < 3600:  # 1小时封禁
                return False
            else:
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
        self.suspicious_ips[ip] += 1
        if self.suspicious_ips[ip] >= self.config.get("max_suspicious_requests", 5):
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
        self.blocked_ips[ip] = time()
        security_auditor.log_security_event(
            event_type="IP_BLOCKED",
            message=f"IP blocked due to suspicious activity: {ip}",
            details={
                "ip": ip,
                "suspicious_count": self.suspicious_ips[ip],
                "block_time": time(),
            },
        )

    def report_suspicious_activity(self, key: str) -> None:
        """报告可疑活动"""
        self.suspicious_ips[key] += 1
        if self.suspicious_ips[key] >= self.config.get("max_suspicious_requests", 5):
            self._block_ip(key)
