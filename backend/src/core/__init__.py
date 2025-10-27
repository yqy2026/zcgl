"""
核心模块
提供配置管理、缓存等核心功能
"""

from .config import settings, validate_config

__all__ = ["settings", "validate_config"]
