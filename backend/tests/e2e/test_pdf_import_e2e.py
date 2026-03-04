"""
End-to-end tests for PDF import endpoints.
"""

import io

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.e2e

_MINIMAL_PDF_BYTES = (
    b"%PDF-1.4\n"
    b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    b"2 0 obj\n<< /Type /Pages /Count 0 >>\nendobj\n"
    b"trailer\n<< /Root 1 0 R >>\n%%EOF"
)


def test_pdf_upload_success_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
) -> None:
    response = authenticated_client.post(
        "/api/v1/pdf-import/upload",
        files={
            "file": (
                "contract.pdf",
                io.BytesIO(_MINIMAL_PDF_BYTES),
                "application/pdf",
            )
        },
        data={
            "prefer_markitdown": "false",
            "force_method": "text",
        },
        headers=csrf_headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload.get("success") is True
    session_id = payload.get("session_id")
    assert isinstance(session_id, str)
    assert session_id.strip() != ""
    assert isinstance(payload.get("estimated_time"), str)


def test_pdf_upload_same_file_twice_returns_distinct_sessions_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
) -> None:
    first_response = authenticated_client.post(
        "/api/v1/pdf-import/upload",
        files={
            "file": (
                "contract.pdf",
                io.BytesIO(_MINIMAL_PDF_BYTES),
                "application/pdf",
            )
        },
        headers=csrf_headers,
    )
    second_response = authenticated_client.post(
        "/api/v1/pdf-import/upload",
        files={
            "file": (
                "contract.pdf",
                io.BytesIO(_MINIMAL_PDF_BYTES),
                "application/pdf",
            )
        },
        headers=csrf_headers,
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    first_payload = first_response.json()
    second_payload = second_response.json()

    assert first_payload.get("success") is True
    assert second_payload.get("success") is True

    first_session_id = first_payload.get("session_id")
    second_session_id = second_payload.get("session_id")
    assert isinstance(first_session_id, str)
    assert isinstance(second_session_id, str)
    assert first_session_id.strip() != ""
    assert second_session_id.strip() != ""
    assert first_session_id != second_session_id


def test_pdf_upload_accepts_trimmed_force_method_value_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
) -> None:
    response = authenticated_client.post(
        "/api/v1/pdf-import/upload",
        files={
            "file": (
                "contract.pdf",
                io.BytesIO(_MINIMAL_PDF_BYTES),
                "application/pdf",
            )
        },
        data={"force_method": " text "},
        headers=csrf_headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload.get("success") is True
    session_id = payload.get("session_id")
    assert isinstance(session_id, str)
    assert session_id.strip() != ""


def test_pdf_upload_rejects_non_pdf_file_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
) -> None:
    response = authenticated_client.post(
        "/api/v1/pdf-import/upload",
        files={
            "file": (
                "contract.txt",
                io.BytesIO(b"not-a-pdf"),
                "text/plain",
            )
        },
        headers=csrf_headers,
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload.get("success") is False
    error = payload.get("error", {})
    assert isinstance(error, dict)
    assert error.get("code") == "VALIDATION_ERROR"


def test_pdf_upload_rejects_oversized_file_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.api.v1.documents import pdf_upload as pdf_upload_module

    monkeypatch.setattr(pdf_upload_module, "DEFAULT_MAX_FILE_SIZE", 1024)

    oversized_pdf_bytes = _MINIMAL_PDF_BYTES + (b"0" * 2048)
    response = authenticated_client.post(
        "/api/v1/pdf-import/upload",
        files={
            "file": (
                "oversized.pdf",
                io.BytesIO(oversized_pdf_bytes),
                "application/pdf",
            )
        },
        headers=csrf_headers,
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload.get("success") is False
    error = payload.get("error", {})
    assert isinstance(error, dict)
    assert error.get("code") == "INVALID_REQUEST"


def test_pdf_upload_requires_csrf_header_e2e(
    authenticated_client: TestClient,
) -> None:
    response = authenticated_client.post(
        "/api/v1/pdf-import/upload",
        files={
            "file": (
                "contract.pdf",
                io.BytesIO(_MINIMAL_PDF_BYTES),
                "application/pdf",
            )
        },
    )

    assert response.status_code == 403
    payload = response.json()
    assert payload.get("success") is False
    assert payload.get("error_type") == "csrf_missing"


def test_pdf_upload_rejects_invalid_force_method_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
) -> None:
    response = authenticated_client.post(
        "/api/v1/pdf-import/upload",
        files={
            "file": (
                "contract.pdf",
                io.BytesIO(_MINIMAL_PDF_BYTES),
                "application/pdf",
            )
        },
        data={"force_method": "invalid"},
        headers=csrf_headers,
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload.get("success") is False
    error = payload.get("error", {})
    assert isinstance(error, dict)
    assert error.get("code") == "INVALID_REQUEST"


def test_pdf_upload_can_succeed_after_invalid_force_method_retry_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
) -> None:
    failed_response = authenticated_client.post(
        "/api/v1/pdf-import/upload",
        files={
            "file": (
                "contract.pdf",
                io.BytesIO(_MINIMAL_PDF_BYTES),
                "application/pdf",
            )
        },
        data={"force_method": "invalid"},
        headers=csrf_headers,
    )
    success_response = authenticated_client.post(
        "/api/v1/pdf-import/upload",
        files={
            "file": (
                "contract.pdf",
                io.BytesIO(_MINIMAL_PDF_BYTES),
                "application/pdf",
            )
        },
        data={"force_method": "text"},
        headers=csrf_headers,
    )

    assert failed_response.status_code == 400
    failed_payload = failed_response.json()
    assert failed_payload.get("success") is False

    assert success_response.status_code == 200
    success_payload = success_response.json()
    assert success_payload.get("success") is True
    session_id = success_payload.get("session_id")
    assert isinstance(session_id, str)
    assert session_id.strip() != ""
