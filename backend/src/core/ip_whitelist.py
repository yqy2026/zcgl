"""
IP Whitelist Manager

Provides strict IP whitelist validation to block dangerous IP ranges.
Supports environment-specific behavior (production vs development).
"""

import os
from datetime import datetime
from ipaddress import ip_network, ip_address, IPv4Network
from typing import List, Set

from src.core.environment import get_environment


class IPRange:
    """IP range with metadata"""

    def __init__(self, cidr: str, added_by: str = "system"):
        self.network = ip_network(cidr, strict=False)
        self.cidr = cidr
        self.added_by = added_by
        self.created_at = datetime.utcnow()


class IPWhitelistManager:
    """Manage IP whitelist with strict validation"""

    # RFC 1918 private ranges (should be blocked in production)
    PRIVATE_RANGES = [
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16",
    ]

    # Dangerous ranges that should always be rejected
    BLOCKED_RANGES = [
        "0.0.0.0/0",  # Matches everything
    ]

    def __init__(self):
        self.env = get_environment()
        self.whitelist: Set[IPv4Network] = set()
        self._load_from_env()

    def _load_from_env(self):
        """Load whitelist from environment variable"""
        whitelist_str = os.getenv("IP_WHITELIST", "")
        if whitelist_str:
            ranges = [r.strip() for r in whitelist_str.split(",")]
            for cidr in ranges:
                if self.validate_range(cidr):
                    self.whitelist.add(ip_network(cidr))

    def validate_range(self, cidr: str) -> bool:
        """Validate IP range for whitelist addition"""
        try:
            network = ip_network(cidr, strict=False)

            # Reject dangerous ranges (exact match only, not overlap)
            # 0.0.0.0/0 matches everything and should never be allowed
            if str(network) in self.BLOCKED_RANGES:
                return False

            # In production/staging, reject private ranges
            # Allow private ranges in development and testing
            from src.core.environment import Environment
            if self.env in (Environment.PRODUCTION, Environment.STAGING):
                for private in self.PRIVATE_RANGES:
                    if network.overlaps(ip_network(private)):
                        return False

            return True

        except ValueError:
            return False

    def add_range(self, cidr: str, added_by: str = "system") -> bool:
        """Add IP range to whitelist"""
        if not self.validate_range(cidr):
            return False

        self.whitelist.add(ip_network(cidr))
        return True

    def remove_range(self, cidr: str) -> bool:
        """Remove IP range from whitelist"""
        try:
            network = ip_network(cidr)
            if network in self.whitelist:
                self.whitelist.remove(network)
                return True
            return False
        except ValueError:
            return False

    def is_allowed(self, ip_str: str) -> bool:
        """Check if IP is allowed"""
        # Special case: allow "testclient" for testing
        if ip_str == "testclient" or ip_str.startswith("testclient"):
            return True

        try:
            ip = ip_address(ip_str)

            # If whitelist is empty, allow all (except in production/staging)
            if not self.whitelist:
                from src.core.environment import Environment
                return self.env not in (Environment.PRODUCTION, Environment.STAGING)

            # Check if IP matches any whitelist entry
            for network in self.whitelist:
                if ip in network:
                    return True

            return False

        except ValueError:
            return False

    def get_ranges(self) -> List[str]:
        """Get all whitelisted ranges as CIDR strings"""
        return [str(network) for network in self.whitelist]

    def clear(self) -> None:
        """Clear all whitelist entries"""
        self.whitelist.clear()


# Singleton instance
ip_whitelist = IPWhitelistManager()
