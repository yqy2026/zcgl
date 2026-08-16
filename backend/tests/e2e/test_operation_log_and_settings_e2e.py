"""
End-to-end operation log and system settings tests (REQ-SYS-002/003).

Covers the request-logging middleware's visible audit trail (filtered by
actor + module + action because committed log rows persist across tests)
and the in-memory system settings round-trip with restore.
"""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.e2e

_DEFAULT_SETTINGS: dict[str, object] = {
    "site_name": "土地物业资产管理系统",
    "site_description": "专业的土地物业资产管理平台",
    "allow_registration": False,
    "session_timeout": 120,
    "password_policy": {
        "min_length": 8,
        "require_uppercase": True,
        "require_lowercase": True,
        "require_numbers": True,
        "require_special_chars": False,
    },
}


def test_operation_log_records_business_requests_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    db_session,
) -> None:
    """The middleware audit trail is queryable for this actor's actions."""
    suffix = uuid4().hex[:8]
    admin_user_id = getattr(authenticated_client, "_user_id")

    # A business write after login is what the middleware records.
    party_response = authenticated_client.post(
        "/api/v1/parties",
        json={"party_type": "legal_entity", "name": f"日志主体-{suffix}"},
        headers=csrf_headers,
    )
    assert party_response.status_code == 200, party_response.text

    logs = authenticated_client.get(
        "/api/v1/logs",
        params={"user_id": admin_user_id, "module": "parties", "action": "create"},
    )
    assert logs.status_code == 200, logs.text
    log_data = logs.json()["data"]
    assert log_data["pagination"]["total"] >= 1
    entry = log_data["items"][0]
    assert entry["module"] == "parties"
    assert entry["action"] == "create"

    summary = authenticated_client.get(
        "/api/v1/logs/statistics/summary", params={"days": 1}
    )
    assert summary.status_code == 200
    summary_data = summary.json()["data"]
    assert summary_data["days"] == 1
    assert summary_data["total_logs"] >= 1

    # Malformed date filters are rejected.
    bad_dates = authenticated_client.get(
        "/api/v1/logs", params={"start_date": "2026/01/01"}
    )
    assert bad_dates.status_code == 400
    assert bad_dates.json().get("error", {}).get("code") == "INVALID_REQUEST"

    # Unknown log ids are a 404.
    missing = authenticated_client.get(f"/api/v1/logs/{uuid4()}")
    assert missing.status_code == 404
    assert missing.json().get("error", {}).get("code") == "RESOURCE_NOT_FOUND"


def test_system_settings_roundtrip_e2e(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
) -> None:
    """Settings round-trip in memory; unknown keys are ignored, not errors."""
    initial = authenticated_client.get("/api/v1/system/settings")
    assert initial.status_code == 200, initial.text
    assert initial.json()["data"]["site_name"] == _DEFAULT_SETTINGS["site_name"]

    updated = authenticated_client.put(
        "/api/v1/system/settings",
        json={
            **_DEFAULT_SETTINGS,
            "site_name": f"E2E站点-{uuid4().hex[:6]}",
            "session_timeout": 60,
            "unknown_key": "silently ignored",
        },
        headers=csrf_headers,
    )
    assert updated.status_code == 200, updated.text
    updated_data = updated.json()["data"]
    assert updated_data["session_timeout"] == 60
    assert updated_data["site_name"].startswith("E2E站点-")

    # Restore the module-level defaults so later tests see the baseline.
    restored = authenticated_client.put(
        "/api/v1/system/settings",
        json=_DEFAULT_SETTINGS,
        headers=csrf_headers,
    )
    assert restored.status_code == 200
    assert restored.json()["data"]["site_name"] == _DEFAULT_SETTINGS["site_name"]

    # Type violations are schema-level rejections.
    bad_type = authenticated_client.put(
        "/api/v1/system/settings",
        json={**_DEFAULT_SETTINGS, "session_timeout": "not-a-number"},
        headers=csrf_headers,
    )
    assert bad_type.status_code == 422
    restore_again = authenticated_client.put(
        "/api/v1/system/settings", json=_DEFAULT_SETTINGS, headers=csrf_headers
    )
    assert restore_again.status_code == 200

def test_settings_update_requires_csrf_header_e2e(authenticated_client) -> None:
    """E2E Admission Standard #2: mutations need the CSRF negative branch."""
    response = authenticated_client.put("/api/v1/system/settings", json={})
    assert response.status_code == 403
