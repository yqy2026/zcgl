#!/usr/bin/env python3
"""
PDF 批量导入 API 集成测试（真实认证链路）
"""

import io

import pytest
from fastapi.testclient import TestClient

from src.api.v1.documents import pdf_batch_routes
from src.services.document.processing_tracker import BatchStatusTracker

pytestmark = pytest.mark.integration
UPLOAD_ORGANIZATION_ID = 1


@pytest.fixture
def authenticated_client(client: TestClient, test_data) -> TestClient:
    """通过真实登录流程初始化认证 cookie。"""
    admin_user = test_data["admin"]
    login_response = client.post(
        "/api/v1/auth/login",
        json={"identifier": admin_user.username, "password": "Admin123!@#"},
    )
    assert login_response.status_code == 200

    auth_token = login_response.cookies.get("auth_token")
    csrf_token = login_response.cookies.get("csrf_token")
    assert auth_token is not None

    client.cookies.set("auth_token", auth_token)
    if csrf_token is not None:
        client.cookies.set("csrf_token", csrf_token)
    setattr(client, "_csrf_token", csrf_token)
    return client


@pytest.fixture
def csrf_headers(authenticated_client: TestClient) -> dict[str, str]:
    """写操作时使用 CSRF Header。"""
    csrf_token = getattr(authenticated_client, "_csrf_token", None)
    if csrf_token is None:
        return {}
    return {"X-CSRF-Token": csrf_token}


@pytest.fixture
def owner_context(test_data) -> dict[str, int]:
    """当前登录用户的可见性上下文。"""
    return {
        "user_id": test_data["admin"].id,
        "organization_id": test_data["organization"].id,
    }


@pytest.fixture
def batch_tracker():
    """替换路由层批处理追踪器，确保测试隔离。"""
    tracker = BatchStatusTracker()
    original_tracker = pdf_batch_routes._batch_tracker
    pdf_batch_routes._batch_tracker = tracker
    yield tracker
    pdf_batch_routes._batch_tracker = original_tracker
    if hasattr(tracker, "_fallback_store"):
        tracker._fallback_store.clear()
    if hasattr(tracker, "_memory_store"):
        tracker._memory_store.clear()


@pytest.fixture
def sample_pdf_files() -> list[tuple[str, tuple[str, io.BytesIO, str]]]:
    """创建多个示例 PDF 文件。"""
    files: list[tuple[str, tuple[str, io.BytesIO, str]]] = []
    for index in range(3):
        content = f"%PDF-1.4\nSample PDF file {index}".encode()
        files.append(
            (
                "files",
                (f"contract_{index}.pdf", io.BytesIO(content), "application/pdf"),
            )
        )
    return files


def _seed_owned_batch(
    batch_tracker: BatchStatusTracker,
    *,
    batch_id: str,
    total: int,
    user_id: int,
    organization_id: int,
    status: str,
) -> None:
    created = batch_tracker.create_batch(
        batch_id=batch_id,
        total=total,
        user_id=user_id,
        organization_id=organization_id,
        created_by_user_id=str(user_id),
    )
    assert created is True
    batch_tracker.set_status(batch_id, status)


