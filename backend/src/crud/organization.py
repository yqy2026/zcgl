from sqlalchemy import and_, not_
from sqlalchemy.orm import Session

from ..crud.base import CRUDBase
from ..models.organization import Organization
from ..schemas.organization import OrganizationCreate, OrganizationUpdate


class CRUDOrganization(CRUDBase[Organization, OrganizationCreate, OrganizationUpdate]):
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

        stmt = self.query_builder.build_query(
            db_session=db,
            model=Organization,
            filters=filters,
            base_query=query,
            search_query=keyword,
            search_fields=["name", "description"],
            sort_by="level",  # Sort by level, then sort_order
            sort_desc=False,
            skip=skip,
            limit=limit,
        )
        # Note: QueryBuilder only supports one sort field.
        # For complex sort (level asc, sort_order asc), we might need to rely on base query if QB doesn't override.
        # But QB applies order_by(desc(id)) if sort_by not provided.
        # Let's use QB for main list, but for tree operations we might use specific methods.

        result = db.execute(stmt)
        return list(result.scalars().all())

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
            children = []
            direct_children = self.get_children(db, parent_id, False)
            for child in direct_children:
                children.append(child)
                children.extend(self.get_children(db, child.id, True))
            return children

    def get_path_to_root(self, db: Session, org_id: str) -> list[Organization]:
        """获取到根节点的路径"""
        path = []
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
