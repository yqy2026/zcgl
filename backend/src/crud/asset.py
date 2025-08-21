"""
资产CRUD操作
"""

from typing import List, Optional, Dict, Any, Union
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
import copy

from .base import CRUDBase
from ..models.asset import Asset, AssetHistory
from ..schemas.asset import AssetCreate, AssetUpdate


class CRUDAsset(CRUDBase[Asset, AssetCreate, AssetUpdate]):
    """资产CRUD操作类"""
    
    def get_by_name(self, db: Session, *, property_name: str) -> Optional[Asset]:
        """根据物业名称获取资产"""
        return db.query(Asset).filter(Asset.property_name == property_name).first()
    
    def get_multi_with_search(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        sort_field: str = "created_at",
        sort_order: str = "desc"
    ) -> List[Asset]:
        """
        获取资产列表，支持搜索、筛选和排序
        
        Args:
            db: 数据库会话
            skip: 跳过记录数
            limit: 限制记录数
            search: 搜索关键词
            filters: 筛选条件
            sort_field: 排序字段
            sort_order: 排序方向（asc/desc）
        """
        query = db.query(Asset)
        
        # 搜索功能 - 支持多字段模糊搜索
        if search:
            search_term = f"%{search}%"
            search_filter = or_(
                Asset.property_name.ilike(search_term),
                Asset.address.ilike(search_term),
                Asset.ownership_entity.ilike(search_term),
                Asset.management_entity.ilike(search_term),
                Asset.actual_usage.ilike(search_term),
                Asset.business_category.ilike(search_term),
                Asset.tenant_name.ilike(search_term),
                Asset.wuyang_project_name.ilike(search_term),
                Asset.description.ilike(search_term)
            )
            query = query.filter(search_filter)
        
        # 筛选功能
        if filters:
            # 确权状态筛选
            if filters.get("ownership_status"):
                query = query.filter(Asset.ownership_status == filters["ownership_status"])
            
            # 物业性质筛选
            if filters.get("property_nature"):
                query = query.filter(Asset.property_nature == filters["property_nature"])
            
            # 使用状态筛选
            if filters.get("usage_status"):
                query = query.filter(Asset.usage_status == filters["usage_status"])
            
            # 权属方筛选
            if filters.get("ownership_entity"):
                query = query.filter(Asset.ownership_entity == filters["ownership_entity"])
            
            # 经营管理方筛选
            if filters.get("management_entity"):
                query = query.filter(Asset.management_entity == filters["management_entity"])
            
            # 业态类别筛选
            if filters.get("business_category"):
                query = query.filter(Asset.business_category == filters["business_category"])
            
            # 面积范围筛选
            if filters.get("min_area"):
                query = query.filter(Asset.actual_property_area >= filters["min_area"])
            
            if filters.get("max_area"):
                query = query.filter(Asset.actual_property_area <= filters["max_area"])
            
            # 是否涉诉筛选
            if filters.get("is_litigated"):
                query = query.filter(Asset.is_litigated == filters["is_litigated"])
            
            # 日期范围筛选
            if filters.get("created_after"):
                query = query.filter(Asset.created_at >= filters["created_after"])
            
            if filters.get("created_before"):
                query = query.filter(Asset.created_at <= filters["created_before"])
        
        # 排序功能
        if hasattr(Asset, sort_field):
            sort_column = getattr(Asset, sort_field)
            if sort_order.lower() == "desc":
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())
        else:
            # 默认按创建时间降序排序
            query = query.order_by(Asset.created_at.desc())
        
        return query.offset(skip).limit(limit).all()
    
    def count_with_search(
        self,
        db: Session,
        *,
        search: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """获取搜索和筛选后的记录总数"""
        query = db.query(Asset)
        
        # 搜索功能 - 与get_multi_with_search保持一致
        if search:
            search_term = f"%{search}%"
            search_filter = or_(
                Asset.property_name.ilike(search_term),
                Asset.address.ilike(search_term),
                Asset.ownership_entity.ilike(search_term),
                Asset.management_entity.ilike(search_term),
                Asset.actual_usage.ilike(search_term),
                Asset.business_category.ilike(search_term),
                Asset.tenant_name.ilike(search_term),
                Asset.wuyang_project_name.ilike(search_term),
                Asset.description.ilike(search_term)
            )
            query = query.filter(search_filter)
        
        # 筛选功能 - 与get_multi_with_search保持一致
        if filters:
            # 确权状态筛选
            if filters.get("ownership_status"):
                query = query.filter(Asset.ownership_status == filters["ownership_status"])
            
            # 物业性质筛选
            if filters.get("property_nature"):
                query = query.filter(Asset.property_nature == filters["property_nature"])
            
            # 使用状态筛选
            if filters.get("usage_status"):
                query = query.filter(Asset.usage_status == filters["usage_status"])
            
            # 权属方筛选
            if filters.get("ownership_entity"):
                query = query.filter(Asset.ownership_entity == filters["ownership_entity"])
            
            # 经营管理方筛选
            if filters.get("management_entity"):
                query = query.filter(Asset.management_entity == filters["management_entity"])
            
            # 业态类别筛选
            if filters.get("business_category"):
                query = query.filter(Asset.business_category == filters["business_category"])
            
            # 面积范围筛选
            if filters.get("min_area"):
                query = query.filter(Asset.actual_property_area >= filters["min_area"])
            
            if filters.get("max_area"):
                query = query.filter(Asset.actual_property_area <= filters["max_area"])
            
            # 是否涉诉筛选
            if filters.get("is_litigated"):
                query = query.filter(Asset.is_litigated == filters["is_litigated"])
            
            # 日期范围筛选
            if filters.get("created_after"):
                query = query.filter(Asset.created_at >= filters["created_after"])
            
            if filters.get("created_before"):
                query = query.filter(Asset.created_at <= filters["created_before"])
        
        return query.count()
    
    def create_with_history(
        self, 
        db: Session, 
        *, 
        obj_in: AssetCreate, 
        changed_by: str = "system",
        reason: Optional[str] = None
    ) -> Asset:
        """创建资产并记录历史"""
        from ..services.history_tracker import HistoryTracker
        
        # 创建资产
        asset = self.create(db, obj_in=obj_in)
        
        # 记录创建历史
        HistoryTracker.track_asset_creation(
            db=db,
            asset=asset,
            changed_by=changed_by,
            reason=reason
        )
        
        db.commit()
        return asset
    
    def update_with_history(
        self,
        db: Session,
        *,
        db_obj: Asset,
        obj_in: Union[AssetUpdate, Dict[str, Any]],
        changed_by: str = "system",
        reason: Optional[str] = None
    ) -> Asset:
        """更新资产并记录历史"""
        from ..services.history_tracker import HistoryTracker
        
        # 保存更新前的状态
        old_asset = copy.deepcopy(db_obj)
        
        # 更新资产
        updated_asset = self.update(db, db_obj=db_obj, obj_in=obj_in)
        
        # 记录变更历史
        HistoryTracker.track_asset_update(
            db=db,
            old_asset=old_asset,
            new_asset=updated_asset,
            changed_by=changed_by,
            reason=reason
        )
        
        db.commit()
        return updated_asset
    
    def remove_with_history(
        self,
        db: Session,
        *,
        id: Any,
        changed_by: str = "system",
        reason: Optional[str] = None
    ) -> Asset:
        """删除资产并记录历史"""
        from ..services.history_tracker import HistoryTracker
        
        # 获取要删除的资产
        asset = self.get(db, id=id)
        if not asset:
            raise ValueError(f"资产不存在: {id}")
        
        # 记录删除历史
        HistoryTracker.track_asset_deletion(
            db=db,
            asset=asset,
            changed_by=changed_by,
            reason=reason
        )
        
        # 删除资产
        deleted_asset = self.remove(db, id=id)
        
        return deleted_asset


# 创建资产CRUD实例
asset_crud = CRUDAsset(Asset)