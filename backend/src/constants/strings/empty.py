"""
Empty string constant.

Provides a centralized constant for empty string comparisons to improve
code readability and maintainability.
"""

from typing import Final

EMPTY_STRING: Final[str] = ""

# Legacy compatibility alias (deprecated, will be removed in v2.0)
EMPTY = EMPTY_STRING
