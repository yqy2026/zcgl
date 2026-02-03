"""
Collection CRUD operations.
"""

from ..models.collection import CollectionRecord
from ..schemas.collection import CollectionRecordCreate, CollectionRecordUpdate
from .base import CRUDBase


class CRUDCollectionRecord(
    CRUDBase[CollectionRecord, CollectionRecordCreate, CollectionRecordUpdate]
):
    """CRUD for CollectionRecord."""


collection_crud = CRUDCollectionRecord(CollectionRecord)
