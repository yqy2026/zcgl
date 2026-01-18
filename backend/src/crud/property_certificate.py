"""
Property Certificate CRUD Operations
产权证CRUD操作
"""

from sqlalchemy.orm import Session

from ..models.property_certificate import PropertyCertificate
from ..schemas.property_certificate import (
    PropertyCertificateCreate,
    PropertyCertificateUpdate,
)
from .base import CRUDBase


class CRUDPropertyCertificate(
    CRUDBase[PropertyCertificate, PropertyCertificateCreate, PropertyCertificateUpdate]
):
    """产权证CRUD操作类"""

    def get_by_certificate_number(
        self, db: Session, certificate_number: str
    ) -> PropertyCertificate | None:
        """
        根据证书编号获取产权证

        Args:
            db: 数据库会话
            certificate_number: 证书编号

        Returns:
            PropertyCertificate | None: 产权证对象或None
        """
        return (
            db.query(PropertyCertificate)
            .filter(PropertyCertificate.certificate_number == certificate_number)
            .first()
        )

    def create_with_owners(
        self,
        db: Session,
        *,
        obj_in: PropertyCertificateCreate,
        owner_ids: list[str] | None = None,
    ) -> PropertyCertificate:
        """
        创建产权证并关联权利人

        Args:
            db: 数据库会话
            obj_in: 创建数据
            owner_ids: 权利人ID列表

        Returns:
            PropertyCertificate: 创建的产权证对象
        """
        from ..models.property_certificate import PropertyOwner

        db_obj = PropertyCertificate(**obj_in.model_dump())
        db.add(db_obj)
        db.flush()  # Flush to get the ID without committing

        # Link owners if provided
        if owner_ids:
            for owner_id in owner_ids:
                owner = (
                    db.query(PropertyOwner).filter(PropertyOwner.id == owner_id).first()
                )
                if owner:
                    db_obj.owners.append(owner)

        db.commit()
        db.refresh(db_obj)
        return db_obj


property_certificate_crud = CRUDPropertyCertificate(PropertyCertificate)
