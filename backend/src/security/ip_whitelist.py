"""
Backward-compatible re-export for IP whitelist.

Prefer importing from src.core.ip_whitelist.
"""

from src.core.ip_whitelist import IPRange, IPWhitelistManager, ip_whitelist

__all__ = ["IPRange", "IPWhitelistManager", "ip_whitelist"]
