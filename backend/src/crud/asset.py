"""
资产CRUD操作
"""

from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc, func

from ..models.asset import Asset, AssetHistory
from ..schemas.asset import AssetCreate, AssetUpdate
from ..services.asset_calculator import AssetCalculator
class AssetCRUD:
    """资产CRUD操作类"""

    def __init__(self):
        pass

    def get(self, db: Session, id: str) -> Optional[Asset]:
        """根据ID获取资产"""
        asset = db.query(Asset).filter(Asset.id == id).first()
        if asset:
            # 解密敏感数据用于内部处理
            # 注意：在API返回前需要根据用户权限决定是否脱敏
            pass
        return asset

    def get_by_name(self, db: Session, property_name: str) -> Optional[Asset]:
        """根据物业名称获取资产"""
        return db.query(Asset).filter(Asset.property_name == property_name).first()

    def get_by_property_name(self, db: Session, property_name: str) -> Optional[Asset]:
        """根据物业名称获取资产（别名方法）"""
        return self.get_by_name(db, property_name)

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
                elif key == "ids" and isinstance(value, list):
                    # 支持按多个资产ID筛选
                    filter_conditions.append(Asset.id.in_(value))
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

    def get_filtered_query(self, db: Session, search: Optional[str] = None,
                          filters: Optional[Dict[str, Any]] = None,
                          sort_field: str = "created_at", sort_order: str = "desc"):
        """
        获取过滤后的查询对象（不执行查询）
        用于组织权限过滤
        """
        query = db.query(Asset)

        # 搜索条件
        if search:
            search_filter = or_(
                Asset.property_name.contains(search),
                Asset.address.contains(search),
                Asset.ownership_entity.contains(search),
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
                elif key == "ids" and isinstance(value, list):
                    # 支持按多个资产ID筛选
                    filter_conditions.append(Asset.id.in_(value))
                elif hasattr(Asset, key):
                    filter_conditions.append(getattr(Asset, key) == value)

            if filter_conditions:
                query = query.filter(and_(*filter_conditions))

        # 排序
        if hasattr(Asset, sort_field):
            sort_column = getattr(Asset, sort_field)
            if sort_order.lower() == "desc":
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(asc(sort_column))

        return query

    def execute_paginated_query(self, query, skip: int = 0, limit: int = 100) -> Tuple[List[Asset], int]:
        """
        执行分页查询
        """
        total = query.count()
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
                elif key == "ids" and isinstance(value, list):
                    # 支持按多个资产ID筛选
                    filter_conditions.append(Asset.id.in_(value))
                elif hasattr(Asset, key):
                    filter_conditions.append(getattr(Asset, key) == value)
            
            if filter_conditions:
                query = query.filter(and_(*filter_conditions))
        
        return query.count()

    def create(self, db: Session, obj_in: AssetCreate) -> Asset:
        """创建资产"""
        # 获取数据并进行自动计算
        asset_data = obj_in.dict()
        
        # 加密敏感数据
        asset_data = self.sensitive_data_handler.encrypt_sensitive_data(asset_data)
        
        asset_data = AssetCalculator.auto_calculate_fields(asset_data)
        
        # 验证数据一致性
        errors = AssetCalculator.validate_area_consistency(asset_data)
        if errors:
            raise ValueError(f"数据验证失败: {'; '.join(errors)}")
        
        db_obj = Asset(**asset_data)
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
        
        # 加密敏感数据
        update_data = self.sensitive_data_handler.encrypt_sensitive_data(update_data)
        
        # 合并当前数据和更新数据进行计算
        current_data = {}
        for field in ['rentable_area', 'rented_area', 'annual_income', 'annual_expense']:
            if hasattr(db_obj, field):
                current_data[field] = getattr(db_obj, field)
        
        # 合并更新数据
        current_data.update(update_data)
        
        # 自动计算相关字段
        calculated_data = AssetCalculator.auto_calculate_fields(current_data)
        
        # 验证数据一致性
        errors = AssetCalculator.validate_area_consistency(calculated_data)
        if errors:
            raise ValueError(f"数据验证失败: {'; '.join(errors)}")
        
        # 更新所有字段（包括计算得出的字段）
        for field, value in calculated_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        
        # 更新版本号
        if hasattr(db_obj, 'version'):
            db_obj.version = (db_obj.version or 0) + 1
        
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