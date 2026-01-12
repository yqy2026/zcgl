"""
核心模块
提供配置管理、缓存等核心功能

注意：使用延迟导入以避免在测试收集时过早初始化 Settings
"""
from typing import Any


def __getattr__(name: str) -> Any:
    """延迟导入配置，避免在模块导入时立即初始化 Settings"""
    if name == "settings":
        from .config import settings as _settings  # noqa: F401

        return _settings
    elif name == "validate_config":
        from .config import validate_config as _validate_config  # noqa: F401

        return _validate_config
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["settings", "validate_config"]
