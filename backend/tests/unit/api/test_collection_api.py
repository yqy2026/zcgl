"""Contract tests for collection API endpoints."""

from __future__ import annotations

from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, patch


def _sample_record(record_id: str = "record-1") -> dict[str, object]:
    now = datetime.now(UTC).isoformat()
    return {
        "id": record_id,
        "ledger_id": "ledger-1",
        "contract_id": "contract-1",
        "collection_method": "phone",
        "collection_date": date.today().isoformat(),
        "collection_status": "pending",
        "contacted_person": "张三",
        "contact_phone": "13800000000",
        "promised_amount": "1000.00",
        "promised_date": date.today().isoformat(),
        "actual_payment_amount": None,
        "collection_notes": "首次催缴",
        "next_follow_up_date": None,
        "operator": "testuser",
        "operator_id": "test_user_001",
        "created_at": now,
        "updated_at": now,
    }


class TestCollectionSummary:
    """Tests for GET /api/v1/collection/summary."""

    @patch("src.api.v1.system.collection.collection_service.get_summary_async")
    def test_get_collection_summary_success(self, mock_get_summary, client) -> None:
        mock_get_summary.return_value = {
            "total_overdue_count": 3,
            "total_overdue_amount": "3000.00",
            "pending_collection_count": 2,
            "this_month_collection_count": 5,
            "collection_success_rate": "60.00",
        }

        response = client.get("/api/v1/collection/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["total_overdue_count"] == 3
        assert data["pending_collection_count"] == 2

    def test_get_collection_summary_unauthorized(
        self, unauthenticated_client
    ) -> None:
        response = unauthenticated_client.get("/api/v1/collection/summary")
        assert response.status_code == 401


class TestListCollectionRecords:
    """Tests for GET /api/v1/collection/records."""

    @patch("src.api.v1.system.collection.collection_service.list_records_async")
    def test_list_records_success(self, mock_list_records, client) -> None:
        mock_list_records.return_value = {
            "items": [_sample_record("record-1"), _sample_record("record-2")],
            "page": 1,
            "page_size": 20,
            "total": 2,
        }

        response = client.get("/api/v1/collection/records")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["pagination"]["page"] == 1
        assert len(data["data"]["items"]) == 2

    @patch("src.api.v1.system.collection.collection_service.list_records_async")
    def test_list_records_forwards_filters(self, mock_list_records, client) -> None:
        mock_list_records.return_value = {
            "items": [],
            "page": 2,
            "page_size": 10,
            "total": 0,
        }

        response = client.get(
            "/api/v1/collection/records?"
            "ledger_id=ledger-1&contract_id=contract-1&collection_status=pending"
            "&page=2&page_size=10"
        )

        assert response.status_code == 200
        kwargs = mock_list_records.call_args.kwargs
        assert kwargs["ledger_id"] == "ledger-1"
        assert kwargs["contract_id"] == "contract-1"
        assert kwargs["collection_status"].value == "pending"
        assert kwargs["page"] == 2
        assert kwargs["page_size"] == 10


class TestCollectionRecordDetails:
    """Tests for record detail CRUD endpoints."""

    @patch("src.api.v1.system.collection.collection_service.get_by_id_async")
    def test_get_record_not_found(self, mock_get_by_id, client) -> None:
        mock_get_by_id.return_value = None

        response = client.get("/api/v1/collection/records/not-found")

        assert response.status_code == 404
        data = response.json()
        assert data["error"]["code"] == "RESOURCE_NOT_FOUND"

    @patch("src.api.v1.system.collection.collection_service.create_async")
    def test_create_record_success(self, mock_create, client) -> None:
        mock_create.return_value = _sample_record("created-1")
        payload = {
            "ledger_id": "ledger-1",
            "contract_id": "contract-1",
            "collection_method": "phone",
            "collection_date": date.today().isoformat(),
            "collection_status": "pending",
            "collection_notes": "电话催缴",
        }

        response = client.post("/api/v1/collection/records", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "created-1"
        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs["operator"] == "testuser"
        assert call_kwargs["operator_id"] == "test_user_001"

    def test_create_record_missing_required_field_returns_422(self, client) -> None:
        payload = {
            "ledger_id": "ledger-1",
            "contract_id": "contract-1",
            "collection_date": date.today().isoformat(),
        }

        response = client.post("/api/v1/collection/records", json=payload)
        assert response.status_code == 422

    @patch("src.api.v1.system.collection.collection_service.update_async")
    @patch("src.api.v1.system.collection.collection_service.get_by_id_async")
    def test_update_record_success(
        self, mock_get_by_id, mock_update, client
    ) -> None:
        existing = _sample_record("record-1")
        updated = dict(existing)
        updated["collection_status"] = "success"
        updated["collection_notes"] = "已收回"
        mock_get_by_id.return_value = existing
        mock_update.return_value = updated

        response = client.put(
            "/api/v1/collection/records/record-1",
            json={"collection_status": "success", "collection_notes": "已收回"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["collection_status"] == "success"

    @patch("src.api.v1.system.collection.collection_service.get_by_id_async")
    def test_update_record_not_found(self, mock_get_by_id, client) -> None:
        mock_get_by_id.return_value = None

        response = client.put(
            "/api/v1/collection/records/not-found",
            json={"collection_status": "success"},
        )

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"

    @patch("src.api.v1.system.collection.collection_service.delete_async")
    @patch("src.api.v1.system.collection.collection_service.get_by_id_async")
    def test_delete_record_success(
        self, mock_get_by_id, mock_delete, client
    ) -> None:
        mock_get_by_id.return_value = _sample_record("record-1")
        mock_delete.return_value = AsyncMock()

        response = client.delete("/api/v1/collection/records/record-1")

        assert response.status_code == 200
        assert response.json()["message"] == "催缴记录已删除"
        assert mock_delete.await_count == 1

    @patch("src.api.v1.system.collection.collection_service.get_by_id_async")
    def test_delete_record_not_found(self, mock_get_by_id, client) -> None:
        mock_get_by_id.return_value = None

        response = client.delete("/api/v1/collection/records/not-found")

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"
