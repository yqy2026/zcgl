"""
资产历史CRUD操作
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from models.asset import AssetHistory


class HistoryCRUD:
    """资产历史CRUD操作类"""

    def get(self, db: Session, id: str) -> Optional[AssetHistory]:
        """根据ID获取历史记录"""
        return db.query(AssetHistory).filter(AssetHistory.id == id).first()

    def get_by_asset_id(self, db: Session, asset_id: str) -> List[AssetHistory]:
        """根据资产ID获取历史记录"""
        return (
            db.query(AssetHistory)
            .filter(AssetHistory.asset_id == asset_id)
            .order_by(desc(AssetHistory.operation_time))
            .all()
        )

    def get_multi(
        self, 
        db: Session, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[AssetHistory]:
        """获取多个历史记录"""
        return (
            db.query(AssetHistory)
            .order_by(desc(AssetHistory.operation_time))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create(self, db: Session, **kwargs) -> AssetHistory:
        """创建历史记录"""
        db_obj = AssetHistory(**kwargs)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, id: str) -> AssetHistory:
        """删除历史记录"""
        obj = db.query(AssetHistory).get(id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj


# 创建全局实例
history_crud = HistoryCRUD()