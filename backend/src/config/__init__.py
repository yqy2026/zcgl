"""
Deprecated compatibility shim for legacy imports.
Use src.core.config instead.
"""

from __future__ import annotations

import warnings

from src.core.config import (
    Settings,
    settings,
    validate_config,
)

warnings.warn(
    "src.config is deprecated; use src.core.config instead",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["Settings", "settings", "validate_config"]
