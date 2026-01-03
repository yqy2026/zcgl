from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from src.models.asset import Ownership, Asset
from src.schemas.ownership import OwnershipCreate, OwnershipUpdate
from src.services.ownership.service import OwnershipService

# Constants
TEST_OWNERSHIP_ID = "ownership_123"
TEST_OWNERSHIP_NAME = "Test Ownership"

@pytest.fixture
def mock_db():
    return MagicMock(spec=Session)

@pytest.fixture
def service():
    return OwnershipService()

class TestOwnershipService:
    def test_generate_ownership_code(self, service, mock_db):
        # Mock query return
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        
        code = service.generate_ownership_code(mock_db)
        # Should start with OW and contain date
        assert code.startswith("OW")
        assert len(code) == 9 # OW + YYMM + 001
        
    def test_create_ownership(self, service, mock_db):
        # Prepare
        create_in = OwnershipCreate(name=TEST_OWNERSHIP_NAME, short_name="TO")
        
        # Mock no existing name
        with patch("src.crud.ownership.ownership.get_by_name", return_value=None):
            # Mock code generation
            service.generate_ownership_code = MagicMock(return_value="OW2401001")
            
            # Execute
            result = service.create_ownership(mock_db, obj_in=create_in)
            
            # Verify
            assert result.name == TEST_OWNERSHIP_NAME
            assert result.code == "OW2401001"
            mock_db.add.assert_called()
            mock_db.commit.assert_called()

    def test_update_ownership(self, service, mock_db):
        # Prepare
        db_obj = Ownership(id=TEST_OWNERSHIP_ID, name=TEST_OWNERSHIP_NAME)
        update_in = OwnershipUpdate(name="New Name")
        
        with patch("src.crud.ownership.ownership.get_by_name", return_value=None):
            # Execute
            result = service.update_ownership(mock_db, db_obj=db_obj, obj_in=update_in)
            
            # Verify
            assert result.name == "New Name"
            mock_db.add.assert_called() # update calls add to merge/update session
            mock_db.commit.assert_called()

    def test_delete_ownership_with_assets(self, service, mock_db):
        # Mock get
        db_obj = Ownership(id=TEST_OWNERSHIP_ID, name=TEST_OWNERSHIP_NAME)
        
        with patch("src.crud.ownership.ownership.get", return_value=db_obj):
            # Mock asset count > 0
            # service.delete_ownership queries DB for asset count.
            mock_query = MagicMock()
            mock_db.query.return_value = mock_query
            mock_query.filter.return_value = mock_query
            mock_query.count.return_value = 5 # 5 assets
            
            # Execute & Verify
            with pytest.raises(ValueError) as excinfo:
                service.delete_ownership(mock_db, id=TEST_OWNERSHIP_ID)
            
            assert "关联资产" in str(excinfo.value)

    def test_delete_ownership_success(self, service, mock_db):
        # Mock get
        db_obj = Ownership(id=TEST_OWNERSHIP_ID, name=TEST_OWNERSHIP_NAME)
        
        with patch("src.crud.ownership.ownership.get", return_value=db_obj):
            with patch("src.crud.ownership.ownership.remove") as mock_remove:
                # Mock asset count = 0
                mock_query = MagicMock()
                mock_db.query.return_value = mock_query
                mock_query.filter.return_value = mock_query
                mock_query.count.return_value = 0
                
                # Execute
                service.delete_ownership(mock_db, id=TEST_OWNERSHIP_ID)
                
                # Verify
                mock_remove.assert_called_with(mock_db, id=TEST_OWNERSHIP_ID)

    def test_toggle_status(self, service, mock_db):
        db_obj = Ownership(id=TEST_OWNERSHIP_ID, name=TEST_OWNERSHIP_NAME, is_active=True)
        
        with patch("src.crud.ownership.ownership.get", return_value=db_obj):
            # Execute
            result = service.toggle_status(mock_db, id=TEST_OWNERSHIP_ID)
            
            # Verify
            assert result.is_active is False
            mock_db.commit.assert_called()
