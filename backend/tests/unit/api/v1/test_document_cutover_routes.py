"""Public route retirement guards for the document-extraction cutover."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from src.main import app


def test_legacy_document_and_prompt_routers_are_not_included() -> None:
    from src.api.v1 import __file__ as package_file

    source = Path(package_file).read_text(encoding="utf-8")
    assert "pdf_import_router" not in source
    assert "pdf_batch_router" not in source
    assert "llm_prompts_router" not in source


def test_legacy_property_certificate_import_endpoints_are_not_registered() -> None:
    from src.api.v1.assets import property_certificate as module

    source = Path(module.__file__).read_text(encoding="utf-8")
    assert '@router.post("/upload"' not in source
    assert '@router.post("/confirm-import"' not in source


def test_only_unified_extraction_session_routes_are_public() -> None:
    expected_paths = {
        "/api/v1/extraction-sessions",
        "/api/v1/document-extraction/capabilities",
        "/api/v1/extraction-sessions/{session_id}",
        "/api/v1/extraction-sessions/{session_id}/confirm",
        "/api/v1/extraction-sessions/{session_id}/cancel",
    }
    exposed_paths = {
        route.path
        for route in app.routes
        if "extraction-sessions" in getattr(route, "path", "")
        or "document-extraction" in getattr(route, "path", "")
    }

    assert exposed_paths == expected_paths


def test_retired_document_routes_return_not_found() -> None:
    """Retired routes must be unreachable even when no authentication is supplied."""
    retired_paths = [
        "/api/v1/pdf-import/info",
        "/api/v1/pdf-import/batch/health",
        "/api/v1/pdf-import/performance/realtime",
        "/api/v1/pdf-import/test_system",
        "/api/v1/llm-prompts/llm-prompts/",
        "/api/v1/property-certificate-extraction-sessions/missing",
        "/api/v1/assets/property-certificates/upload",
    ]

    with TestClient(app) as client:
        for path in retired_paths:
            response = client.get(path)
            assert response.status_code == 404, path
