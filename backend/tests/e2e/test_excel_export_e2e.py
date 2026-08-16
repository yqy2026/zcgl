"""
End-to-end Excel export tests (asset import/export auxiliary domain).

Covers the synchronous Excel chain: template download, full and selected
exports (empty-data safe), and the async-task guard (a pending task
cannot be downloaded). The full async pipeline needs an independently
committed task row, which the transactional e2e harness cannot provide.
"""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.e2e

_XLSX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


def test_excel_template_and_sync_export_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
) -> None:
    """Template and sync exports stream real xlsx files without data."""
    template = authenticated_client.get("/api/v1/excel/template")
    assert template.status_code == 200, template.text
    assert _XLSX_CONTENT_TYPE in template.headers.get("content-type", "")
    assert "land_property_asset_template.xlsx" in template.headers.get(
        "content-disposition", ""
    )
    assert template.content.startswith(b"PK")

    export_all = authenticated_client.get("/api/v1/excel/export")
    assert export_all.status_code == 200, export_all.text
    assert _XLSX_CONTENT_TYPE in export_all.headers.get("content-type", "")
    assert export_all.content.startswith(b"PK")

    export_selected = authenticated_client.post(
        "/api/v1/excel/export", json=[], headers=csrf_headers
    )
    assert export_selected.status_code == 200, export_selected.text
    assert _XLSX_CONTENT_TYPE in export_selected.headers.get("content-type", "")
    assert export_selected.content.startswith(b"PK")


def test_excel_async_export_guard_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
) -> None:
    """Async export creates a task; pending tasks refuse downloads."""
    async_export = authenticated_client.post(
        "/api/v1/excel/export/async",
        json={"filters": {}, "export_format": "xlsx"},
        headers=csrf_headers,
    )
    assert async_export.status_code == 200, async_export.text
    task = async_export.json()
    assert task["task_id"]
    assert task["status"] == "pending"

    status = authenticated_client.get(f"/api/v1/excel/status/{task['task_id']}")
    assert status.status_code == 200, status.text
    assert status.json()["task_id"] == task["task_id"]

    early_download = authenticated_client.get(
        f"/api/v1/excel/download/{task['task_id']}"
    )
    assert early_download.status_code == 400, early_download.text
    error = early_download.json().get("error", {})
    assert error.get("code") == "INVALID_REQUEST"
    assert "尚未完成" in error.get("message", "")

    # Unknown tasks are a 404 on both endpoints.
    missing_id = uuid4()
    assert (
        authenticated_client.get(f"/api/v1/excel/status/{missing_id}").status_code
        == 404
    )
    assert (
        authenticated_client.get(f"/api/v1/excel/download/{missing_id}").status_code
        == 404
    )

def test_excel_export_requires_csrf_header_e2e(authenticated_client) -> None:
    """E2E Admission Standard #2: mutations need the CSRF negative branch."""
    response = authenticated_client.post("/api/v1/excel/export", json=[])
    assert response.status_code == 403
