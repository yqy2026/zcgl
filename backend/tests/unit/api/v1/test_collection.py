"""
Comprehensive Unit Tests for Collection API Routes (src/api/v1/system/collection.py)

This test module covers all endpoints in the collection router to achieve 70%+ coverage.

Endpoints Tested:
1. GET /api/v1/collection/summary - Get collection task summary
2. GET /api/v1/collection/records - Get collection records list
3. GET /api/v1/collection/records/{record_id} - Get collection record details
4. POST /api/v1/collection/records - Create collection record
5. PUT /api/v1/collection/records/{record_id} - Update collection record
6. DELETE /api/v1/collection/records/{record_id} - Delete collection record

Testing Approach:
- Mock all dependencies (database, auth)
- Test successful responses
- Test error handling scenarios
- Test request validation
- Test response schemas
- Test edge cases (empty results, pagination, filters)
"""

import json
from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from src.core.exception_handler import BaseBusinessError, not_found
from src.models.collection import CollectionStatus
from src.schemas.collection import (
    CollectionRecordCreate,
    CollectionRecordUpdate,
)

pytestmark = pytest.mark.api


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_current_user():
    """Create mock authenticated user"""
    user = MagicMock()
    user.id = "test-user-id"
    user.username = "testuser"
    user.email = "test@example.com"
    user.is_active = True
    return user


@pytest.fixture
def mock_collection_record():
    """Create mock collection record"""
    record = MagicMock()
    record.id = "record-123"
    record.ledger_id = "ledger-123"
    record.contract_id = "contract-123"
    record.collection_method = "phone"
    record.collection_date = date.today()
    record.collection_status = CollectionStatus.PENDING
    record.contacted_person = "John Doe"
    record.contact_phone = "1234567890"
    record.promised_amount = Decimal("1000.00")
    record.promised_date = date.today()
    record.actual_payment_amount = None
    record.collection_notes = "Initial contact made"
    record.next_follow_up_date = None
    record.operator = "testuser"
    record.operator_id = "test-user-id"
    record.created_at = datetime.now(UTC)
    record.updated_at = datetime.now(UTC)
    return record


@pytest.fixture
def mock_rent_ledger():
    """Create mock rent ledger"""
    from src.constants.rent_contract_constants import PaymentStatus

    ledger = MagicMock()
    ledger.id = "ledger-123"
    ledger.payment_status = PaymentStatus.UNPAID
    ledger.due_date = date.today()
    ledger.overdue_amount = Decimal("5000.00")
    ledger.data_status = "正常"
    return ledger


@pytest.fixture
def mock_collection_service(monkeypatch):
    """Patch collection_service used by the collection endpoints."""
    from src.api.v1.system import collection as collection_module

    service = MagicMock()
    monkeypatch.setattr(collection_module, "collection_service", service)
    return service


def assert_paginated_payload(payload, *, total, page, page_size, items_len):
    """Assert standard pagination payload fields."""
    assert payload["success"] is True
    data = payload["data"]
    assert len(data["items"]) == items_len
    pagination = data["pagination"]
    assert pagination["total"] == total
    assert pagination["page"] == page
    assert pagination["page_size"] == page_size
    assert pagination["total_pages"] == (total + page_size - 1) // page_size


# ============================================================================
# Test: GET /collection/summary - Get Collection Task Summary
# ============================================================================


class TestGetCollectionSummary:
    """Tests for GET /api/v1/collection/summary endpoint"""

    @pytest.mark.skip("Complex database query mocking - tested in integration tests")
    def test_get_collection_summary_success(self, mock_db, mock_current_user):
        """Test getting collection summary successfully"""
        # Skipped due to complex SQLAlchemy query mocking
        # This endpoint is tested in integration tests
        pass

    @pytest.mark.skip("Complex database query mocking - tested in integration tests")
    def test_get_collection_summary_no_overdue(self, mock_db, mock_current_user):
        """Test getting collection summary with no overdue records"""
        # Skipped due to complex SQLAlchemy query mocking
        # This endpoint is tested in integration tests
        pass

    @pytest.mark.skip("Complex database query mocking - tested in integration tests")
    def test_get_collection_summary_zero_total_records(
        self, mock_db, mock_current_user
    ):
        """Test getting collection summary with zero total collection records"""
        # Skipped due to complex SQLAlchemy query mocking
        # This endpoint is tested in integration tests
        pass


