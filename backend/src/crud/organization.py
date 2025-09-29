"""
组织架构数据访问层
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional, Dict, Any
from datetime import datetime

from ..models.organization import Organization, OrganizationHistory
from ..schemas.organization import OrganizationCreate, OrganizationUpdate


class OrganizationCRUD:
    """组织架构CRUD操作"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get(self, org_id: str) -> Optional[Organization]:
        """根据ID获取组织"""
        return self.db.query(Organization).filter(
            and_(Organization.id == org_id, Organization.is_deleted == False)
        ).first()
    

    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[Organization]:
        """获取所有组织"""
        query = self.db.query(Organization).filter(Organization.is_deleted == False)
        
        return query.order_by(Organization.level, Organization.sort_order).offset(skip).limit(limit).all()
    
    def get_tree(self, parent_id: Optional[str] = None) -> List[Organization]:
        """获取组织树形结构"""
        query = self.db.query(Organization).filter(
            and_(Organization.is_deleted == False, Organization.parent_id == parent_id)
        )
        return query.order_by(Organization.sort_order, Organization.name).all()
    
    def get_children(self, parent_id: str, recursive: bool = False) -> List[Organization]:
        """获取子组织"""
        if not recursive:
            return self.db.query(Organization).filter(
                and_(
                    Organization.parent_id == parent_id,
                    Organization.is_deleted == False
                )
            ).order_by(Organization.sort_order, Organization.name).all()
        else:
            # 递归获取所有子组织
            children = []
            direct_children = self.get_children(parent_id, False)
            for child in direct_children:
                children.append(child)
                children.extend(self.get_children(child.id, True))
            return children
    
    def get_path_to_root(self, org_id: str) -> List[Organization]:
        """获取到根节点的路径"""
        path = []
        current = self.get(org_id)
        
        while current:
            path.insert(0, current)
            if current.parent_id:
                current = self.get(current.parent_id)
            else:
                break
        
        return path
    
    def search(self, keyword: str, skip: int = 0, limit: int = 100) -> List[Organization]:
        """搜索组织"""
        return self.db.query(Organization).filter(
            and_(
                Organization.is_deleted == False,
                or_(
                    Organization.name.contains(keyword),
                    Organization.description.contains(keyword)
                )
            )
        ).order_by(Organization.level, Organization.sort_order).offset(skip).limit(limit).all()
    
    def create(self, obj_in: OrganizationCreate) -> Organization:
        """创建组织"""
        # 创建组织对象
        db_obj = Organization(**obj_in.dict())
        
        # 设置层级和路径
        if obj_in.parent_id:
            parent = self.get(obj_in.parent_id)
            if parent:
                db_obj.level = parent.level + 1
                db_obj.path = f"{parent.path}/{db_obj.id}" if parent.path else f"/{parent.id}/{db_obj.id}"
            else:
                raise ValueError(f"上级组织 {obj_in.parent_id} 不存在")
        else:
            db_obj.level = 1
            db_obj.path = f"/{db_obj.id}"
        
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        
        # 记录创建历史
        self._create_history(db_obj.id, "create", created_by=obj_in.created_by)
        
        return db_obj
    
    def update(self, org_id: str, obj_in: OrganizationUpdate) -> Optional[Organization]:
        """更新组织"""
        db_obj = self.get(org_id)
        if not db_obj:
            return None
        
        # 记录变更前的值
        old_values = {}
        update_data = obj_in.dict(exclude_unset=True)
        
        for field, new_value in update_data.items():
            if field == 'updated_by':
                continue
            old_value = getattr(db_obj, field)
            if old_value != new_value:
                old_values[field] = {"old": str(old_value), "new": str(new_value)}
        

        
        # 特殊处理上级组织变更
        if 'parent_id' in update_data:
            new_parent_id = update_data['parent_id']
            if new_parent_id != db_obj.parent_id:
                if new_parent_id:
                    # 检查是否会形成循环引用
                    if self._would_create_cycle(org_id, new_parent_id):
                        raise ValueError("不能将组织移动到其子组织下")
                    
                    parent = self.get(new_parent_id)
                    if parent:
                        db_obj.level = parent.level + 1
                        db_obj.path = f"{parent.path}/{db_obj.id}" if parent.path else f"/{parent.id}/{db_obj.id}"
                    else:
                        raise ValueError(f"上级组织 {new_parent_id} 不存在")
                else:
                    db_obj.level = 1
                    db_obj.path = f"/{db_obj.id}"
                
                # 更新所有子组织的层级和路径
                self._update_children_path(db_obj)
        
        # 应用更新
        for field, value in update_data.items():
            if field != 'updated_by':
                setattr(db_obj, field, value)
        
        db_obj.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(db_obj)
        
        # 记录变更历史
        for field, values in old_values.items():
            self._create_history(
                org_id, "update", field, 
                values["old"], values["new"], 
                created_by=obj_in.updated_by
            )
        
        return db_obj
    
    def delete(self, org_id: str, deleted_by: Optional[str] = None) -> bool:
        """软删除组织"""
        db_obj = self.get(org_id)
        if not db_obj:
            return False
        
        # 检查是否有子组织
        children = self.get_children(org_id)
        if children:
            raise ValueError("不能删除有子组织的组织，请先删除或移动子组织")
        
        db_obj.is_deleted = True
        db_obj.updated_at = datetime.now()
        self.db.commit()
        
        # 记录删除历史
        self._create_history(org_id, "delete", created_by=deleted_by)
        
        return True
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取组织统计信息"""
        total = self.db.query(Organization).filter(Organization.is_deleted == False).count()
        active = total  # 由于删除了status字段，所有未删除的组织都视为活跃
        inactive = 0    # 非活跃数量为0，因为没有status字段
        
        # 按层级统计
        level_stats = {}
        levels = self.db.query(Organization.level).filter(Organization.is_deleted == False).distinct().all()
        for level_row in levels:
            level = level_row[0]
            count = self.db.query(Organization).filter(
                and_(Organization.is_deleted == False, Organization.level == level)
            ).count()
            level_stats[f"level_{level}"] = count
        
        # 按类型统计（由于删除了type字段，返回空字典）
        type_stats = {}
        
        return {
            "total": total,
            "active": active,
            "inactive": inactive,
            "by_type": type_stats,
            "by_level": level_stats
        }
    
    def get_history(self, org_id: str, skip: int = 0, limit: int = 100) -> List[OrganizationHistory]:
        """获取组织变更历史"""
        return self.db.query(OrganizationHistory).filter(
            OrganizationHistory.organization_id == org_id
        ).order_by(OrganizationHistory.created_at.desc()).offset(skip).limit(limit).all()
    
    def _would_create_cycle(self, org_id: str, new_parent_id: str) -> bool:
        """检查是否会创建循环引用"""
        current_id = new_parent_id
        while current_id:
            if current_id == org_id:
                return True
            parent = self.get(current_id)
            current_id = parent.parent_id if parent else None
        return False
    
    def _update_children_path(self, parent_org: Organization):
        """更新子组织路径"""
        children = self.get_children(parent_org.id)
        for child in children:
            child.level = parent_org.level + 1
            child.path = f"{parent_org.path}/{child.id}"
            self.db.commit()
            # 递归更新子组织的子组织
            self._update_children_path(child)
    
    def _create_history(self, org_id: str, action: str, field_name: Optional[str] = None, 
                       old_value: Optional[str] = None, new_value: Optional[str] = None,
                       created_by: Optional[str] = None):
        """创建历史记录"""
        history = OrganizationHistory(
            organization_id=org_id,
            action=action,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            created_by=created_by
        )
        self.db.add(history)
        self.db.commit()


def get_organization_crud(db: Session) -> OrganizationCRUD:
    """获取组织架构CRUD实例"""
    return OrganizationCRUD(db)