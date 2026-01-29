"""
API路由模块
"""

from typing import Any

# Lazy import to avoid circular dependencies
# from .v1 import api_router  # noqa: F401

__all__ = ["api_router"]


def __getattr__(name: str) -> Any:
    """延迟导入以避免循环依赖"""
    if name == "api_router":
        from .v1 import api_router

        return api_router
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
