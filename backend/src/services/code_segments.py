"""Shared code-segment helpers for business identifiers."""

import re

_CODE_SEGMENT_RE = re.compile(r"[A-Z0-9]")


def build_party_code_segment(party_code: str, *, length: int = 8) -> str:
    """Derive a stable uppercase alphanumeric segment from a Party code."""
    upper = str(party_code or "").upper()
    chars = _CODE_SEGMENT_RE.findall(upper)
    segment = "".join(chars)[:length]
    return segment.ljust(length, "X")
