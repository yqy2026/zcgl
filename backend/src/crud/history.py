"""
资产历史CRUD操作
"""

from typing import Any

from sqlalchemy import desc
from sqlalchemy.orm import Session

from ..models.asset import AssetHistory


class HistoryCRUD:
    """资产历史CRUD操作类"""

    def get(self, db: Session, id: str) -> AssetHistory | None:
        """根据ID获取历史记录"""
        return db.query(AssetHistory).filter(AssetHistory.id == id).first()

    def get_by_asset_id(self, db: Session, asset_id: str) -> list[AssetHistory]:
        """根据资产ID获取历史记录"""
        return (
            db.query(AssetHistory)
            .filter(AssetHistory.asset_id == asset_id)
            .order_by(desc(AssetHistory.operation_time))
            .all()
        )

    def get_multi(
        self, db: Session, skip: int = 0, limit: int = 100
    ) -> list[AssetHistory]:
        """获取多个历史记录"""
        return (
            db.query(AssetHistory)
            .order_by(desc(AssetHistory.operation_time))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create(
        self, db: Session, *, commit: bool = True, **kwargs: Any
    ) -> AssetHistory:
        """创建历史记录"""
        db_obj = AssetHistory(**kwargs)
        db.add(db_obj)
        if commit:
            db.commit()
            db.refresh(db_obj)
        else:
            db.flush()
            db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, id: str) -> AssetHistory | None:
        """删除历史记录"""
        obj = db.query(AssetHistory).filter(AssetHistory.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()
        return obj


# 创建全局实例
history_crud = HistoryCRUD()
