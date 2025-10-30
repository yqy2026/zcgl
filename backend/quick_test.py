import sys
import os

# 添加路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    print("Testing basic imports...")
    from schemas.asset import AssetCreate, OwnershipStatus, PropertyNature, UsageStatus
    print("✅ Schema imports successful")
    
    from datetime import date
    asset = AssetCreate(
        ownership_entity='测试权属方',
        property_name='测试物业名称', 
        address='测试物业地址',
        ownership_status=OwnershipStatus.CONFIRMED,
        property_nature=PropertyNature.COMMERCIAL,
        usage_status=UsageStatus.RENTED,
    )
    print(f"✅ Asset creation successful: {asset.property_name}")
    
    print("🎉 All tests passed!")
    
except Exception as e:
    print(f"❌ Test failed: {e}")
    import traceback
    traceback.print_exc()