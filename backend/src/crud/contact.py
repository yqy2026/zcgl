"""
联系人 CRUD 操作
"""

from sqlalchemy.orm import Session

from ..models.contact import Contact, ContactType


class ContactCRUD:
    """联系人 CRUD 操作类"""

    def get(self, db: Session, id: str) -> Contact | None:
        """根据ID获取联系人"""
        return db.query(Contact).filter(Contact.id == id).first()

    def get_multi(
        self,
        db: Session,
        entity_type: str,
        entity_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[Contact], int]:
        """获取指定实体的所有联系人"""
        query = db.query(Contact).filter(
            Contact.entity_type == entity_type,
            Contact.entity_id == entity_id,
            Contact.is_active == True,
        )

        total = query.count()
        contacts = (
            query.order_by(Contact.is_primary.desc(), Contact.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        return contacts, total

    def get_primary(
        self, db: Session, entity_type: str, entity_id: str
    ) -> Contact | None:
        """获取指定实体的主要联系人"""
        return (
            db.query(Contact)
            .filter(
                Contact.entity_type == entity_type,
                Contact.entity_id == entity_id,
                Contact.is_primary == True,
                Contact.is_active == True,
            )
            .first()
        )

    def create(self, db: Session, obj_in: dict) -> Contact:
        """创建联系人"""
        # 如果设置为主要联系人，先取消该实体的其他主要联系人
        if obj_in.get("is_primary", False):
            db.query(Contact).filter(
                Contact.entity_type == obj_in["entity_type"],
                Contact.entity_id == obj_in["entity_id"],
                Contact.is_primary == True,
            ).update({"is_primary": False}, synchronize_session=False)

        db_obj = Contact(**obj_in)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, db_obj: Contact, obj_in: dict) -> Contact:
        """更新联系人"""
        # 如果设置为主要联系人，先取消其他主要联系人
        if obj_in.get("is_primary", False) and not db_obj.is_primary:
            db.query(Contact).filter(
                Contact.entity_type == db_obj.entity_type,
                Contact.entity_id == db_obj.entity_id,
                Contact.is_primary == True,
            ).update({"is_primary": False}, synchronize_session=False)

        for field, value in obj_in.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)

        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: str) -> Contact:
        """软删除联系人（设置is_active=False）"""
        obj = self.get(db, id)
        if obj:
            obj.is_active = False
            db.commit()
            db.refresh(obj)
        return obj

    def get_multi_by_type(
        self,
        db: Session,
        entity_type: str,
        entity_ids: list[str],
        contact_type: ContactType | None = None,
    ) -> list[Contact]:
        """批量获取联系人"""
        query = db.query(Contact).filter(
            Contact.entity_type == entity_type,
            Contact.entity_id.in_(entity_ids),
            Contact.is_active == True,
        )

        if contact_type:
            query = query.filter(Contact.contact_type == contact_type)

        return query.all()


contact_crud = ContactCRUD()
