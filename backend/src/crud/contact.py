"""
联系人 CRUD 操作 - 支持敏感字段加密
"""

from typing import Any

from sqlalchemy.orm import Session

from ..crud.asset import SensitiveDataHandler
from ..models.contact import Contact, ContactType


def _set_attr(obj: Any, attr: str, value: Any) -> None:
    """安全地设置 ORM 对象属性，避免 mypy 类型错误"""
    object.__setattr__(obj, attr, value)


class ContactCRUD:
    """联系人 CRUD 操作类 - 支持敏感字段加密"""

    def __init__(self) -> None:
        """初始化联系人CRUD - 配置敏感字段"""
        self.sensitive_data_handler = SensitiveDataHandler(
            searchable_fields={
                "phone",  # 手机号码 - 敏感，需要搜索
                "office_phone",  # 办公电话 - 敏感，需要搜索
            }
        )

    def _build_entity_query(
        self,
        db: Session,
        *,
        entity_type: str,
        entity_id: str | None = None,
        entity_ids: list[str] | None = None,
        is_active: bool | None = True,
        is_primary: bool | None = None,
        contact_type: ContactType | None = None,
    ) -> Any:
        query = db.query(Contact).filter(Contact.entity_type == entity_type)

        if entity_id is not None:
            query = query.filter(Contact.entity_id == entity_id)

        if entity_ids is not None:
            query = query.filter(Contact.entity_id.in_(entity_ids))

        if is_active is not None:
            query = query.filter(Contact.is_active.is_(is_active))

        if is_primary is not None:
            query = query.filter(Contact.is_primary.is_(is_primary))

        if contact_type:
            query = query.filter(Contact.contact_type == contact_type)

        return query

    def _decrypt_contact(self, obj: Contact | None) -> Contact | None:
        if obj is not None:
            self.sensitive_data_handler.decrypt_data(obj.__dict__)
        return obj

    def _decrypt_contacts(self, results: list[Contact]) -> list[Contact]:
        for contact in results:
            self.sensitive_data_handler.decrypt_data(contact.__dict__)
        return results

    def get(self, db: Session, id: str) -> Contact | None:
        """根据ID获取联系人 - 解密敏感字段"""
        obj = db.query(Contact).filter(Contact.id == id).first()
        return self._decrypt_contact(obj)

    def get_multi(
        self,
        db: Session,
        entity_type: str,
        entity_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[Contact], int]:
        """获取指定实体的所有联系人 - 解密敏感字段"""
        query = self._build_entity_query(
            db,
            entity_type=entity_type,
            entity_id=entity_id,
            is_active=True,
        )

        total = query.count()
        contacts = (
            query.order_by(Contact.is_primary.desc(), Contact.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        return self._decrypt_contacts(contacts), total

    def get_primary(
        self, db: Session, entity_type: str, entity_id: str
    ) -> Contact | None:
        """获取指定实体的主要联系人 - 解密敏感字段"""
        obj = self._build_entity_query(
            db,
            entity_type=entity_type,
            entity_id=entity_id,
            is_active=True,
            is_primary=True,
        ).first()
        return self._decrypt_contact(obj)

    def create(self, db: Session, obj_in: dict[str, Any]) -> Contact:
        """创建联系人 - 加密敏感字段"""
        # 加密敏感字段
        encrypted_data = self.sensitive_data_handler.encrypt_data(obj_in.copy())

        # 如果设置为主要联系人，先取消该实体的其他主要联系人
        if encrypted_data.get("is_primary", False):
            db.query(Contact).filter(
                Contact.entity_type == encrypted_data["entity_type"],
                Contact.entity_id == encrypted_data["entity_id"],
                Contact.is_primary.is_(True),
            ).update({"is_primary": False}, synchronize_session=False)

        db_obj = Contact(**encrypted_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)

        # 解密后返回
        self.sensitive_data_handler.decrypt_data(db_obj.__dict__)
        return db_obj

    def update(self, db: Session, db_obj: Contact, obj_in: dict[str, Any]) -> Contact:
        """更新联系人 - 加密新的敏感字段值"""
        # 加密敏感字段
        encrypted_data = {}
        for field_name, value in obj_in.items():
            if field_name in self.sensitive_data_handler.ALL_PII_FIELDS:
                encrypted_data[field_name] = self.sensitive_data_handler.encrypt_field(
                    field_name, value
                )
            else:
                encrypted_data[field_name] = value

        # 如果设置为主要联系人，先取消其他主要联系人
        if encrypted_data.get("is_primary", False) and not db_obj.is_primary:
            db.query(Contact).filter(
                Contact.entity_type == db_obj.entity_type,
                Contact.entity_id == db_obj.entity_id,
                Contact.is_primary.is_(True),
            ).update({"is_primary": False}, synchronize_session=False)

        for field, value in encrypted_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)

        db.commit()
        db.refresh(db_obj)

        # 解密后返回
        self.sensitive_data_handler.decrypt_data(db_obj.__dict__)
        return db_obj

    def delete(self, db: Session, id: str) -> Contact | None:
        """软删除联系人（设置is_active=False）"""
        obj = self.get(db, id)
        if obj:
            _set_attr(obj, "is_active", False)
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
        """批量获取联系人 - 解密敏感字段"""
        query = self._build_entity_query(
            db,
            entity_type=entity_type,
            entity_ids=entity_ids,
            is_active=True,
            contact_type=contact_type,
        )
        results = query.all()
        return self._decrypt_contacts(results)


contact_crud = ContactCRUD()
