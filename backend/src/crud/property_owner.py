"""
Property Owner CRUD
"""

from sqlalchemy.orm import Session
from src.crud.base import CRUDBase
from src.models.property_certificate import PropertyOwner
from src.schemas.property_certificate import PropertyOwnerCreate, PropertyOwnerUpdate


class CRUDPropertyOwner(CRUDBase[PropertyOwner, PropertyOwnerCreate, PropertyOwnerUpdate]):
    """权利人CRUD"""

    def get_by_name(self, db: Session, name: str) -> PropertyOwner | None:
        """按姓名查询"""
        return db.query(PropertyOwner).filter(PropertyOwner.name == name).first()


property_owner_crud = CRUDPropertyOwner(PropertyOwner)