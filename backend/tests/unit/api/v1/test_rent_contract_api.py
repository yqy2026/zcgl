"""
Comprehensive Unit Tests for Rent Contract API Routes (src/api/v1/rent_contract.py)

This test module covers all endpoints in the rent_contract router to achieve 70%+ coverage.
"""

import json
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.api

from src.constants.rent_contract_constants import PaymentStatus
from src.core.exception_handler import (
    BusinessValidationError,
    PermissionDeniedError,
    ResourceNotFoundError,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_current_user():
    """Create mock authenticated user"""
    from src.models.auth import UserRole

    user = MagicMock()
    user.id = "test-user-id"
    user.username = "testuser"
    user.full_name = "Test User"
    user.is_active = True
    user.role = UserRole.ADMIN
    return user


@pytest.fixture
def mock_current_user_admin():
    """Create mock admin user"""
    from src.models.auth import UserRole

    user = MagicMock()
    user.id = "admin-id"
    user.username = "admin"
    user.full_name = "Admin User"
    user.is_active = True
    user.role = UserRole.ADMIN
    return user


@pytest.fixture
def mock_current_user_regular():
    """Create mock regular user"""
    from src.models.auth import UserRole

    user = MagicMock()
    user.id = "user-id"
    user.username = "regularuser"
    user.full_name = "Regular User"
    user.is_active = True
    user.role = UserRole.USER
    return user


@pytest.fixture
def mock_contract():
    """Create mock contract with proper attributes"""
    contract = MagicMock()
    contract.id = "contract-123"
    contract.contract_number = "CT-2024-001"
    contract.tenant_name = "Test Tenant"
    contract.ownership_id = "ownership-123"
    contract.asset_ids = ["asset-123"]
    contract.contract_type = "lease_downstream"
    contract.owner_name = None
    contract.owner_contact = None
    contract.owner_phone = None
    contract.service_fee_rate = None
    contract.tenant_contact = None
    contract.tenant_phone = None
    contract.tenant_address = None
    contract.tenant_usage = None
    contract.sign_date = date(2024, 1, 1)
    contract.start_date = date(2024, 1, 1)
    contract.end_date = date(2024, 12, 31)
    contract.total_deposit = Decimal("0")
    contract.monthly_rent_base = None
    contract.payment_cycle = "monthly"
    contract.contract_status = "ACTIVE"
    contract.payment_terms = None
    contract.contract_notes = None
    contract.data_status = "正常"
    contract.version = 1
    contract.created_at = datetime.now()
    contract.updated_at = datetime.now()
    return contract


@pytest.fixture
def mock_ledger():
    """Create mock ledger with proper string attributes"""
    from src.constants.rent_contract_constants import PaymentStatus

    ledger = MagicMock()
    ledger.id = "ledger-123"
    ledger.contract_id = "contract-123"
    ledger.asset_id = "asset-123"
    ledger.ownership_id = "ownership-123"
    ledger.year_month = "2024-01"
    ledger.payment_status = PaymentStatus.UNPAID
    ledger.due_date = date(2024, 1, 1)
    ledger.due_amount = Decimal("1000.00")
    ledger.paid_amount = Decimal("0.00")
    ledger.overdue_amount = Decimal("0.00")
    ledger.payment_date = None
    ledger.payment_method = None
    ledger.payment_reference = None
    ledger.late_fee = Decimal("0.00")
    ledger.notes = None
    ledger.data_status = "正常"
    return ledger


# ============================================================================
# Test: POST /contracts - Create Contract
# ============================================================================


class TestCreateContract:
    """Tests for POST /contracts endpoint"""

    @patch("src.api.v1.rent_contract.contracts.asset_crud")
    @patch("src.api.v1.rent_contract.contracts.ownership")
    @patch("src.api.v1.rent_contract.contracts.rent_contract_service")
    def test_create_contract_success(
        self, mock_service, mock_ownership, mock_asset_crud, mock_db, mock_current_user
    ):
        """Test successful contract creation"""
        from src.api.v1.rent_contract.contracts import create_contract
        from src.schemas.rent_contract import RentContractCreate, RentTermCreate

        rent_term = RentTermCreate(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            monthly_rent=Decimal("1000.00"),
        )

        contract_in = RentContractCreate(
            contract_number="CT-2024-001",
            tenant_name="Test Tenant",
            ownership_id="ownership-123",
            asset_ids=["asset-123"],
            sign_date=date(2024, 1, 1),
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            rent_terms=[rent_term],
        )

        mock_asset = MagicMock()
        mock_asset_crud.get.return_value = mock_asset
        mock_ownership_obj = MagicMock()
        mock_ownership.get.return_value = mock_ownership_obj
        mock_service.create_contract.return_value = mock_contract

        result = create_contract(
            db=mock_db, contract_in=contract_in, current_user=mock_current_user
        )

        assert result is not None
        mock_service.create_contract.assert_called_once()

    @patch("src.api.v1.rent_contract.contracts.asset_crud")
    def test_create_contract_asset_not_found(
        self, mock_asset_crud, mock_db, mock_current_user
    ):
        """Test contract creation with non-existent asset"""
        from src.api.v1.rent_contract.contracts import create_contract
        from src.schemas.rent_contract import RentContractCreate, RentTermCreate

        rent_term = RentTermCreate(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            monthly_rent=Decimal("1000.00"),
        )

        contract_in = RentContractCreate(
            contract_number="CT-2024-001",
            tenant_name="Test Tenant",
            ownership_id="ownership-123",
            asset_ids=["nonexistent-asset"],
            sign_date=date(2024, 1, 1),
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            rent_terms=[rent_term],
        )

        mock_asset_crud.get.return_value = None

        with pytest.raises(ResourceNotFoundError) as exc_info:
            create_contract(
                db=mock_db, contract_in=contract_in, current_user=mock_current_user
            )

        assert exc_info.value.status_code == 404
        assert "asset不存在" in str(exc_info.value)

    @patch("src.api.v1.rent_contract.contracts.asset_crud")
    @patch("src.api.v1.rent_contract.contracts.ownership")
    def test_create_contract_ownership_not_found(
        self, mock_ownership, mock_asset_crud, mock_db, mock_current_user
    ):
        """Test contract creation with non-existent ownership"""
        from src.api.v1.rent_contract.contracts import create_contract
        from src.schemas.rent_contract import RentContractCreate, RentTermCreate

        rent_term = RentTermCreate(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            monthly_rent=Decimal("1000.00"),
        )

        contract_in = RentContractCreate(
            contract_number="CT-2024-001",
            tenant_name="Test Tenant",
            ownership_id="nonexistent-ownership",
            asset_ids=["asset-123"],
            sign_date=date(2024, 1, 1),
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            rent_terms=[rent_term],
        )

        mock_asset_crud.get.return_value = MagicMock()
        mock_ownership.get.return_value = None

        with pytest.raises(ResourceNotFoundError) as exc_info:
            create_contract(
                db=mock_db, contract_in=contract_in, current_user=mock_current_user
            )

        assert exc_info.value.status_code == 404
        assert "ownership不存在" in str(exc_info.value)


# ============================================================================
# Test: GET /contracts/{contract_id} - Get Contract Details
# ============================================================================


class TestGetContract:
    """Tests for GET /contracts/{contract_id} endpoint"""

    @patch("src.api.v1.rent_contract.contracts.rent_contract")
    def test_get_contract_success(self, mock_rent_contract, mock_db, mock_current_user):
        """Test successful contract retrieval"""
        from src.api.v1.rent_contract.contracts import get_contract

        mock_rent_contract.get_with_details.return_value = mock_contract

        result = get_contract(
            contract_id="contract-123", db=mock_db, current_user=mock_current_user
        )

        assert result is not None
        mock_rent_contract.get_with_details.assert_called_once()

    @patch("src.api.v1.rent_contract.contracts.rent_contract")
    def test_get_contract_not_found(
        self, mock_rent_contract, mock_db, mock_current_user
    ):
        """Test getting non-existent contract"""
        from src.api.v1.rent_contract.contracts import get_contract

        mock_rent_contract.get_with_details.return_value = None

        with pytest.raises(ResourceNotFoundError) as exc_info:
            get_contract(
                contract_id="nonexistent", db=mock_db, current_user=mock_current_user
            )

        assert exc_info.value.status_code == 404
        assert "contract不存在" in exc_info.value.message


# ============================================================================
# Test: GET /contracts - List Contracts
# ============================================================================


class TestGetContracts:
    """Tests for GET /contracts endpoint"""

    @patch("src.api.v1.rent_contract.contracts.rent_contract")
    def test_get_contracts_default_params(
        self, mock_rent_contract, mock_db, mock_current_user
    ):
        """Test listing contracts with default parameters"""
        from src.api.v1.rent_contract.contracts import get_contracts

        # Create proper mock contracts with all required fields
        mock_contracts = []
        for i in range(3):
            contract = MagicMock()
            contract.id = f"contract-{i}"
            contract.contract_number = f"CT-2024-00{i}"
            contract.ownership_id = f"ownership-{i}"
            contract.tenant_name = f"Tenant {i}"
            contract.contract_type = "lease_downstream"
            contract.upstream_contract_id = None
            contract.sign_date = date(2024, 1, 1)
            contract.start_date = date(2024, 1, 1)
            contract.end_date = date(2024, 12, 31)
            contract.total_deposit = Decimal("0")
            contract.payment_cycle = "monthly"
            contract.contract_status = "ACTIVE"
            contract.data_status = "正常"
            contract.version = 1
            contract.created_at = datetime.now()
            contract.updated_at = datetime.now()
            contract.asset_ids = []
            contract.owner_name = None
            contract.owner_contact = None
            contract.owner_phone = None
            contract.service_fee_rate = None
            contract.tenant_contact = None
            contract.tenant_phone = None
            contract.tenant_address = None
            contract.tenant_usage = None
            contract.monthly_rent_base = None
            contract.payment_terms = None
            contract.contract_notes = None
            mock_contracts.append(contract)

        mock_rent_contract.get_multi_with_filters.return_value = (mock_contracts, 3)

        # Call with explicit default values instead of relying on Query defaults
        result = get_contracts(
            db=mock_db,
            current_user=mock_current_user,
            page=1,
            page_size=10,
            contract_number=None,
            tenant_name=None,
            asset_id=None,
            ownership_id=None,
            contract_status=None,
            start_date=None,
            end_date=None,
        )

        body = json.loads(result.body.decode())
        pagination = body["data"]["pagination"]
        assert pagination["total"] == 3
        assert pagination["page"] == 1
        assert pagination["page_size"] == 10

    @patch("src.api.v1.rent_contract.contracts.rent_contract")
    def test_get_contracts_with_pagination(
        self, mock_rent_contract, mock_db, mock_current_user
    ):
        """Test listing contracts with pagination"""
        from src.api.v1.rent_contract.contracts import get_contracts

        # Create proper mock contracts
        mock_contracts = []
        for i in range(20):
            contract = MagicMock()
            contract.id = f"contract-{i}"
            contract.contract_number = f"CT-2024-{i:03d}"
            contract.ownership_id = f"ownership-{i}"
            contract.tenant_name = f"Tenant {i}"
            contract.contract_type = "lease_downstream"
            contract.upstream_contract_id = None
            contract.sign_date = date(2024, 1, 1)
            contract.start_date = date(2024, 1, 1)
            contract.end_date = date(2024, 12, 31)
            contract.total_deposit = Decimal("0")
            contract.payment_cycle = "monthly"
            contract.contract_status = "ACTIVE"
            contract.data_status = "正常"
            contract.version = 1
            contract.created_at = datetime.now()
            contract.updated_at = datetime.now()
            contract.asset_ids = []
            contract.owner_name = None
            contract.owner_contact = None
            contract.owner_phone = None
            contract.service_fee_rate = None
            contract.tenant_contact = None
            contract.tenant_phone = None
            contract.tenant_address = None
            contract.tenant_usage = None
            contract.monthly_rent_base = None
            contract.payment_terms = None
            contract.contract_notes = None
            mock_contracts.append(contract)

        mock_rent_contract.get_multi_with_filters.return_value = (
            mock_contracts[:10],
            25,
        )

        result = get_contracts(
            db=mock_db,
            current_user=mock_current_user,
            page=2,
            page_size=10,
            contract_number=None,
            tenant_name=None,
            asset_id=None,
            ownership_id=None,
            contract_status=None,
            start_date=None,
            end_date=None,
        )

        body = json.loads(result.body.decode())
        pagination = body["data"]["pagination"]
        assert pagination["total"] == 25
        assert pagination["page"] == 2
        assert pagination["page_size"] == 10
        assert pagination["total_pages"] == 3


# ============================================================================
# Test: PUT /contracts/{contract_id} - Update Contract
# ============================================================================


class TestUpdateContract:
    """Tests for PUT /contracts/{contract_id} endpoint"""

    @patch("src.api.v1.rent_contract.contracts.can_edit_contract")
    @patch("src.api.v1.rent_contract.contracts.rent_contract")
    @patch("src.api.v1.rent_contract.contracts.rent_contract_service")
    def test_update_contract_success(
        self,
        mock_service,
        mock_rent_contract,
        mock_can_edit,
        mock_db,
        mock_current_user,
    ):
        """Test successful contract update"""
        from src.api.v1.rent_contract.contracts import update_contract
        from src.schemas.rent_contract import RentContractUpdate

        contract_in = RentContractUpdate(tenant_name="Updated Tenant")

        mock_can_edit.return_value = True
        mock_rent_contract.get_with_details.return_value = mock_contract
        mock_service.update_contract.return_value = mock_contract

        result = update_contract(
            contract_id="contract-123",
            db=mock_db,
            contract_in=contract_in,
            current_user=mock_current_user,
        )

        assert result is not None
        mock_service.update_contract.assert_called_once()

    @patch("src.api.v1.rent_contract.contracts.can_edit_contract")
    def test_update_contract_permission_denied(
        self, mock_can_edit, mock_db, mock_current_user
    ):
        """Test contract update without permission"""
        from src.api.v1.rent_contract.contracts import update_contract
        from src.schemas.rent_contract import RentContractUpdate

        contract_in = RentContractUpdate(tenant_name="Updated Tenant")

        mock_can_edit.return_value = False

        with pytest.raises(PermissionDeniedError) as exc_info:
            update_contract(
                contract_id="contract-123",
                db=mock_db,
                contract_in=contract_in,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 403
        assert "权限不足" in exc_info.value.message


# ============================================================================
# Test: DELETE /contracts/{contract_id} - Delete Contract
# ============================================================================


class TestDeleteContract:
    """Tests for DELETE /contracts/{contract_id} endpoint"""

    @patch("src.api.v1.rent_contract.contracts.rent_contract")
    def test_delete_contract_success_admin(
        self, mock_rent_contract, mock_db, mock_current_user_admin
    ):
        """Test successful contract deletion by admin"""
        from src.api.v1.rent_contract.contracts import delete_contract

        mock_rent_contract.get.return_value = mock_contract
        mock_rent_contract.remove.return_value = None

        result = delete_contract(
            contract_id="contract-123", db=mock_db, current_user=mock_current_user_admin
        )

        assert result["message"] == "合同删除成功"

    def test_delete_contract_permission_denied(
        self, mock_db, mock_current_user_regular
    ):
        """Test contract deletion by non-admin user"""
        from src.api.v1.rent_contract.contracts import delete_contract

        with pytest.raises(PermissionDeniedError) as exc_info:
            delete_contract(
                contract_id="contract-123",
                db=mock_db,
                current_user=mock_current_user_regular,
            )

        assert exc_info.value.status_code == 403


# ============================================================================
# Test: GET /contracts/{contract_id}/terms - Get Contract Terms
# ============================================================================


class TestGetContractTerms:
    """Tests for GET /contracts/{contract_id}/terms endpoint"""

    @patch("src.api.v1.rent_contract.terms.rent_term")
    def test_get_contract_terms_success(
        self, mock_rent_term, mock_db, mock_current_user
    ):
        """Test successful contract terms retrieval"""
        from src.api.v1.rent_contract.terms import get_contract_terms

        mock_terms = [MagicMock() for _ in range(3)]
        mock_rent_term.get_by_contract.return_value = mock_terms

        result = get_contract_terms(
            contract_id="contract-123", db=mock_db, current_user=mock_current_user
        )

        assert len(result) == 3


# ============================================================================
# Test: POST /contracts/{contract_id}/terms - Add Rent Term
# ============================================================================


class TestAddRentTerm:
    """Tests for POST /contracts/{contract_id}/terms endpoint"""

    @patch("src.api.v1.rent_contract.terms.rent_contract")
    @patch("src.api.v1.rent_contract.terms.rent_term")
    def test_add_rent_term_success(
        self, mock_rent_term, mock_rent_contract, mock_db, mock_current_user
    ):
        """Test successful rent term addition"""
        from src.api.v1.rent_contract.terms import add_rent_term
        from src.schemas.rent_contract import RentTermCreate

        term_in = RentTermCreate(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            monthly_rent=Decimal("1000.00"),
        )

        mock_rent_contract.get.return_value = mock_contract
        mock_rent_term.create.return_value = MagicMock()

        result = add_rent_term(
            contract_id="contract-123",
            db=mock_db,
            term_in=term_in,
            current_user=mock_current_user,
        )

        assert result is not None


# ============================================================================
# Test: GET /ledger - List Rent Ledger
# ============================================================================


class TestGetRentLedger:
    """Tests for GET /ledger endpoint"""

    @patch("src.api.v1.rent_contract.ledger.rent_ledger")
    def test_get_rent_ledger_default_params(
        self, mock_rent_ledger, mock_db, mock_current_user
    ):
        from src.constants.rent_contract_constants import PaymentStatus

        """Test listing rent ledger with default parameters"""
        from src.api.v1.rent_contract.ledger import get_rent_ledger

        # Create multiple ledger mocks
        mock_ledgers = []
        for i in range(5):
            ledger = MagicMock()
            ledger.id = f"ledger-{i}"
            ledger.contract_id = f"contract-{i}"
            ledger.asset_id = f"asset-{i}"
            ledger.ownership_id = f"ownership-{i}"
            ledger.year_month = "2024-01"
            ledger.due_date = date(2024, 1, 1)
            ledger.due_amount = Decimal("1000.00")
            ledger.paid_amount = Decimal("0.00")
            ledger.overdue_amount = Decimal("0.00")
            ledger.payment_status = PaymentStatus.UNPAID
            ledger.payment_date = None
            ledger.payment_method = None
            ledger.payment_reference = None
            ledger.late_fee = Decimal("0.00")
            ledger.notes = None
            ledger.data_status = "正常"
            ledger.created_at = datetime.now()
            ledger.updated_at = datetime.now()
            mock_ledgers.append(ledger)

        mock_rent_ledger.get_multi_with_filters.return_value = (mock_ledgers, 5)

        result = get_rent_ledger(
            db=mock_db,
            current_user=mock_current_user,
            page=1,
            page_size=10,
            contract_id=None,
            asset_id=None,
            ownership_id=None,
            year_month=None,
            payment_status=None,
            start_date=None,
            end_date=None,
        )

        body = json.loads(result.body.decode())
        pagination = body["data"]["pagination"]
        assert pagination["total"] == 5
        assert pagination["page"] == 1
        assert pagination["page_size"] == 10


# ============================================================================
# Test: GET /ledger/{ledger_id} - Get Ledger Details
# ============================================================================


class TestGetRentLedgerDetail:
    """Tests for GET /ledger/{ledger_id} endpoint"""

    @patch("src.api.v1.rent_contract.ledger.rent_ledger")
    def test_get_rent_ledger_detail_success(
        self, mock_rent_ledger, mock_db, mock_current_user
    ):
        """Test successful ledger detail retrieval"""
        from src.api.v1.rent_contract.ledger import get_rent_ledger_detail

        mock_rent_ledger.get.return_value = mock_ledger

        result = get_rent_ledger_detail(
            ledger_id="ledger-123", db=mock_db, current_user=mock_current_user
        )

        assert result is not None

    @patch("src.api.v1.rent_contract.ledger.rent_ledger")
    def test_get_rent_ledger_detail_not_found(
        self, mock_rent_ledger, mock_db, mock_current_user
    ):
        """Test getting non-existent ledger"""
        from src.api.v1.rent_contract.ledger import get_rent_ledger_detail

        mock_rent_ledger.get.return_value = None

        with pytest.raises(ResourceNotFoundError) as exc_info:
            get_rent_ledger_detail(
                ledger_id="nonexistent", db=mock_db, current_user=mock_current_user
            )

        assert exc_info.value.status_code == 404


# ============================================================================
# Test: PUT /ledger/{ledger_id} - Update Ledger
# ============================================================================


class TestUpdateRentLedger:
    """Tests for PUT /ledger/{ledger_id} endpoint"""

    @patch("src.api.v1.rent_contract.ledger.rent_ledger")
    def test_update_rent_ledger_success(
        self, mock_rent_ledger, mock_db, mock_current_user
    ):
        """Test successful ledger update"""
        from src.api.v1.rent_contract.ledger import update_rent_ledger
        from src.schemas.rent_contract import RentLedgerUpdate

        ledger_in = RentLedgerUpdate(payment_status=PaymentStatus.PAID)

        mock_rent_ledger.get.return_value = mock_ledger
        mock_rent_ledger.update.return_value = mock_ledger

        result = update_rent_ledger(
            ledger_id="ledger-123",
            ledger_in=ledger_in,
            db=mock_db,
            current_user=mock_current_user,
        )

        assert result is not None

    @patch("src.api.v1.rent_contract.ledger.rent_ledger")
    def test_update_rent_ledger_not_found(
        self, mock_rent_ledger, mock_db, mock_current_user
    ):
        """Test updating non-existent ledger"""
        from src.api.v1.rent_contract.ledger import update_rent_ledger
        from src.schemas.rent_contract import RentLedgerUpdate

        ledger_in = RentLedgerUpdate(payment_status=PaymentStatus.PAID)

        mock_rent_ledger.get.return_value = None

        with pytest.raises(ResourceNotFoundError) as exc_info:
            update_rent_ledger(
                ledger_id="nonexistent",
                ledger_in=ledger_in,
                db=mock_db,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 404

    @patch("src.api.v1.rent_contract.ledger.rent_ledger")
    def test_update_rent_ledger_invalid_status(
        self, mock_rent_ledger, mock_db, mock_current_user
    ):
        """Test ledger update with invalid payment status"""
        from src.api.v1.rent_contract.ledger import update_rent_ledger
        from src.schemas.rent_contract import RentLedgerUpdate

        ledger_in = RentLedgerUpdate(payment_status="invalid_status")

        mock_rent_ledger.get.return_value = mock_ledger

        with pytest.raises(BusinessValidationError) as exc_info:
            update_rent_ledger(
                ledger_id="ledger-123",
                ledger_in=ledger_in,
                db=mock_db,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 422


# ============================================================================
# Test: Statistics Endpoints
# ============================================================================


class TestStatisticsEndpoints:
    """Tests for statistics endpoints"""

    @patch("src.api.v1.rent_contract.statistics.rent_contract_service")
    def test_get_rent_statistics_success(
        self, mock_service, mock_db, mock_current_user
    ):
        """Test successful statistics retrieval"""
        from src.api.v1.rent_contract.statistics import get_rent_statistics

        mock_service.get_statistics.return_value = {
            "total_contracts": 10,
            "active_contracts": 8,
            "total_monthly_rent": Decimal("50000.00"),
        }

        result = get_rent_statistics(
            db=mock_db,
            current_user=mock_current_user,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            ownership_ids=None,
            asset_ids=None,
            contract_status=None,
        )

        assert result["total_contracts"] == 10

    @patch("src.api.v1.rent_contract.statistics.rent_contract_service")
    def test_get_ownership_statistics_success(
        self, mock_service, mock_db, mock_current_user
    ):
        """Test successful ownership statistics retrieval"""
        from src.api.v1.rent_contract.statistics import get_ownership_statistics

        mock_service.get_ownership_statistics.return_value = [
            {"ownership_id": "own-1", "total_contracts": 5}
        ]

        result = get_ownership_statistics(
            db=mock_db,
            current_user=mock_current_user,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )

        assert len(result) == 1

    @patch("src.api.v1.rent_contract.statistics.rent_contract_service")
    def test_get_asset_statistics_success(
        self, mock_service, mock_db, mock_current_user
    ):
        """Test successful asset statistics retrieval"""
        from src.api.v1.rent_contract.statistics import get_asset_statistics

        mock_service.get_asset_statistics.return_value = [
            {"asset_id": "asset-1", "total_contracts": 3}
        ]

        result = get_asset_statistics(
            db=mock_db,
            current_user=mock_current_user,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )

        assert len(result) == 1

    @patch("src.api.v1.rent_contract.statistics.rent_contract_service")
    def test_get_monthly_statistics_success(
        self, mock_service, mock_db, mock_current_user
    ):
        """Test successful monthly statistics retrieval"""
        from src.api.v1.rent_contract.statistics import get_monthly_statistics

        mock_service.get_monthly_statistics.return_value = [
            {"year_month": "2024-01", "total_rent": Decimal("10000.00")}
        ]

        result = get_monthly_statistics(
            db=mock_db,
            current_user=mock_current_user,
            year=2024,
        )

        assert len(result) == 1


# ============================================================================
# Test: GET /contracts/{contract_id}/ledger - Get Contract Ledger
# ============================================================================


class TestGetContractLedger:
    """Tests for GET /contracts/{contract_id}/ledger endpoint"""

    @patch("src.api.v1.rent_contract.ledger.rent_ledger")
    def test_get_contract_ledger_success(
        self, mock_rent_ledger, mock_db, mock_current_user
    ):
        """Test successful contract ledger retrieval"""
        from src.api.v1.rent_contract.ledger import get_contract_ledger

        mock_ledgers = [mock_ledger for _ in range(5)]
        mock_rent_ledger.get_multi_with_filters.return_value = (mock_ledgers, 5)

        result = get_contract_ledger(
            contract_id="contract-123", db=mock_db, current_user=mock_current_user
        )

        assert len(result) == 5


# ============================================================================
# Test: GET /assets/{asset_id}/contracts - Get Asset Contracts
# ============================================================================


class TestGetAssetContracts:
    """Tests for GET /assets/{asset_id}/contracts endpoint"""

    @patch("src.api.v1.rent_contract.contracts.rent_contract")
    def test_get_asset_contracts_success(
        self, mock_rent_contract, mock_db, mock_current_user
    ):
        """Test successful asset contracts retrieval"""
        from src.api.v1.rent_contract.contracts import get_asset_contracts

        mock_contracts = [mock_contract for _ in range(3)]
        mock_rent_contract.get_multi_with_filters.return_value = (mock_contracts, 3)

        result = get_asset_contracts(
            asset_id="asset-123", db=mock_db, current_user=mock_current_user
        )

        assert len(result) == 3


# ============================================================================
# Test: Excel Import/Export
# ============================================================================


class TestExcelOperations:
    """Tests for Excel operations endpoints"""

    @patch("src.api.v1.rent_contract.excel_ops.EXCEL_SERVICE_AVAILABLE", True)
    @patch("src.api.v1.rent_contract.excel_ops.rent_contract_excel_service")
    def test_download_excel_template_success(
        self, mock_excel_service, mock_current_user
    ):
        """Test successful Excel template download"""
        from fastapi.responses import FileResponse

        from src.api.v1.rent_contract.excel_ops import download_excel_template

        mock_excel_service.download_contract_template.return_value = {
            "success": True,
            "file_path": "/tmp/template.xlsx",
            "file_name": "template.xlsx",
        }

        result = download_excel_template(current_user=mock_current_user)

        assert isinstance(result, FileResponse)

    @patch("src.api.v1.rent_contract.excel_ops.EXCEL_SERVICE_AVAILABLE", True)
    @patch("src.api.v1.rent_contract.excel_ops.rent_contract_excel_service")
    def test_export_contracts_to_excel_success(
        self, mock_excel_service, mock_current_user
    ):
        """Test successful Excel export"""
        from fastapi.responses import FileResponse

        from src.api.v1.rent_contract.excel_ops import export_contracts_to_excel

        mock_excel_service.export_contracts_to_excel.return_value = {
            "success": True,
            "file_path": "/tmp/export.xlsx",
            "file_name": "export.xlsx",
        }

        result = export_contracts_to_excel(
            contract_ids=["contract-1", "contract-2"],
            current_user=mock_current_user,
            should_include_terms=True,
            should_include_ledger=True,
        )

        assert isinstance(result, FileResponse)


# ============================================================================
# Test: Attachment Management
# ============================================================================


class TestAttachmentManagement:
    """Tests for attachment management endpoints"""

    @pytest.mark.asyncio
    @patch("src.api.v1.rent_contract.attachments.rent_contract")
    async def test_get_contract_attachments_success(
        self, mock_rent_contract, mock_db, mock_current_user
    ):
        """Test successful attachment list retrieval"""
        from src.api.v1.rent_contract.attachments import get_contract_attachments

        mock_rent_contract.get.return_value = mock_contract

        # Mock query chain
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_order = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.order_by.return_value = mock_order

        # Mock attachment
        mock_attachment = MagicMock()
        mock_attachment.id = "att-1"
        mock_attachment.file_name = "test.pdf"
        mock_attachment.file_size = 1024
        mock_attachment.file_type = "contract_scan"
        mock_attachment.mime_type = "application/pdf"
        mock_attachment.description = "Test"
        mock_attachment.uploader = "Test User"
        mock_attachment.created_at = datetime.now()

        mock_order.all.return_value = [mock_attachment]

        result = await get_contract_attachments(
            contract_id="contract-123",
            current_user=mock_current_user,
            db=mock_db,
        )

        assert len(result) == 1
        assert result[0]["file_name"] == "test.pdf"

    @pytest.mark.asyncio
    @patch("src.api.v1.rent_contract.attachments.rent_contract")
    async def test_get_contract_attachments_contract_not_found(
        self, mock_rent_contract, mock_db, mock_current_user
    ):
        """Test getting attachments for non-existent contract"""
        from src.api.v1.rent_contract.attachments import get_contract_attachments

        mock_rent_contract.get.return_value = None

        with pytest.raises(ResourceNotFoundError) as exc_info:
            await get_contract_attachments(
                contract_id="nonexistent",
                current_user=mock_current_user,
                db=mock_db,
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_download_contract_attachment_not_found(
        self, mock_db, mock_current_user
    ):
        """Test downloading non-existent attachment"""
        from src.api.v1.rent_contract.attachments import download_contract_attachment

        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = None

        with pytest.raises(ResourceNotFoundError) as exc_info:
            await download_contract_attachment(
                contract_id="contract-123",
                attachment_id="nonexistent",
                current_user=mock_current_user,
                db=mock_db,
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_contract_attachment_not_found(
        self, mock_db, mock_current_user
    ):
        """Test deleting non-existent attachment"""
        from src.api.v1.rent_contract.attachments import delete_contract_attachment

        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = None

        with pytest.raises(ResourceNotFoundError) as exc_info:
            await delete_contract_attachment(
                contract_id="contract-123",
                attachment_id="nonexistent",
                current_user=mock_current_user,
                db=mock_db,
            )

        assert exc_info.value.status_code == 404


# ============================================================================
# Test: Additional Error Cases and Edge Cases
# ============================================================================


class TestAdditionalErrorCases:
    """Additional tests for error handling and edge cases"""

    @patch("src.api.v1.rent_contract.contracts.rent_contract")
    def test_update_contract_not_found(
        self, mock_rent_contract, mock_db, mock_current_user
    ):
        """Test updating non-existent contract"""
        from src.api.v1.rent_contract.contracts import update_contract
        from src.schemas.rent_contract import RentContractUpdate

        contract_in = RentContractUpdate(tenant_name="Updated Tenant")

        mock_rent_contract.get_with_details.return_value = None

        with pytest.raises(ResourceNotFoundError) as exc_info:
            update_contract(
                contract_id="nonexistent",
                db=mock_db,
                contract_in=contract_in,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 404

    @patch("src.api.v1.rent_contract.contracts.rent_contract")
    def test_delete_contract_not_found(
        self, mock_rent_contract, mock_db, mock_current_user_admin
    ):
        """Test deleting non-existent contract"""
        from src.api.v1.rent_contract.contracts import delete_contract

        mock_rent_contract.get.return_value = None

        with pytest.raises(ResourceNotFoundError) as exc_info:
            delete_contract(
                contract_id="nonexistent",
                db=mock_db,
                current_user=mock_current_user_admin,
            )

        assert exc_info.value.status_code == 404

    @patch("src.api.v1.rent_contract.terms.rent_contract")
    def test_add_rent_term_contract_not_found(
        self, mock_rent_contract, mock_db, mock_current_user
    ):
        """Test adding rent term to non-existent contract"""
        from src.api.v1.rent_contract.terms import add_rent_term
        from src.schemas.rent_contract import RentTermCreate

        term_in = RentTermCreate(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            monthly_rent=Decimal("1000.00"),
        )

        mock_rent_contract.get.return_value = None

        with pytest.raises(ResourceNotFoundError) as exc_info:
            add_rent_term(
                contract_id="nonexistent",
                db=mock_db,
                term_in=term_in,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 404
