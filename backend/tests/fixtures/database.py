"""
数据库测试fixtures
提供数据库相关的测试辅助函数
"""

from sqlalchemy.orm import Session


class DatabaseFixture:
    """数据库fixture类"""

    @staticmethod
    def create_asset(db: Session, **kwargs):
        """创建测试资产"""
        from src.models.asset import Asset
        from src.models.ownership import Ownership

        default_data = {
            "ownership_id": None,
            "property_name": "测试物业",
            "address": "测试地址",
            "ownership_status": "已确权",
            "property_nature": "商业用途",
            "usage_status": "使用中",
        }
        default_data.update(kwargs)

        if not default_data.get("ownership_id"):
            ownership = (
                db.query(Ownership).filter(Ownership.name == "测试权属人").first()
            )
            if not ownership:
                ownership = Ownership(name="测试权属人", code="OWN-TEST")
                db.add(ownership)
                db.flush()
                db.refresh(ownership)
            default_data["ownership_id"] = ownership.id

        asset = Asset(**default_data)
        db.add(asset)
        db.commit()
        db.refresh(asset)
        return asset

    @staticmethod
    def cleanup_assets(db: Session):
        """清理所有测试资产"""
        from src.models.asset import Asset

        db.query(Asset).delete()
        db.commit()
