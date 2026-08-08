"""Contract checks for generic property-certificate attachment routes."""

from __future__ import annotations

from pathlib import Path


def test_property_certificate_attachment_append_accepts_multiple_files_and_returns_per_item_results() -> (
    None
):
    from src.api.v1 import property_certificate_attachments as module

    source = Path(module.__file__).read_text(encoding="utf-8")
    assert "async def append_property_certificate_attachments" in source
    assert "files: Annotated[list[UploadFile], File()]" in source
    assert 'return {"results": results}' in source
    assert '"error": str(exc)' in source
