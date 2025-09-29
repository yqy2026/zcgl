"""
初始化演示数�?
"""

from sqlalchemy.orm import Session
from datetime import datetime
import uuid

from .database import SessionLocal, create_tables
from .models.asset import Asset
from .crud.asset import CRUDAsset


def init_demo_data():
    """初始化演示数�?""
    # 创建数据库表
    create_tables()
    
    # 创建数据库会�?
    db = SessionLocal()
    
    try:
        # 检查是否已有数�?
        asset_crud = CRUDAsset(Asset)
        existing_assets = asset_crud.get_multi(db, limit=1)
        
        if existing_assets:
            print("演示数据已存在，跳过初始�?)
            return
        
        # 创建演示数据
        demo_assets = [
            {
                'property_name': '示例商业大厦A�?,
                'ownership_entity': '示例集团有限公司',
                'management_entity': '示例物业管理公司',
                'address': '广东省广州市天河区珠江新城示例路123�?,
                'land_area': 5000.0,
                'actual_property_area': 12000.0,
                'rentable_area': 10000.0,
                'rented_area': 8000.0,
                'unrented_area': 2000.0,
                'non_commercial_area': 2000.0,
                'ownership_status': '已确�?,
                'certificated_usage': '商业',
                'actual_usage': '办公、商�?,
                'business_category': '写字�?,
                'usage_status': '出租',
                'is_litigated': '�?,
                'property_nature': '经营�?,
                'business_model': '整体出租',
                'include_in_occupancy_rate': '�?,
                'occupancy_rate': '80.00%',
                'lease_contract': 'HT-2024-001',
                'tenant_name': '示例科技有限公司',
                'description': '位于珠江新城核心区域的高端商业大�?
            },
            {
                'property_name': '示例工业园B�?,
                'ownership_entity': '示例实业有限公司',
                'address': '广东省深圳市宝安区示例工业园�?,
                'land_area': 15000.0,
                'actual_property_area': 8000.0,
                'rentable_area': 7000.0,
                'rented_area': 5000.0,
                'unrented_area': 2000.0,
                'non_commercial_area': 1000.0,
                'ownership_status': '已确�?,
                'certificated_usage': '工业',
                'actual_usage': '生产制�?,
                'business_category': '制造业',
                'usage_status': '出租',
                'is_litigated': '�?,
                'property_nature': '经营�?,
                'occupancy_rate': '71.43%',
                'description': '现代化工业园区，配套设施完善'
            },
            {
                'property_name': '示例住宅小区',
                'ownership_entity': '示例房地产开发有限公�?,
                'address': '广东省广州市番禺区示例住宅区',
                'land_area': 20000.0,
                'actual_property_area': 50000.0,
                'rentable_area': 0.0,
                'rented_area': 0.0,
                'unrented_area': 0.0,
                'non_commercial_area': 50000.0,
                'ownership_status': '部分确权',
                'certificated_usage': '住宅',
                'actual_usage': '住宅',
                'business_category': '住宅',
                'usage_status': '自用',
                'is_litigated': '�?,
                'property_nature': '非经营类',
                'occupancy_rate': '0%',
                'description': '高品质住宅小区，环境优美'
            }
        ]
        
        # 插入演示数据
        for asset_data in demo_assets:
            from schemas.asset import AssetCreate
            asset_create = AssetCreate(**asset_data)
            asset_crud.create(db, obj_in=asset_create)
        
        db.commit()
        print(f"成功初始�?{len(demo_assets)} 条演示数�?)
        
    except Exception as e:
        db.rollback()
        print(f"初始化演示数据失�? {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    init_demo_data()
