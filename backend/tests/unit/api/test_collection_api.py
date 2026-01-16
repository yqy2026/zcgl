"""
Tests for Collection API endpoints (api/v1/collection.py)

This test module covers all endpoints in the collection management API:
- GET /collection/summary - Get collection task summary
- GET /collection/records - List collection records
- GET /collection/records/{id} - Get collection record details
- POST /collection/records - Create collection record
- PUT /collection/records/{id} - Update collection record
- DELETE /collection/records/{id} - Delete collection record
"""

import pytest

# Skip all tests in this module - requires proper authentication setup
pytestmark = pytest.mark.skip(reason="Unit API tests require proper authentication setup")

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

from src.main import app


class TestCollectionSummary:
    """Tests for GET /collection/summary endpoint"""

    def test_get_collection_summary_success(self, client):
        """Test successful retrieval of collection summary"""
        # Setup test data
        from src.models.collection import CollectionRecord, CollectionStatus
        from src.models.rent_contract import RentLedger

        # Create test overdue ledger (use correct fields)
        ledger = RentLedger(
            id="test-ledger-1",
            contract_id="test-contract-1",
            asset_id="test-asset-1",
            year_month="2024-01",
            due_date=date(2024, 1, 1),
            payment_status="未支付",
            overdue_amount=Decimal("1000.00"),
            data_status="正常",
        )
        client.db.add(ledger)

        # Create test collection records
        record1 = CollectionRecord(
            id="test-record-1",
            ledger_id="test-ledger-1",
            contract_id="test-contract-1",
            collection_status=CollectionStatus.PENDING,
            collection_date=date.today(),
            operator="test_user",
        )
        record2 = CollectionRecord(
            id="test-record-2",
            ledger_id="test-ledger-1",
            contract_id="test-contract-1",
            collection_status=CollectionStatus.SUCCESS,
            collection_date=date.today(),
            operator="test_user",
        )
        client.db.add(record1)
        client.db.add(record2)
        client.db.commit()

        response = client.get("/api/v1/collection/summary")

        assert response.status_code == 200
        data = response.json()
        assert "total_overdue_count" in data
        assert "total_overdue_amount" in data
        assert "pending_collection_count" in data
        assert "this_month_collection_count" in data
        assert data["total_overdue_count"] >= 1
        assert data["pending_collection_count"] >= 1

    def test_get_collection_summary_unauthorized(self, client):
        """Test that unauthorized requests are rejected"""
        # Create a new client without auth

        unauthenticated_client = TestClient(app)
        response = unauthenticated_client.get("/api/v1/collection/summary")

        assert response.status_code == 401


