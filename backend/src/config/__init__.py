"""
Deprecated compatibility shim for legacy imports.
Use src.core.config instead.
"""

from __future__ import annotations

import warnings

from src.core.config import (
    Settings,
    get_config,
    initialize_config,
    settings,
    validate_config,
)

warnings.warn(
    "src.config is deprecated; use src.core.config instead",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["Settings", "settings", "get_config", "initialize_config", "validate_config"]
