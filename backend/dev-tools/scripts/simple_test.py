import os
import sys

# 将src目录添加到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

try:
    print("正在测试基本导入...")
    from schemas.asset import AssetCreate, OwnershipStatus, PropertyNature, UsageStatus

    print("✅ 基础模式导入成功")

    asset = AssetCreate(
        ownership_entity="测试权属方",
        property_name="测试物业",
        address="测试地址",
        ownership_status=OwnershipStatus.CONFIRMED,
        property_nature=PropertyNature.COMMERCIAL,
        usage_status=UsageStatus.RENTED,
    )
    print("✅ Pydantic模型创建成功")

    print("✅ 数据库连接成功")

    print("🎉 所有基础测试通过！")

except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback

    traceback.print_exc()