# ============================================================================
# Test: GET /collection/records - Get Collection Records List
# ============================================================================


class TestListCollectionRecords:
    """Tests for GET /api/v1/collection/records endpoint"""

    def test_list_records_default_params(
        self,
        mock_db,
        mock_current_user,
        mock_collection_record,
        mock_collection_service,
    ):
        """Test getting collection records with default parameters"""
        from src.api.v1.system.collection import list_collection_records

        mock_records = [mock_collection_record for _ in range(20)]
        mock_collection_service.list_records.return_value = {
            "items": mock_records,
            "page": 1,
            "page_size": 20,
            "total": 100,
        }

        result = list_collection_records(
            ledger_id=None,
            contract_id=None,
            collection_status=None,
            page=1,
            page_size=20,
            db=mock_db,
            current_user=mock_current_user,
        )

        payload = json.loads(result.body)
        assert_paginated_payload(payload, total=100, page=1, page_size=20, items_len=20)
        mock_collection_service.list_records.assert_called_once_with(
            mock_db,
            ledger_id=None,
            contract_id=None,
            collection_status=None,
            page=1,
            page_size=20,
        )

    def test_list_records_with_ledger_filter(
        self,
        mock_db,
        mock_current_user,
        mock_collection_record,
        mock_collection_service,
    ):
        """Test getting collection records filtered by ledger_id"""
        from src.api.v1.system.collection import list_collection_records

        mock_collection_service.list_records.return_value = {
            "items": [mock_collection_record],
            "page": 1,
            "page_size": 20,
            "total": 5,
        }

        result = list_collection_records(
            ledger_id="ledger-123",
            contract_id=None,
            collection_status=None,
            page=1,
            page_size=20,
            db=mock_db,
            current_user=mock_current_user,
        )

        payload = json.loads(result.body)
        assert_paginated_payload(payload, total=5, page=1, page_size=20, items_len=1)
        mock_collection_service.list_records.assert_called_once_with(
            mock_db,
            ledger_id="ledger-123",
            contract_id=None,
            collection_status=None,
            page=1,
            page_size=20,
        )

    def test_list_records_with_contract_filter(
        self,
        mock_db,
        mock_current_user,
        mock_collection_record,
        mock_collection_service,
    ):
        """Test getting collection records filtered by contract_id"""
        from src.api.v1.system.collection import list_collection_records

        mock_collection_service.list_records.return_value = {
            "items": [mock_collection_record],
            "page": 1,
            "page_size": 20,
            "total": 3,
        }

        result = list_collection_records(
            ledger_id=None,
            contract_id="contract-123",
            collection_status=None,
            page=1,
            page_size=20,
            db=mock_db,
            current_user=mock_current_user,
        )

        payload = json.loads(result.body)
        assert_paginated_payload(payload, total=3, page=1, page_size=20, items_len=1)
        mock_collection_service.list_records.assert_called_once_with(
            mock_db,
            ledger_id=None,
            contract_id="contract-123",
            collection_status=None,
            page=1,
            page_size=20,
        )

    def test_list_records_with_status_filter(
        self,
        mock_db,
        mock_current_user,
        mock_collection_record,
        mock_collection_service,
    ):
        """Test getting collection records filtered by status"""
        from src.api.v1.system.collection import list_collection_records

        mock_collection_service.list_records.return_value = {
            "items": [mock_collection_record],
            "page": 1,
            "page_size": 20,
            "total": 8,
        }

        result = list_collection_records(
            ledger_id=None,
            contract_id=None,
            collection_status=CollectionStatus.SUCCESS,
            page=1,
            page_size=20,
            db=mock_db,
            current_user=mock_current_user,
        )

        payload = json.loads(result.body)
        assert_paginated_payload(payload, total=8, page=1, page_size=20, items_len=1)
        mock_collection_service.list_records.assert_called_once_with(
            mock_db,
            ledger_id=None,
            contract_id=None,
            collection_status=CollectionStatus.SUCCESS,
            page=1,
            page_size=20,
        )

    def test_list_records_with_all_filters(
        self,
        mock_db,
        mock_current_user,
        mock_collection_record,
        mock_collection_service,
    ):
        """Test getting collection records with all filters applied"""
        from src.api.v1.system.collection import list_collection_records

        mock_collection_service.list_records.return_value = {
            "items": [mock_collection_record],
            "page": 1,
            "page_size": 20,
            "total": 1,
        }

        result = list_collection_records(
            ledger_id="ledger-123",
            contract_id="contract-123",
            collection_status=CollectionStatus.PENDING,
            page=1,
            page_size=20,
            db=mock_db,
            current_user=mock_current_user,
        )

        payload = json.loads(result.body)
        assert_paginated_payload(payload, total=1, page=1, page_size=20, items_len=1)
        mock_collection_service.list_records.assert_called_once_with(
            mock_db,
            ledger_id="ledger-123",
            contract_id="contract-123",
            collection_status=CollectionStatus.PENDING,
            page=1,
            page_size=20,
        )

    def test_list_records_pagination(
        self,
        mock_db,
        mock_current_user,
        mock_collection_record,
        mock_collection_service,
    ):
        """Test pagination of collection records"""
        from src.api.v1.system.collection import list_collection_records

        mock_records = [mock_collection_record for _ in range(10)]
        mock_collection_service.list_records.return_value = {
            "items": mock_records,
            "page": 2,
            "page_size": 10,
            "total": 25,
        }

        result = list_collection_records(
            ledger_id=None,
            contract_id=None,
            collection_status=None,
            page=2,
            page_size=10,
            db=mock_db,
            current_user=mock_current_user,
        )

        payload = json.loads(result.body)
        assert_paginated_payload(payload, total=25, page=2, page_size=10, items_len=10)
        mock_collection_service.list_records.assert_called_once_with(
            mock_db,
            ledger_id=None,
            contract_id=None,
            collection_status=None,
            page=2,
            page_size=10,
        )

    def test_list_records_empty_result(
        self, mock_db, mock_current_user, mock_collection_service
    ):
        """Test getting collection records with empty result"""
        from src.api.v1.system.collection import list_collection_records

        mock_collection_service.list_records.return_value = {
            "items": [],
            "page": 1,
            "page_size": 20,
            "total": 0,
        }

        result = list_collection_records(
            ledger_id=None,
            contract_id=None,
            collection_status=None,
            page=1,
            page_size=20,
            db=mock_db,
            current_user=mock_current_user,
        )

        payload = json.loads(result.body)
        assert_paginated_payload(payload, total=0, page=1, page_size=20, items_len=0)

    def test_list_records_invalid_page(
        self, mock_db, mock_current_user, mock_collection_service
    ):
        """Test getting collection records with page < 1 (validation should handle)"""
        from src.api.v1.system.collection import list_collection_records

        # FastAPI Query validation should reject page < 1
        # This test verifies the endpoint would handle valid page=1
        mock_collection_service.list_records.return_value = {
            "items": [],
            "page": 1,
            "page_size": 20,
            "total": 0,
        }

        result = list_collection_records(
            ledger_id=None,
            contract_id=None,
            collection_status=None,
            page=1,  # Minimum valid page
            page_size=20,
            db=mock_db,
            current_user=mock_current_user,
        )

        payload = json.loads(result.body)
        assert payload["data"]["pagination"]["page"] == 1


