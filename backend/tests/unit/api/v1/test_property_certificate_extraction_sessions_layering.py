"""Authorization boundaries for reviewed property-certificate extraction sessions."""

from __future__ import annotations

import re
from pathlib import Path


def test_existing_attachment_review_uses_certificate_read_authorization() -> None:
    """Reviewing an existing attachment must not require create authorization."""
    from src.api.v1 import property_certificate_extraction_sessions as module

    module_source = Path(module.__file__).read_text(encoding="utf-8")
    expected_patterns = [
        r"async def create_existing_property_certificate_review_session[\s\S]*?action=\"read\"[\s\S]*?resource_id=\"\{certificate_id\}\"",
        r"async def confirm_existing_property_certificate_review_session[\s\S]*?action=\"read\"[\s\S]*?resource_id=\"\{certificate_id\}\"",
    ]
    for pattern in expected_patterns:
        assert re.search(pattern, module_source), pattern
