"""
简单测试API函数
"""

from src.database import SessionLocal
from src.models.asset import Asset

print('=== 简单测试 ===')

# 创建数据库会话
db = SessionLocal()

try:
    print('1. 测试基础查询')
    total_assets = db.query(Asset).count()
    print(f'   总资产数: {total_assets}')

    print('2. 测试确权状态查询')
    confirmed_count = db.query(Asset).filter(Asset.ownership_status == '已确权').count()
    print(f'   已确权: {confirmed_count}')

    print('3. 测试使用状态查询')
    rented_count = db.query(Asset).filter(Asset.usage_status == '出租').count()
    print(f'   出租: {rented_count}')

    # 测试我们修复的状态
    print('4. 测试闲置状态查询')
    idle_count = db.query(Asset).filter(Asset.usage_status == '闲置').count()
    print(f'   闲置: {idle_count}')

except Exception as e:
    print(f'错误: {e}')
    import traceback
    traceback.print_exc()
finally:
    db.close()