class TestListCollectionRecords:
    """Tests for GET /collection/records endpoint"""

    def test_list_records_default_params(self, client):
        """Test listing records with default parameters"""
        from src.models.collection import CollectionRecord, CollectionStatus

        # Create test records
        for i in range(5):
            record = CollectionRecord(
                id=f"test-record-{i}",
                ledger_id=f"test-ledger-{i}",
                contract_id=f"test-contract-{i}",
                collection_status=CollectionStatus.PENDING,
                collection_date=date.today(),
                operator="test_user",
            )
            client.db.add(record)
        client.db.commit()

        response = client.get("/api/v1/collection/records")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "limit" in data
        assert data["page"] == 1
        assert data["limit"] == 20
        assert len(data["items"]) <= 20

    def test_list_records_with_filters(self, client):
        """Test listing records with status filter"""
        from src.models.collection import CollectionRecord, CollectionStatus

        # Create records with different statuses
        record1 = CollectionRecord(
            id="test-record-1",
            ledger_id="test-ledger-1",
            contract_id="test-contract-1",
            collection_status=CollectionStatus.PENDING,
            collection_date=date.today(),
            operator="test_user",
        )
        record2 = CollectionRecord(
            id="test-record-2",
            ledger_id="test-ledger-2",
            contract_id="test-contract-2",
            collection_status=CollectionStatus.SUCCESS,
            collection_date=date.today(),
            operator="test_user",
        )
        client.db.add(record1)
        client.db.add(record2)
        client.db.commit()

        # Filter by status
        response = client.get("/api/v1/collection/records?collection_status=PENDING")

        assert response.status_code == 200
        data = response.json()
        assert all(item["collection_status"] == "PENDING" for item in data["items"])

    def test_list_records_pagination(self, client):
        """Test pagination functionality"""
        from src.models.collection import CollectionRecord, CollectionStatus

        # Create 25 records (more than default page size)
        for i in range(25):
            record = CollectionRecord(
                id=f"test-record-{i}",
                ledger_id=f"test-ledger-{i}",
                contract_id=f"test-contract-{i}",
                collection_status=CollectionStatus.PENDING,
                collection_date=date.today(),
                operator="test_user",
            )
            client.db.add(record)
        client.db.commit()

        # Get first page
        response = client.get("/api/v1/collection/records?page=1&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 10
        assert data["page"] == 1
        assert data["total"] >= 25


class TestGetCollectionRecord:
    """Tests for GET /collection/records/{record_id} endpoint"""

    def test_get_record_success(self, client):
        """Test successful retrieval of collection record"""
        from src.models.collection import CollectionRecord, CollectionStatus

        record = CollectionRecord(
            id="test-record-1",
            ledger_id="test-ledger-1",
            contract_id="test-contract-1",
            collection_status=CollectionStatus.PENDING,
            collection_date=date.today(),
            operator="test_user",
            notes="Test collection record",
        )
        client.db.add(record)
        client.db.commit()

        response = client.get("/api/v1/collection/records/test-record-1")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test-record-1"
        assert data["ledger_id"] == "test-ledger-1"
        assert data["notes"] == "Test collection record"

    def test_get_record_not_found(self, client):
        """Test retrieving non-existent record returns 404"""
        response = client.get("/api/v1/collection/records/nonexistent-id")

        assert response.status_code == 404
        assert "不存在" in response.json()["detail"]


class TestCreateCollectionRecord:
    """Tests for POST /collection/records endpoint"""

    def test_create_record_success(self, client):
        """Test successful creation of collection record"""
        from src.models.rent_contract import RentLedger

        # Create test ledger
        ledger = RentLedger(
            id="test-ledger-1",
            contract_id="test-contract-1",
            tenant_id="test-tenant-1",
            due_date=date(2024, 1, 1),
            payment_status="未支付",
            overdue_amount=Decimal("1000.00"),
            data_status="正常",
        )
        client.db.add(ledger)
        client.db.commit()

        record_data = {
            "ledger_id": "test-ledger-1",
            "contract_id": "test-contract-1",
            "collection_status": "pending",
            "collection_date": date.today().isoformat(),
            "notes": "Test collection",
        }

        response = client.post("/api/v1/collection/records", json=record_data)

        assert response.status_code == 200
        data = response.json()
        assert data["ledger_id"] == "test-ledger-1"
        assert data["operator"] is not None

    def test_create_record_ledger_not_found(self, client):
        """Test creating record with non-existent ledger returns 404"""
        record_data = {
            "ledger_id": "nonexistent-ledger",
            "contract_id": "test-contract-1",
            "collection_status": "pending",
            "collection_date": date.today().isoformat(),
        }

        response = client.post("/api/v1/collection/records", json=record_data)

        assert response.status_code == 404
        assert "台账不存在" in response.json()["detail"]


class TestUpdateCollectionRecord:
    """Tests for PUT /collection/records/{record_id} endpoint"""

    def test_update_record_success(self, client):
        """Test successful update of collection record"""
        from src.models.collection import CollectionRecord, CollectionStatus

        record = CollectionRecord(
            id="test-record-1",
            ledger_id="test-ledger-1",
            contract_id="test-contract-1",
            collection_status=CollectionStatus.PENDING,
            collection_date=date.today(),
            operator="test_user",
        )
        client.db.add(record)
        client.db.commit()

        update_data = {
            "collection_status": "success",
            "notes": "Successfully collected",
            "promise_amount": "1000.00",
            "promise_date": date.today().isoformat(),
        }

        response = client.put("/api/v1/collection/records/test-record-1", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["collection_status"] == "success"
        assert data["notes"] == "Successfully collected"

    def test_update_record_not_found(self, client):
        """Test updating non-existent record returns 404"""
        update_data = {"collection_status": "success"}

        response = client.put(
            "/api/v1/collection/records/nonexistent-id", json=update_data
        )

        assert response.status_code == 404


class TestDeleteCollectionRecord:
    """Tests for DELETE /collection/records/{record_id} endpoint"""

    def test_delete_record_success(self, client):
        """Test successful deletion of collection record"""
        from src.models.collection import CollectionRecord, CollectionStatus

        record = CollectionRecord(
            id="test-record-1",
            ledger_id="test-ledger-1",
            contract_id="test-contract-1",
            collection_status=CollectionStatus.PENDING,
            collection_date=date.today(),
            operator="test_user",
        )
        client.db.add(record)
        client.db.commit()

        response = client.delete("/api/v1/collection/records/test-record-1")

        assert response.status_code == 200
        assert "已删除" in response.json()["message"]

        # Verify record is deleted
        from src.models.collection import CollectionRecord

        deleted_record = (
            client.db.query(CollectionRecord)
            .filter(CollectionRecord.id == "test-record-1")
            .first()
        )
        assert deleted_record is None

    def test_delete_record_not_found(self, client):
        """Test deleting non-existent record returns 404"""
        response = client.delete("/api/v1/collection/records/nonexistent-id")

        assert response.status_code == 404
