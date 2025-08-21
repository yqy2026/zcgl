"""
资产变更历史跟踪服务
"""

import json
import logging
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc

from src.models.asset import Asset, AssetHistory
from src.schemas.asset import AssetHistoryResponse

logger = logging.getLogger(__name__)


class HistoryTracker:
    """资产变更历史跟踪器"""
    
    # 需要忽略的字段（系统字段，不记录变更）
    IGNORED_FIELDS = {
        'id', 'created_at', 'updated_at', 'version'
    }
    
    # 敏感字段（需要特殊处理的字段）
    SENSITIVE_FIELDS = {
        'notes', 'description'
    }
    
    @staticmethod
    def get_field_changes(
        old_data: Dict[str, Any], 
        new_data: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """
        比较两个数据字典，返回变更的字段
        
        Args:
            old_data: 旧数据
            new_data: 新数据
            
        Returns:
            变更字段的字典，格式为 {field_name: {'old': old_value, 'new': new_value}}
        """
        changes = {}
        
        # 获取所有字段
        all_fields = set(old_data.keys()) | set(new_data.keys())
        
        for field in all_fields:
            # 跳过忽略的字段
            if field in HistoryTracker.IGNORED_FIELDS:
                continue
                
            old_value = old_data.get(field)
            new_value = new_data.get(field)
            
            # 处理None值和空字符串
            old_value = None if old_value in [None, ''] else old_value
            new_value = None if new_value in [None, ''] else new_value
            
            # 处理日期时间对象
            if isinstance(old_value, datetime):
                old_value = old_value.isoformat()
            if isinstance(new_value, datetime):
                new_value = new_value.isoformat()
            
            # 比较值是否发生变化
            if old_value != new_value:
                changes[field] = {
                    'old': old_value,
                    'new': new_value
                }
        
        return changes
    
    @staticmethod
    def model_to_dict(model: Asset) -> Dict[str, Any]:
        """
        将SQLAlchemy模型转换为字典
        
        Args:
            model: Asset模型实例
            
        Returns:
            模型数据的字典表示
        """
        if model is None:
            return {}
        
        data = {}
        for column in model.__table__.columns:
            value = getattr(model, column.name)
            if isinstance(value, datetime):
                value = value.isoformat()
            data[column.name] = value
        
        return data
    
    @staticmethod
    def create_history_record(
        db: Session,
        asset_id: str,
        change_type: str,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        changed_by: str = "system",
        reason: Optional[str] = None
    ) -> AssetHistory:
        """
        创建变更历史记录
        
        Args:
            db: 数据库会话
            asset_id: 资产ID
            change_type: 变更类型 (create/update/delete)
            old_values: 变更前的值
            new_values: 变更后的值
            changed_by: 变更人
            reason: 变更原因
            
        Returns:
            创建的历史记录
        """
        try:
            # 计算变更字段
            changed_fields = []
            if old_values and new_values:
                changes = HistoryTracker.get_field_changes(old_values, new_values)
                changed_fields = list(changes.keys())
            elif new_values:
                # 创建操作，所有非空字段都是变更字段
                changed_fields = [k for k, v in new_values.items() 
                                if v is not None and k not in HistoryTracker.IGNORED_FIELDS]
            
            # 创建历史记录
            history = AssetHistory(
                asset_id=asset_id,
                change_type=change_type,
                changed_fields=changed_fields,
                old_values=old_values or {},
                new_values=new_values or {},
                changed_by=changed_by,
                changed_at=datetime.utcnow(),
                reason=reason
            )
            
            db.add(history)
            db.flush()  # 获取ID但不提交事务
            
            logger.info(f"创建变更历史记录: asset_id={asset_id}, type={change_type}, fields={len(changed_fields)}")
            return history
            
        except Exception as e:
            logger.error(f"创建变更历史记录失败: {str(e)}")
            raise
    
    @staticmethod
    def track_asset_creation(
        db: Session,
        asset: Asset,
        changed_by: str = "system",
        reason: Optional[str] = None
    ) -> AssetHistory:
        """
        跟踪资产创建
        
        Args:
            db: 数据库会话
            asset: 新创建的资产
            changed_by: 创建人
            reason: 创建原因
            
        Returns:
            创建的历史记录
        """
        new_values = HistoryTracker.model_to_dict(asset)
        
        return HistoryTracker.create_history_record(
            db=db,
            asset_id=asset.id,
            change_type="create",
            old_values=None,
            new_values=new_values,
            changed_by=changed_by,
            reason=reason or "创建资产"
        )
    
    @staticmethod
    def track_asset_update(
        db: Session,
        old_asset: Asset,
        new_asset: Asset,
        changed_by: str = "system",
        reason: Optional[str] = None
    ) -> Optional[AssetHistory]:
        """
        跟踪资产更新
        
        Args:
            db: 数据库会话
            old_asset: 更新前的资产
            new_asset: 更新后的资产
            changed_by: 更新人
            reason: 更新原因
            
        Returns:
            创建的历史记录，如果没有变更则返回None
        """
        old_values = HistoryTracker.model_to_dict(old_asset)
        new_values = HistoryTracker.model_to_dict(new_asset)
        
        # 检查是否有实际变更
        changes = HistoryTracker.get_field_changes(old_values, new_values)
        if not changes:
            logger.info(f"资产 {new_asset.id} 没有实际变更，跳过历史记录")
            return None
        
        return HistoryTracker.create_history_record(
            db=db,
            asset_id=new_asset.id,
            change_type="update",
            old_values=old_values,
            new_values=new_values,
            changed_by=changed_by,
            reason=reason or f"更新资产，变更字段: {', '.join(changes.keys())}"
        )
    
    @staticmethod
    def track_asset_deletion(
        db: Session,
        asset: Asset,
        changed_by: str = "system",
        reason: Optional[str] = None
    ) -> AssetHistory:
        """
        跟踪资产删除
        
        Args:
            db: 数据库会话
            asset: 被删除的资产
            changed_by: 删除人
            reason: 删除原因
            
        Returns:
            创建的历史记录
        """
        old_values = HistoryTracker.model_to_dict(asset)
        
        return HistoryTracker.create_history_record(
            db=db,
            asset_id=asset.id,
            change_type="delete",
            old_values=old_values,
            new_values=None,
            changed_by=changed_by,
            reason=reason or "删除资产"
        )


class HistoryService:
    """变更历史服务"""
    
    def __init__(self):
        self.tracker = HistoryTracker()
    
    def get_asset_history(
        self,
        db: Session,
        asset_id: str,
        skip: int = 0,
        limit: int = 20,
        change_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取资产变更历史
        
        Args:
            db: 数据库会话
            asset_id: 资产ID
            skip: 跳过记录数
            limit: 限制记录数
            change_type: 变更类型筛选
            
        Returns:
            分页的历史记录
        """
        try:
            query = db.query(AssetHistory).filter(AssetHistory.asset_id == asset_id)
            
            # 按变更类型筛选
            if change_type:
                query = query.filter(AssetHistory.change_type == change_type)
            
            # 按时间倒序排列
            query = query.order_by(desc(AssetHistory.changed_at))
            
            # 获取总数
            total = query.count()
            
            # 分页查询
            histories = query.offset(skip).limit(limit).all()
            
            return {
                "data": histories,
                "total": total,
                "page": skip // limit + 1,
                "limit": limit,
                "has_next": skip + limit < total,
                "has_prev": skip > 0
            }
            
        except Exception as e:
            logger.error(f"获取资产历史失败: {str(e)}")
            raise
    
    def get_history_by_id(self, db: Session, history_id: str) -> Optional[AssetHistory]:
        """
        根据ID获取历史记录
        
        Args:
            db: 数据库会话
            history_id: 历史记录ID
            
        Returns:
            历史记录或None
        """
        return db.query(AssetHistory).filter(AssetHistory.id == history_id).first()
    
    def compare_history_records(
        self,
        db: Session,
        history_id1: str,
        history_id2: str
    ) -> Dict[str, Any]:
        """
        比较两个历史记录
        
        Args:
            db: 数据库会话
            history_id1: 第一个历史记录ID
            history_id2: 第二个历史记录ID
            
        Returns:
            比较结果
        """
        try:
            history1 = self.get_history_by_id(db, history_id1)
            history2 = self.get_history_by_id(db, history_id2)
            
            if not history1 or not history2:
                raise ValueError("历史记录不存在")
            
            if history1.asset_id != history2.asset_id:
                raise ValueError("不能比较不同资产的历史记录")
            
            # 获取两个记录的数据
            data1 = history1.new_values or history1.old_values or {}
            data2 = history2.new_values or history2.old_values or {}
            
            # 计算差异
            changes = HistoryTracker.get_field_changes(data1, data2)
            
            return {
                "history1": {
                    "id": history1.id,
                    "change_type": history1.change_type,
                    "changed_at": history1.changed_at.isoformat(),
                    "changed_by": history1.changed_by,
                    "data": data1
                },
                "history2": {
                    "id": history2.id,
                    "change_type": history2.change_type,
                    "changed_at": history2.changed_at.isoformat(),
                    "changed_by": history2.changed_by,
                    "data": data2
                },
                "differences": changes,
                "total_changes": len(changes)
            }
            
        except Exception as e:
            logger.error(f"比较历史记录失败: {str(e)}")
            raise
    
    def get_field_history(
        self,
        db: Session,
        asset_id: str,
        field_name: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        获取特定字段的变更历史
        
        Args:
            db: 数据库会话
            asset_id: 资产ID
            field_name: 字段名
            limit: 限制记录数
            
        Returns:
            字段变更历史列表
        """
        try:
            # 查询包含该字段变更的历史记录
            histories = db.query(AssetHistory).filter(
                AssetHistory.asset_id == asset_id,
                AssetHistory.changed_fields.contains([field_name])
            ).order_by(desc(AssetHistory.changed_at)).limit(limit).all()
            
            field_history = []
            for history in histories:
                old_value = history.old_values.get(field_name) if history.old_values else None
                new_value = history.new_values.get(field_name) if history.new_values else None
                
                field_history.append({
                    "history_id": history.id,
                    "change_type": history.change_type,
                    "old_value": old_value,
                    "new_value": new_value,
                    "changed_at": history.changed_at.isoformat(),
                    "changed_by": history.changed_by,
                    "reason": history.reason
                })
            
            return field_history
            
        except Exception as e:
            logger.error(f"获取字段历史失败: {str(e)}")
            raise
    
    def get_recent_changes(
        self,
        db: Session,
        limit: int = 50,
        change_type: Optional[str] = None
    ) -> List[AssetHistory]:
        """
        获取最近的变更记录
        
        Args:
            db: 数据库会话
            limit: 限制记录数
            change_type: 变更类型筛选
            
        Returns:
            最近的变更记录列表
        """
        try:
            query = db.query(AssetHistory)
            
            if change_type:
                query = query.filter(AssetHistory.change_type == change_type)
            
            return query.order_by(desc(AssetHistory.changed_at)).limit(limit).all()
            
        except Exception as e:
            logger.error(f"获取最近变更失败: {str(e)}")
            raise
    
    def get_change_statistics(
        self,
        db: Session,
        asset_id: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        获取变更统计信息
        
        Args:
            db: 数据库会话
            asset_id: 资产ID（可选，为空则统计所有资产）
            days: 统计天数
            
        Returns:
            变更统计信息
        """
        try:
            from datetime import timedelta
            
            # 计算时间范围
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            query = db.query(AssetHistory).filter(
                AssetHistory.changed_at >= start_date,
                AssetHistory.changed_at <= end_date
            )
            
            if asset_id:
                query = query.filter(AssetHistory.asset_id == asset_id)
            
            histories = query.all()
            
            # 统计各种变更类型
            stats = {
                "total_changes": len(histories),
                "change_types": {},
                "changed_by": {},
                "most_changed_fields": {},
                "daily_changes": {},
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "days": days
                }
            }
            
            for history in histories:
                # 统计变更类型
                change_type = history.change_type
                stats["change_types"][change_type] = stats["change_types"].get(change_type, 0) + 1
                
                # 统计变更人
                changed_by = history.changed_by
                stats["changed_by"][changed_by] = stats["changed_by"].get(changed_by, 0) + 1
                
                # 统计变更字段
                for field in history.changed_fields or []:
                    stats["most_changed_fields"][field] = stats["most_changed_fields"].get(field, 0) + 1
                
                # 统计每日变更
                date_key = history.changed_at.date().isoformat()
                stats["daily_changes"][date_key] = stats["daily_changes"].get(date_key, 0) + 1
            
            return stats
            
        except Exception as e:
            logger.error(f"获取变更统计失败: {str(e)}")
            raise