import pytest
from sqlalchemy.orm import Session
from backend.src.services.asset.asset_service import AssetService
from backend.src.schemas.asset import AssetCreate, AssetUpdate
from backend.src.core.exception_handler import ResourceNotFoundError

def test_asset_service_crud_lifecycle(db: Session):
    service = AssetService(db)
    
    # 1. Create
    asset_in = AssetCreate(
        property_name="Test Service Asset",
        address="123 Test St",
        original_value=1000000.00,
        property_nature="Commercial",
        usage_status="Vacant",
        ownership_status="Owned",
        tencat_risk_level="Low"
    )
    asset = service.create_asset(asset_in)
    assert asset.property_name == "Test Service Asset"
    assert asset.id is not None
    
    # 2. Get
    fetched_asset = service.get_asset(asset.id)
    assert fetched_asset.id == asset.id
    assert fetched_asset.property_name == "Test Service Asset"
    
    # 3. Update
    update_in = AssetUpdate(
        property_name="Updated Service Asset"
    )
    updated_asset = service.update_asset(asset.id, update_in)
    assert updated_asset.property_name == "Updated Service Asset"
    
    # 4. Search
    assets, total = service.get_assets(search="Updated")
    assert total >= 1
    assert any(a.id == asset.id for a in assets)
    
    # 5. Delete
    service.delete_asset(asset.id)
    
    # 6. Verify Deletion
    with pytest.raises(ResourceNotFoundError):
        service.get_asset(asset.id)
