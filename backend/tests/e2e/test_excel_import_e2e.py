"""
End-to-end tests for rent contract Excel import/export endpoints.
"""

import io

import pytest
from fastapi.testclient import TestClient

from src.api.v1.rent_contracts import excel_ops

pytestmark = pytest.mark.e2e

_XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _skip_when_excel_service_unavailable() -> None:
    if not excel_ops.EXCEL_SERVICE_AVAILABLE or excel_ops.rent_contract_excel_service is None:
        pytest.skip("Excel service is not available in current test environment")


def test_excel_template_download_and_import_empty_template_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
) -> None:
    _skip_when_excel_service_unavailable()

    template_response = authenticated_client.get("/api/v1/rental-contracts/excel/template")
    assert template_response.status_code == 200
    assert _XLSX_CONTENT_TYPE in template_response.headers.get("content-type", "")
    assert template_response.content

    import_response = authenticated_client.post(
        "/api/v1/rental-contracts/excel/import",
        files={
            "file": (
                "rent_contract_template.xlsx",
                io.BytesIO(template_response.content),
                _XLSX_CONTENT_TYPE,
            )
        },
        data={
            "should_import_terms": "true",
            "should_import_ledger": "false",
            "should_overwrite_existing": "false",
        },
        headers=csrf_headers,
    )

    assert import_response.status_code == 200
    payload = import_response.json()
    assert payload.get("success") is False
    assert payload.get("imported_contracts") == 0
    assert isinstance(payload.get("errors"), list)
    assert isinstance(payload.get("warnings"), list)


def test_excel_import_rejects_invalid_extension_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
) -> None:
    _skip_when_excel_service_unavailable()

    response = authenticated_client.post(
        "/api/v1/rental-contracts/excel/import",
        files={
            "file": (
                "contracts.txt",
                io.BytesIO(b"not-an-excel-file"),
                "text/plain",
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


def test_excel_import_requires_csrf_header_e2e(
    authenticated_client: TestClient,
) -> None:
    response = authenticated_client.post(
        "/api/v1/rental-contracts/excel/import",
        files={
            "file": (
                "contracts.xlsx",
                io.BytesIO(b"dummy-content"),
                _XLSX_CONTENT_TYPE,
            )
        },
    )

    assert response.status_code == 403
    payload = response.json()
    assert payload.get("success") is False
    assert payload.get("error_type") == "csrf_missing"


def test_excel_import_requires_file_payload_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
) -> None:
    _skip_when_excel_service_unavailable()

    response = authenticated_client.post(
        "/api/v1/rental-contracts/excel/import",
        headers=csrf_headers,
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload.get("success") is False
    error = payload.get("error", {})
    assert isinstance(error, dict)
    assert error.get("code") == "VALIDATION_ERROR"