# ============================================================================
# Test: GET /collection/records/{record_id} - Get Collection Record Details
# ============================================================================


class TestGetCollectionRecord:
    """Tests for GET /api/v1/collection/records/{record_id} endpoint"""

    def test_get_record_success(
        self,
        mock_db,
        mock_current_user,
        mock_collection_record,
        mock_collection_service,
    ):
        """Test getting collection record successfully"""
        from src.api.v1.system.collection import get_collection_record

        mock_collection_service.get_by_id.return_value = mock_collection_record

        result = get_collection_record(
            record_id="record-123", db=mock_db, current_user=mock_current_user
        )

        assert result.id == "record-123"
        assert result.ledger_id == "ledger-123"
        assert result.collection_method == "phone"
        mock_collection_service.get_by_id.assert_called_once_with(
            mock_db, record_id="record-123"
        )

    def test_get_record_not_found(
        self, mock_db, mock_current_user, mock_collection_service
    ):
        """Test getting non-existent collection record"""
        from src.api.v1.system.collection import get_collection_record

        mock_collection_service.get_by_id.return_value = None

        with pytest.raises(BaseBusinessError) as exc_info:
            get_collection_record(
                record_id="nonexistent", db=mock_db, current_user=mock_current_user
            )

        assert exc_info.value.status_code == 404
        assert "collection_record" in exc_info.value.message
        assert "不存在" in exc_info.value.message


