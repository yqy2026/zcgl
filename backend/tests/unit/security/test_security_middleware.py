"""
Security middleware helper tests.
"""

import pytest
from starlette.requests import Request

from src.core.exception_handler import PermissionDeniedError
from src.security.security_middleware import SecurityMiddleware


def _make_request(ip: str, user_agent: str = "test-agent-123") -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(b"user-agent", user_agent.encode("latin-1"))],
        "client": (ip, 12345),
        "query_string": b"",
    }
    return Request(scope)


@pytest.mark.asyncio
async def test_security_middleware_disabled_skips_checks():
    middleware = SecurityMiddleware(
        {
            "enabled": False,
            "ip_blacklist": ["203.0.113.1"],
            "rate_limit_enabled": True,
        }
    )
    request = _make_request("203.0.113.1")
    assert await middleware.validate_request(request) is True


@pytest.mark.asyncio
async def test_security_middleware_ip_blacklist_blocks():
    middleware = SecurityMiddleware(
        {
            "ip_blacklist": ["203.0.113.2"],
            "ip_blacklist_enabled": True,
        }
    )
    request = _make_request("203.0.113.2")
    with pytest.raises(PermissionDeniedError):
        await middleware.validate_request(request)
