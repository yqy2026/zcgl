from sqlalchemy.orm import Session

from ..models.organization import OrganizationHistory


class OrganizationHistoryCRUD:
    """组织历史 CRUD 操作"""

    def get_multi(
        self, db: Session, org_id: str, skip: int = 0, limit: int = 100
    ) -> list[OrganizationHistory]:
        """获取组织历史列表"""
        items, _ = self.get_multi_with_count(
            db=db, org_id=org_id, skip=skip, limit=limit
        )
        return items

    def get_multi_with_count(
        self, db: Session, org_id: str, skip: int = 0, limit: int = 100
    ) -> tuple[list[OrganizationHistory], int]:
        """获取组织历史列表与总数"""
        query = db.query(OrganizationHistory).filter(
            OrganizationHistory.organization_id == org_id
        )
        total = query.count()
        items = (
            query.order_by(OrganizationHistory.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return items, total
