"""
Property Certificate CRUD
"""

from sqlalchemy.orm import Session
from src.crud.base import CRUDBase
from src.models.property_certificate import PropertyCertificate
from src.schemas.property_certificate import PropertyCertificateCreate, PropertyCertificateUpdate


class CRUDPropertyCertificate(
    CRUDBase[PropertyCertificate, PropertyCertificateCreate, PropertyCertificateUpdate]
):
    """产权证CRUD"""

    def get_by_certificate_number(self, db: Session, number: str) -> PropertyCertificate | None:
        """按证书编号查询"""
        return db.query(PropertyCertificate).filter(PropertyCertificate.certificate_number == number).first()


property_certificate_crud = CRUDPropertyCertificate(PropertyCertificate)