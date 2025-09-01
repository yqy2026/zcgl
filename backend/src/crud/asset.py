"""
资产CRUD操作
"""

from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc, func

from models.asset import Asset, AssetHistory
from schemas.asset import AssetCreate, AssetUpdate


class AssetCRUD:
    """资产CRUD操作类"""

    def get(self, db: Session, id: str) -> Optional[Asset]:
        """根据ID获取资产"""
        return db.query(Asset).filter(Asset.id == id).first()

    def get_by_name(self, db: Session, property_name: str) -> Optional[Asset]:
        """根据物业名称获取资产"""
        return db.query(Asset).filter(Asset.property_name == property_name).first()

    def get_multi(
        self, 
        db: Session, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Asset]:
        """获取多个资产"""
        return db.query(Asset).offset(skip).limit(limit).all()

    def get_multi_with_search(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        sort_field: str = "created_at",
        sort_order: str = "desc"
    ) -> Tuple[List[Asset], int]:
        """
        获取资产列表，支持搜索、筛选和排序
        
        Args:
            db: 数据库会话
            skip: 跳过记录数
            limit: 限制记录数
            search: 搜索关键词
            filters: 筛选条件
            sort_field: 排序字段
            sort_order: 排序方向
            
        Returns:
            (资产列表, 总记录数)
        """
        query = db.query(Asset)
        
        # 搜索条件
        if search:
            search_filter = or_(
                Asset.property_name.contains(search),
                Asset.address.contains(search),
                Asset.ownership_entity.contains(search),
                Asset.management_entity.contains(search),
                Asset.business_category.contains(search)
            )
            query = query.filter(search_filter)
        
        # 筛选条件
        if filters:
            filter_conditions = []
            
            for key, value in filters.items():
                if value is None:
                    continue
                    
                if key == "min_area" and hasattr(Asset, 'total_area'):
                    filter_conditions.append(Asset.total_area >= value)
                elif key == "max_area" and hasattr(Asset, 'total_area'):
                    filter_conditions.append(Asset.total_area <= value)
                elif hasattr(Asset, key):
                    filter_conditions.append(getattr(Asset, key) == value)
            
            if filter_conditions:
                query = query.filter(and_(*filter_conditions))
        
        # 获取总记录数
        total = query.count()
        
        # 排序
        if hasattr(Asset, sort_field):
            sort_column = getattr(Asset, sort_field)
            if sort_order.lower() == "desc":
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(asc(sort_column))
        
        # 分页
        assets = query.offset(skip).limit(limit).all()
        
        return assets, total

    def count(self, db: Session) -> int:
        """获取资产总数"""
        return db.query(Asset).count()

    def count_with_search(
        self, 
        db: Session, 
        search: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """获取符合条件的资产数量"""
        query = db.query(Asset)
        
        # 搜索条件
        if search:
            search_filter = or_(
                Asset.property_name.contains(search),
                Asset.address.contains(search),
                Asset.ownership_entity.contains(search),
                Asset.management_entity.contains(search),
                Asset.business_category.contains(search)
            )
            query = query.filter(search_filter)
        
        # 筛选条件
        if filters:
            filter_conditions = []
            
            for key, value in filters.items():
                if value is None:
                    continue
                    
                if key == "min_area" and hasattr(Asset, 'total_area'):
                    filter_conditions.append(Asset.total_area >= value)
                elif key == "max_area" and hasattr(Asset, 'total_area'):
                    filter_conditions.append(Asset.total_area <= value)
                elif hasattr(Asset, key):
                    filter_conditions.append(getattr(Asset, key) == value)
            
            if filter_conditions:
                query = query.filter(and_(*filter_conditions))
        
        return query.count()

    def create(self, db: Session, obj_in: AssetCreate) -> Asset:
        """创建资产"""
        db_obj = Asset(**obj_in.dict())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def create_with_history(self, db: Session, obj_in: AssetCreate) -> Asset:
        """创建资产并记录历史"""
        # 创建资产
        db_obj = self.create(db=db, obj_in=obj_in)
        
        # 记录创建历史
        history = AssetHistory(
            asset_id=db_obj.id,
            operation_type="CREATE",
            description=f"创建资产: {db_obj.property_name}",
            operator="system"
        )
        db.add(history)
        db.commit()
        
        return db_obj

    def update(
        self, 
        db: Session, 
        db_obj: Asset, 
        obj_in: AssetUpdate
    ) -> Asset:
        """更新资产"""
        update_data = obj_in.dict(exclude_unset=True)
        
        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update_with_history(
        self,
        db: Session,
        db_obj: Asset,
        obj_in: AssetUpdate
    ) -> Asset:
        """更新资产并记录历史"""
        update_data = obj_in.dict(exclude_unset=True)
        
        # 记录变更历史
        for field, new_value in update_data.items():
            if hasattr(db_obj, field):
                old_value = getattr(db_obj, field)
                if old_value != new_value:
                    history = AssetHistory(
                        asset_id=db_obj.id,
                        operation_type="UPDATE",
                        field_name=field,
                        old_value=str(old_value) if old_value is not None else None,
                        new_value=str(new_value) if new_value is not None else None,
                        description=f"更新字段 {field}: {old_value} -> {new_value}",
                        operator="system"
                    )
                    db.add(history)
        
        # 更新资产
        updated_asset = self.update(db=db, db_obj=db_obj, obj_in=obj_in)
        db.commit()
        
        return updated_asset

    def remove(self, db: Session, id: str) -> Asset:
        """删除资产"""
        obj = db.query(Asset).get(id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj


# 创建全局实例
asset_crud = AssetCRUD()