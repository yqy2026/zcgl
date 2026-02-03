"""
Dynamic permission CRUD operations.
"""

from ..models.dynamic_permission import DynamicPermission
from ..schemas.dynamic_permission import (
    DynamicPermissionCreate,
    DynamicPermissionUpdate,
)
from .base import CRUDBase


class CRUDDynamicPermission(
    CRUDBase[DynamicPermission, DynamicPermissionCreate, DynamicPermissionUpdate]
):
    """CRUD for DynamicPermission."""


dynamic_permission_crud = CRUDDynamicPermission(DynamicPermission)
