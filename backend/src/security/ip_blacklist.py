"""
IP blacklist management.
"""

from __future__ import annotations

from collections import defaultdict
from threading import Lock
from time import time
from typing import Any

from .logging_security import security_auditor

class IPBlacklistManager:
    """IP黑名单管理器"""

    def __init__(self) -> None:
        self.config: dict[str, Any] = {}  # TODO: 未来可添加IP黑名单配置
        self.blacklist: set[str] = set(self.config.get("blacklist", []))
        self.auto_block_enabled = self.config.get("auto_block_enabled", True)
        self.auto_block_threshold = self.config.get("auto_block_threshold", 10)
        self.auto_block_duration = self.config.get("auto_block_duration", 3600)
        self.blocked_ips: dict[str, float] = {}
        self.suspicious_ips: dict[str, int] = defaultdict(int)
        self.lock = Lock()

    def is_blacklisted(self, ip: str) -> bool:
        """检查IP是否在黑名单中"""
        with self.lock:
            if ip in self.blacklist:
                return True

            if ip in self.blocked_ips:
                # 检查封禁是否过期
                if time() - self.blocked_ips[ip] < self.auto_block_duration:
                    return True
                else:
                    del self.blocked_ips[ip]

            return False

    def add_to_blacklist(self, ip: str) -> None:
        """添加IP到黑名单"""
        with self.lock:
            self.blacklist.add(ip)
            self.config["blacklist"] = list(self.blacklist)

    def remove_from_blacklist(self, ip: str) -> None:
        """从黑名单移除IP"""
        with self.lock:
            self.blacklist.discard(ip)
            self.config["blacklist"] = list(self.blacklist)

    def report_suspicious_activity(self, ip: str) -> None:
        """报告可疑活动"""
        with self.lock:
            self.suspicious_ips[ip] += 1
            if (
                self.auto_block_enabled
                and self.suspicious_ips[ip] >= self.auto_block_threshold
            ):
                self.blocked_ips[ip] = time()
                security_auditor.log_security_event(
                    event_type="IP_AUTO_BLOCKED",
                    message=f"IP auto-blocked due to suspicious activity: {ip}",
                    details={
                        "ip": ip,
                        "suspicious_count": self.suspicious_ips[ip],
                        "threshold": self.auto_block_threshold,
                    },
                )