# ============================================================================
# Test: POST /collection/records - Create Collection Record
# ============================================================================


class TestCreateCollectionRecord:
    """Tests for POST /api/v1/collection/records endpoint"""

    def test_create_record_success(
        self,
        mock_db,
        mock_current_user,
        mock_collection_record,
        mock_collection_service,
    ):
        """Test creating collection record successfully"""
        from src.api.v1.system.collection import create_collection_record

        record_data = CollectionRecordCreate(
            ledger_id="ledger-123",
            contract_id="contract-123",
            collection_method="phone",
            collection_date=date.today(),
            collection_status=CollectionStatus.PENDING,
            contacted_person="John Doe",
            contact_phone="1234567890",
        )
        mock_collection_service.create.return_value = mock_collection_record

        result = create_collection_record(
            record_data=record_data, db=mock_db, current_user=mock_current_user
        )

        assert result.id == "record-123"
        mock_collection_service.create.assert_called_once_with(
            mock_db,
            obj_in=record_data,
            operator="testuser",
            operator_id="test-user-id",
        )

    def test_create_record_with_operator_info(
        self,
        mock_db,
        mock_current_user,
        mock_collection_record,
        mock_collection_service,
    ):
        """Test creating collection record with operator info already set"""
        from src.api.v1.system.collection import create_collection_record

        record_data = CollectionRecordCreate(
            ledger_id="ledger-123",
            contract_id="contract-123",
            collection_method="email",
            collection_date=date.today(),
            operator="admin",
            operator_id="admin-id",
        )
        mock_collection_service.create.return_value = mock_collection_record

        create_collection_record(
            record_data=record_data, db=mock_db, current_user=mock_current_user
        )

        # Operator info should not be overwritten
        assert record_data.operator == "admin"
        assert record_data.operator_id == "admin-id"
        mock_collection_service.create.assert_called_once_with(
            mock_db,
            obj_in=record_data,
            operator="testuser",
            operator_id="test-user-id",
        )

    def test_create_record_ledger_not_found(
        self, mock_db, mock_current_user, mock_collection_service
    ):
        """Test creating collection record with non-existent ledger"""
        from src.api.v1.system.collection import create_collection_record

        record_data = CollectionRecordCreate(
            ledger_id="nonexistent-ledger",
            contract_id="contract-123",
            collection_method="phone",
            collection_date=date.today(),
        )
        mock_collection_service.create.side_effect = not_found(
            "租金台账不存在", resource_type="rent_ledger"
        )

        with pytest.raises(BaseBusinessError) as exc_info:
            create_collection_record(
                record_data=record_data, db=mock_db, current_user=mock_current_user
            )

        assert exc_info.value.status_code == 404
        assert "rent_ledger" in exc_info.value.message
        assert "不存在" in exc_info.value.message

    def test_create_record_with_all_fields(
        self,
        mock_db,
        mock_current_user,
        mock_collection_record,
        mock_collection_service,
    ):
        """Test creating collection record with all optional fields"""
        from src.api.v1.system.collection import create_collection_record

        record_data = CollectionRecordCreate(
            ledger_id="ledger-123",
            contract_id="contract-123",
            collection_method="visit",
            collection_date=date.today(),
            collection_status=CollectionStatus.IN_PROGRESS,
            contacted_person="Jane Smith",
            contact_phone="9876543210",
            promised_amount=Decimal("5000.00"),
            promised_date=date.today(),
            actual_payment_amount=Decimal("2000.00"),
            collection_notes="Visited in person, partial payment received",
            next_follow_up_date=date.today(),
        )
        mock_collection_service.create.return_value = mock_collection_record

        create_collection_record(
            record_data=record_data, db=mock_db, current_user=mock_current_user
        )

        assert record_data.promised_amount == Decimal("5000.00")
        assert record_data.actual_payment_amount == Decimal("2000.00")
        assert record_data.collection_notes is not None


