from sqlalchemy import and_, not_
from sqlalchemy.orm import Session

from ..crud.base import CRUDBase
from ..models.organization import Organization
from ..schemas.organization import OrganizationCreate, OrganizationUpdate


class CRUDOrganization(CRUDBase):
    """组织架构CRUD操作"""

    def get_multi_with_filters(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        parent_id: str | None = None,
        keyword: str | None = None,
    ) -> list[Organization]:
        """获取多个组织"""
        query = db.query(Organization).filter(not_(Organization.is_deleted))
        filters = {}

        if parent_id:
            filters["parent_id"] = parent_id

        # Apply filters and search directly on query, then paginate
        if keyword:
            from sqlalchemy import or_

            query = query.filter(
                or_(
                    Organization.name.ilike(f"%{keyword}%"),
                    Organization.description.ilike(f"%{keyword}%"),
                )
            )

        # Apply sorting
        query = query.order_by(Organization.level.asc(), Organization.sort_order.asc())

        # Apply pagination
        result = query.offset(skip).limit(limit).all()
        return result

    def get_tree(self, db: Session, parent_id: str | None = None) -> list[Organization]:
        """获取组织树形结构"""
        query = db.query(Organization).filter(
            and_(not_(Organization.is_deleted), Organization.parent_id == parent_id)
        )
        return query.order_by(Organization.sort_order, Organization.name).all()

    def get_children(
        self, db: Session, parent_id: str, recursive: bool = False
    ) -> list[Organization]:
        """获取子组织"""
        if not recursive:
            return (
                db.query(Organization)
                .filter(
                    and_(
                        Organization.parent_id == parent_id,
                        not_(Organization.is_deleted),
                    )
                )
                .order_by(Organization.sort_order, Organization.name)
                .all()
            )
        else:
            # 递归获取所有子组织
            children: list[Organization] = []
            direct_children = self.get_children(db, parent_id, False)
            for child in direct_children:
                children.append(child)
                children.extend(self.get_children(db, str(child.id), True))
            return children

    def get_path_to_root(self, db: Session, org_id: str) -> list[Organization]:
        """获取到根节点的路径"""
        path: list[Organization] = []
        current = self.get(db, id=org_id)

        while current:
            path.insert(0, current)
            if current.parent_id:
                current = self.get(db, id=current.parent_id)
            else:
                break

        return path

    def search(
        self, db: Session, keyword: str, skip: int = 0, limit: int = 100
    ) -> list[Organization]:
        """搜索组织"""
        return self.get_multi_with_filters(db, skip=skip, limit=limit, keyword=keyword)


# 创建CRUD实例
organization = CRUDOrganization(Organization)