class TestBatchAuthAndUploadEndpoint:
    """批量上传与认证测试。"""

    def test_batch_health_requires_authentication(self, client: TestClient) -> None:
        response = client.get("/api/v1/pdf-import/batch/health")
        assert response.status_code == 401
        payload = response.json()
        assert payload["success"] is False

    def test_batch_upload_success(
        self,
        authenticated_client: TestClient,
        csrf_headers: dict[str, str],
        sample_pdf_files,
        owner_context: dict[str, int],
    ) -> None:
        response = authenticated_client.post(
            "/api/v1/pdf-import/batch/upload",
            files=sample_pdf_files,
            headers=csrf_headers,
            data={
                "organization_id": UPLOAD_ORGANIZATION_ID,
                "force_method": "vision",
                "auto_confirm": "false",
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["success"] is True

        data = payload["data"]
        assert isinstance(data["batch_id"], str)
        assert data["batch_id"].startswith("batch-")
        assert data["status"] == "processing"
        assert data["session_count"] == len(data["session_ids"])

        status_response = authenticated_client.get(
            f"/api/v1/pdf-import/batch/status/{data['batch_id']}"
        )
        assert status_response.status_code == 200
        status_payload = status_response.json()
        assert status_payload["success"] is True
        assert (
            status_payload["data"]["batch_status"]["batch_id"] == data["batch_id"]
        )

    def test_batch_upload_exceeds_max_size(
        self, authenticated_client: TestClient, csrf_headers: dict[str, str]
    ) -> None:
        files = []
        for index in range(15):  # 超过 MAX_BATCH_SIZE=10
            files.append(
                (
                    "files",
                    (f"file_{index}.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf"),
                )
            )

        response = authenticated_client.post(
            "/api/v1/pdf-import/batch/upload",
            files=files,
            headers=csrf_headers,
            data={"organization_id": UPLOAD_ORGANIZATION_ID},
        )

        assert response.status_code == 400
        payload = response.json()
        assert payload["success"] is False
        assert "文件数量超过限制" in payload.get("message", "")

    def test_batch_upload_no_valid_files(
        self, authenticated_client: TestClient, csrf_headers: dict[str, str]
    ) -> None:
        files = [("files", ("test.txt", io.BytesIO(b"text content"), "text/plain"))]
        response = authenticated_client.post(
            "/api/v1/pdf-import/batch/upload",
            files=files,
            headers=csrf_headers,
            data={"organization_id": UPLOAD_ORGANIZATION_ID},
        )

        assert response.status_code == 400
        payload = response.json()
        assert payload["success"] is False
        assert payload["error"]["code"] == "INVALID_REQUEST"
        assert "没有有效的 PDF 文件" in payload["error"]["message"]

    def test_batch_upload_service_busy(
        self,
        authenticated_client: TestClient,
        csrf_headers: dict[str, str],
        sample_pdf_files,
        batch_tracker: BatchStatusTracker,
        owner_context: dict[str, int],
    ) -> None:
        _seed_owned_batch(
            batch_tracker,
            batch_id="batch-active-1",
            total=3,
            user_id=owner_context["user_id"],
            organization_id=owner_context["organization_id"],
            status="processing",
        )
        _seed_owned_batch(
            batch_tracker,
            batch_id="batch-active-2",
            total=3,
            user_id=owner_context["user_id"],
            organization_id=owner_context["organization_id"],
            status="pending",
        )

        response = authenticated_client.post(
            "/api/v1/pdf-import/batch/upload",
            files=sample_pdf_files,
            headers=csrf_headers,
            data={"organization_id": UPLOAD_ORGANIZATION_ID},
        )

        assert response.status_code == 503
        payload = response.json()
        assert payload["success"] is False
        error = payload.get("error", {})
        if isinstance(error, dict) and error:
            assert error.get("code") == "SERVICE_UNAVAILABLE"
        message_text = str(error.get("message") or payload.get("message") or "")
        assert message_text != ""


class TestBatchStatusAndListEndpoint:
    """批处理状态和列表端点测试。"""

    def test_get_batch_status_success(
        self,
        authenticated_client: TestClient,
        batch_tracker: BatchStatusTracker,
        owner_context: dict[str, int],
    ) -> None:
        _seed_owned_batch(
            batch_tracker,
            batch_id="batch-abc123",
            total=3,
            user_id=owner_context["user_id"],
            organization_id=owner_context["organization_id"],
            status="processing",
        )

        response = authenticated_client.get("/api/v1/pdf-import/batch/status/batch-abc123")
        assert response.status_code == 200
        payload = response.json()
        assert payload["success"] is True
        assert payload["data"]["batch_status"]["batch_id"] == "batch-abc123"

    def test_get_batch_status_not_found(self, authenticated_client: TestClient) -> None:
        response = authenticated_client.get(
            "/api/v1/pdf-import/batch/status/batch-nonexistent"
        )
        assert response.status_code == 404
        payload = response.json()
        assert payload["success"] is False
        assert payload["error"]["code"] == "RESOURCE_NOT_FOUND"
        assert "批处理任务不存在" in payload["error"]["message"]

    def test_list_batches_all(
        self,
        authenticated_client: TestClient,
        batch_tracker: BatchStatusTracker,
        owner_context: dict[str, int],
    ) -> None:
        _seed_owned_batch(
            batch_tracker,
            batch_id="batch-001",
            total=2,
            user_id=owner_context["user_id"],
            organization_id=owner_context["organization_id"],
            status="completed",
        )
        _seed_owned_batch(
            batch_tracker,
            batch_id="batch-002",
            total=1,
            user_id=owner_context["user_id"],
            organization_id=owner_context["organization_id"],
            status="processing",
        )

        response = authenticated_client.get("/api/v1/pdf-import/batch/list")
        assert response.status_code == 200
        payload = response.json()
        assert payload["success"] is True

        batches = payload["data"]["batches"]
        batch_ids = {item["batch_id"] for item in batches}
        assert {"batch-001", "batch-002"} <= batch_ids

    def test_list_batches_with_status_filter(
        self,
        authenticated_client: TestClient,
        batch_tracker: BatchStatusTracker,
        owner_context: dict[str, int],
    ) -> None:
        _seed_owned_batch(
            batch_tracker,
            batch_id="batch-001",
            total=2,
            user_id=owner_context["user_id"],
            organization_id=owner_context["organization_id"],
            status="completed",
        )
        _seed_owned_batch(
            batch_tracker,
            batch_id="batch-002",
            total=1,
            user_id=owner_context["user_id"],
            organization_id=owner_context["organization_id"],
            status="processing",
        )

        response = authenticated_client.get(
            "/api/v1/pdf-import/batch/list?status_filter=completed"
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["success"] is True
        statuses = {item["status"] for item in payload["data"]["batches"]}
        assert statuses == {"completed"}

    def test_list_batches_with_limit(
        self,
        authenticated_client: TestClient,
        batch_tracker: BatchStatusTracker,
        owner_context: dict[str, int],
    ) -> None:
        _seed_owned_batch(
            batch_tracker,
            batch_id="batch-001",
            total=2,
            user_id=owner_context["user_id"],
            organization_id=owner_context["organization_id"],
            status="completed",
        )
        _seed_owned_batch(
            batch_tracker,
            batch_id="batch-002",
            total=1,
            user_id=owner_context["user_id"],
            organization_id=owner_context["organization_id"],
            status="processing",
        )

        response = authenticated_client.get("/api/v1/pdf-import/batch/list?limit=1")
        assert response.status_code == 200
        payload = response.json()
        assert payload["success"] is True
        assert payload["data"]["count"] <= 1


class TestBatchCancelCleanupAndHealthEndpoint:
    """取消、清理、健康检查端点测试。"""

    def test_cancel_batch_success(
        self,
        authenticated_client: TestClient,
        csrf_headers: dict[str, str],
        batch_tracker: BatchStatusTracker,
        owner_context: dict[str, int],
    ) -> None:
        _seed_owned_batch(
            batch_tracker,
            batch_id="batch-processing",
            total=2,
            user_id=owner_context["user_id"],
            organization_id=owner_context["organization_id"],
            status="processing",
        )

        response = authenticated_client.post(
            "/api/v1/pdf-import/batch/cancel/batch-processing",
            headers=csrf_headers,
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["success"] is True
        assert "cancelled_count" in payload["data"]

    def test_cancel_batch_already_completed(
        self,
        authenticated_client: TestClient,
        csrf_headers: dict[str, str],
        batch_tracker: BatchStatusTracker,
        owner_context: dict[str, int],
    ) -> None:
        _seed_owned_batch(
            batch_tracker,
            batch_id="batch-completed",
            total=2,
            user_id=owner_context["user_id"],
            organization_id=owner_context["organization_id"],
            status="completed",
        )

        response = authenticated_client.post(
            "/api/v1/pdf-import/batch/cancel/batch-completed",
            headers=csrf_headers,
        )
        assert response.status_code == 400
        payload = response.json()
        assert payload["success"] is False
        assert payload["error"]["code"] == "INVALID_REQUEST"
        assert "无法取消" in payload["error"]["message"]

    def test_cleanup_old_batches(
        self,
        authenticated_client: TestClient,
        csrf_headers: dict[str, str],
        batch_tracker: BatchStatusTracker,
        owner_context: dict[str, int],
    ) -> None:
        _seed_owned_batch(
            batch_tracker,
            batch_id="batch-old-1",
            total=2,
            user_id=owner_context["user_id"],
            organization_id=owner_context["organization_id"],
            status="completed",
        )
        _seed_owned_batch(
            batch_tracker,
            batch_id="batch-old-2",
            total=2,
            user_id=owner_context["user_id"],
            organization_id=owner_context["organization_id"],
            status="failed",
        )
        _seed_owned_batch(
            batch_tracker,
            batch_id="batch-recent",
            total=2,
            user_id=owner_context["user_id"],
            organization_id=owner_context["organization_id"],
            status="completed",
        )

        response = authenticated_client.delete(
            "/api/v1/pdf-import/batch/cleanup?older_than_hours=24",
            headers=csrf_headers,
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["success"] is True
        assert "cleaned_count" in payload["data"]

    def test_health_check(
        self, authenticated_client: TestClient, batch_tracker: BatchStatusTracker
    ) -> None:
        response = authenticated_client.get("/api/v1/pdf-import/batch/health")
        assert response.status_code == 200
        payload = response.json()
        assert payload["success"] is True
        assert payload["data"]["status"] == "healthy"

    def test_health_check_with_active_batches(
        self,
        authenticated_client: TestClient,
        batch_tracker: BatchStatusTracker,
        owner_context: dict[str, int],
    ) -> None:
        _seed_owned_batch(
            batch_tracker,
            batch_id="batch-1",
            total=2,
            user_id=owner_context["user_id"],
            organization_id=owner_context["organization_id"],
            status="processing",
        )
        _seed_owned_batch(
            batch_tracker,
            batch_id="batch-2",
            total=2,
            user_id=owner_context["user_id"],
            organization_id=owner_context["organization_id"],
            status="pending",
        )

        response = authenticated_client.get("/api/v1/pdf-import/batch/health")
        assert response.status_code == 200
        payload = response.json()
        current_usage = payload["data"]["current_usage"]
        assert current_usage["active_batches"] >= 2
        assert isinstance(current_usage["available_slots"], int)


class TestBatchAPIIntegrationScenarios:
    """批处理 API 集成场景测试。"""

    def test_upload_then_query_workflow(
        self,
        authenticated_client: TestClient,
        csrf_headers: dict[str, str],
        owner_context: dict[str, int],
    ) -> None:
        files = [("files", ("workflow.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf"))]
        upload_response = authenticated_client.post(
            "/api/v1/pdf-import/batch/upload",
            files=files,
            headers=csrf_headers,
            data={"organization_id": UPLOAD_ORGANIZATION_ID},
        )
        assert upload_response.status_code == 200
        upload_payload = upload_response.json()
        assert upload_payload["success"] is True

        batch_id = upload_payload["data"]["batch_id"]
        list_response = authenticated_client.get("/api/v1/pdf-import/batch/list")
        assert list_response.status_code == 200
        list_payload = list_response.json()
        assert list_payload["success"] is True
        assert any(
            item["batch_id"] == batch_id for item in list_payload["data"]["batches"]
        )

        status_response = authenticated_client.get(
            f"/api/v1/pdf-import/batch/status/{batch_id}"
        )
        assert status_response.status_code == 200
        status_payload = status_response.json()
        assert status_payload["success"] is True

    def test_concurrent_batch_limit_enforcement(
        self,
        authenticated_client: TestClient,
        csrf_headers: dict[str, str],
        batch_tracker: BatchStatusTracker,
        owner_context: dict[str, int],
    ) -> None:
        _seed_owned_batch(
            batch_tracker,
            batch_id="batch-1",
            total=2,
            user_id=owner_context["user_id"],
            organization_id=owner_context["organization_id"],
            status="processing",
        )
        _seed_owned_batch(
            batch_tracker,
            batch_id="batch-2",
            total=2,
            user_id=owner_context["user_id"],
            organization_id=owner_context["organization_id"],
            status="processing",
        )
        files = [("files", ("test.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf"))]

        response = authenticated_client.post(
            "/api/v1/pdf-import/batch/upload",
            files=files,
            headers=csrf_headers,
            data={"organization_id": UPLOAD_ORGANIZATION_ID},
        )
        assert response.status_code == 503
        payload = response.json()
        assert payload["success"] is False
        error = payload.get("error", {})
        if isinstance(error, dict) and error:
            assert error.get("code") == "SERVICE_UNAVAILABLE"