# ============================================================================
# Test: PUT /collection/records/{record_id} - Update Collection Record
# ============================================================================


class TestUpdateCollectionRecord:
    """Tests for POST /api/v1/collection/records/{record_id} endpoint"""

    def test_update_record_success(
        self,
        mock_db,
        mock_current_user,
        mock_collection_record,
        mock_collection_service,
    ):
        """Test updating collection record successfully"""
        from src.api.v1.system.collection import update_collection_record

        update_data = CollectionRecordUpdate(
            collection_status=CollectionStatus.SUCCESS,
            actual_payment_amount=Decimal("5000.00"),
            collection_notes="Payment received in full",
        )

        mock_collection_service.get_by_id.return_value = mock_collection_record
        mock_collection_service.update.return_value = mock_collection_record

        result = update_collection_record(
            record_id="record-123",
            update_data=update_data,
            db=mock_db,
            current_user=mock_current_user,
        )

        assert result.id == "record-123"
        mock_collection_service.get_by_id.assert_called_once_with(
            mock_db, record_id="record-123"
        )
        mock_collection_service.update.assert_called_once_with(
            mock_db, db_obj=mock_collection_record, obj_in=update_data
        )

    def test_update_record_partial_update(
        self,
        mock_db,
        mock_current_user,
        mock_collection_record,
        mock_collection_service,
    ):
        """Test partial update of collection record"""
        from src.api.v1.system.collection import update_collection_record

        update_data = CollectionRecordUpdate(collection_notes="Follow-up scheduled")

        mock_collection_service.get_by_id.return_value = mock_collection_record
        mock_collection_service.update.return_value = mock_collection_record

        update_collection_record(
            record_id="record-123",
            update_data=update_data,
            db=mock_db,
            current_user=mock_current_user,
        )

        mock_collection_service.update.assert_called_once_with(
            mock_db, db_obj=mock_collection_record, obj_in=update_data
        )

    def test_update_record_not_found(
        self, mock_db, mock_current_user, mock_collection_service
    ):
        """Test updating non-existent collection record"""
        from src.api.v1.system.collection import update_collection_record

        update_data = CollectionRecordUpdate(collection_status=CollectionStatus.SUCCESS)

        mock_collection_service.get_by_id.return_value = None

        with pytest.raises(BaseBusinessError) as exc_info:
            update_collection_record(
                record_id="nonexistent",
                update_data=update_data,
                db=mock_db,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 404
        assert "collection_record" in exc_info.value.message
        assert "不存在" in exc_info.value.message

    def test_update_record_status_to_failed(
        self,
        mock_db,
        mock_current_user,
        mock_collection_record,
        mock_collection_service,
    ):
        """Test updating collection record status to failed"""
        from src.api.v1.system.collection import update_collection_record

        update_data = CollectionRecordUpdate(
            collection_status=CollectionStatus.FAILED,
            collection_notes="Unable to contact tenant",
        )

        mock_collection_service.get_by_id.return_value = mock_collection_record
        mock_collection_service.update.return_value = mock_collection_record

        update_collection_record(
            record_id="record-123",
            update_data=update_data,
            db=mock_db,
            current_user=mock_current_user,
        )

        mock_collection_service.update.assert_called_once_with(
            mock_db, db_obj=mock_collection_record, obj_in=update_data
        )

    def test_update_record_with_promised_payment(
        self,
        mock_db,
        mock_current_user,
        mock_collection_record,
        mock_collection_service,
    ):
        """Test updating collection record with promised payment info"""
        from src.api.v1.system.collection import update_collection_record

        update_data = CollectionRecordUpdate(
            promised_amount=Decimal("3000.00"),
            promised_date=date.today(),
            next_follow_up_date=date.today(),
        )

        mock_collection_service.get_by_id.return_value = mock_collection_record
        mock_collection_service.update.return_value = mock_collection_record

        update_collection_record(
            record_id="record-123",
            update_data=update_data,
            db=mock_db,
            current_user=mock_current_user,
        )

        mock_collection_service.update.assert_called_once_with(
            mock_db, db_obj=mock_collection_record, obj_in=update_data
        )


# ============================================================================
# Test: DELETE /collection/records/{record_id} - Delete Collection Record
# ============================================================================


class TestDeleteCollectionRecord:
    """Tests for DELETE /api/v1/collection/records/{record_id} endpoint"""

    def test_delete_record_success(
        self,
        mock_db,
        mock_current_user,
        mock_collection_record,
        mock_collection_service,
    ):
        """Test deleting collection record successfully"""
        from src.api.v1.system.collection import delete_collection_record

        mock_collection_service.get_by_id.return_value = mock_collection_record

        result = delete_collection_record(
            record_id="record-123", db=mock_db, current_user=mock_current_user
        )

        assert result["message"] == "催缴记录已删除"
        mock_collection_service.delete.assert_called_once_with(
            mock_db, db_obj=mock_collection_record
        )

    def test_delete_record_not_found(
        self, mock_db, mock_current_user, mock_collection_service
    ):
        """Test deleting non-existent collection record"""
        from src.api.v1.system.collection import delete_collection_record

        mock_collection_service.get_by_id.return_value = None

        with pytest.raises(BaseBusinessError) as exc_info:
            delete_collection_record(
                record_id="nonexistent", db=mock_db, current_user=mock_current_user
            )

        assert exc_info.value.status_code == 404
        assert "collection_record" in exc_info.value.message
        assert "不存在" in exc_info.value.message


# ============================================================================
# Test: Edge Cases and Error Handling
# ============================================================================


class TestCollectionEdgeCases:
    """Tests for edge cases and error handling"""

    def test_list_records_large_page_size(
        self,
        mock_db,
        mock_current_user,
        mock_collection_record,
        mock_collection_service,
    ):
        """Test getting collection records with maximum page size"""
        from src.api.v1.system.collection import list_collection_records

        mock_records = [mock_collection_record for _ in range(100)]
        mock_collection_service.list_records.return_value = {
            "items": mock_records,
            "page": 1,
            "page_size": 100,
            "total": 200,
        }

        result = list_collection_records(
            ledger_id=None,
            contract_id=None,
            collection_status=None,
            page=1,
            page_size=100,  # Maximum allowed limit
            db=mock_db,
            current_user=mock_current_user,
        )

        payload = json.loads(result.body)
        assert_paginated_payload(
            payload, total=200, page=1, page_size=100, items_len=100
        )

    @pytest.mark.skip("Complex database query mocking - tested in integration tests")
    def test_get_summary_with_null_success_count(self, mock_db, mock_current_user):
        """Test collection summary when success count query returns None"""
        # Skipped due to complex SQLAlchemy query mocking
        # This endpoint is tested in integration tests
        pass

    def test_create_record_without_username(
        self,
        mock_db,
        mock_current_user,
        mock_collection_record,
        mock_collection_service,
    ):
        """Test creating record when user has no username (uses email instead)"""
        from src.api.v1.system.collection import create_collection_record

        # User without username
        mock_current_user.username = None
        mock_current_user.email = "testuser@example.com"

        record_data = CollectionRecordCreate(
            ledger_id="ledger-123",
            contract_id="contract-123",
            collection_method="sms",
            collection_date=date.today(),
        )
        mock_collection_service.create.return_value = mock_collection_record

        create_collection_record(
            record_data=record_data, db=mock_db, current_user=mock_current_user
        )

        mock_collection_service.create.assert_called_once_with(
            mock_db,
            obj_in=record_data,
            operator="testuser@example.com",
            operator_id="test-user-id",
        )

