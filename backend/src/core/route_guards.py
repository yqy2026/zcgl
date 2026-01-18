"""
路由保护装饰器
提供环境感知的端点访问控制，仅在开发环境暴露调试端点
"""

import functools
import os
from collections.abc import Callable
from typing import Any

from .api_errors import not_found


def is_debug_mode() -> bool:
    """检查是否为调试模式"""
    return os.getenv("DEBUG", "false").lower() == "true"


def debug_only(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    装饰器：仅在调试模式下允许访问端点

    在非调试模式(DEBUG!=true)下，返回404 Not Found，
    故意模糊响应以不暴露端点存在。

    用法:
        @router.get("/debug-endpoint")
        @debug_only
        async def my_debug_endpoint():
            ...
    """

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        if not is_debug_mode():
            raise not_found("Not Found")  # 故意模糊响应，不暴露端点存在
        return await func(*args, **kwargs)

    return wrapper


def require_debug_mode(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    同步版本的调试模式装饰器
    用于非async函数
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if not is_debug_mode():
            raise not_found("Not Found")
        return func(*args, **kwargs)

    return wrapper


__all__ = [
    "is_debug_mode",
    "debug_only",
    "require_debug_mode",
]
