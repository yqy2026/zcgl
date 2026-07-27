"""
CRUD操作模块
"""

from ..models.asset import Asset
from ..models.ownership import Ownership
from ..models.project import Project
from ..models.property_certificate import PropertyCertificate
from ..models.rbac import (
    Permission,
    PermissionAuditLog,
    PermissionGrant,
    ResourcePermission,
    UserRoleAssignment,
)
from ..models.system_dictionary import AssetCustomField, SystemDictionary
from ..models.task import AsyncTask, ExcelTaskConfig
from .asset import asset_crud
from .asset_management_history import asset_management_history_crud
from .authz import crud_authz

# Security: Register field whitelists for models
from .field_whitelist import (
    AssetCustomFieldWhitelist,
    AssetWhitelist,
    AsyncTaskWhitelist,
    ExcelTaskConfigWhitelist,
    OwnershipWhitelist,
    PermissionAuditLogWhitelist,
    PermissionGrantWhitelist,
    PermissionWhitelist,
    ProjectWhitelist,
    PropertyCertificateWhitelist,
    ResourcePermissionWhitelist,
    SystemDictionaryWhitelist,
    UserRoleAssignmentWhitelist,
    register_whitelist,
)
from .party import party_crud
from .project import project_crud
from .project_asset import project_asset_crud
from .rbac import permission_grant_crud

# Register whitelists for each model to prevent unauthorized field access
register_whitelist(Asset, AssetWhitelist())
register_whitelist(SystemDictionary, SystemDictionaryWhitelist())
register_whitelist(AssetCustomField, AssetCustomFieldWhitelist())
register_whitelist(Permission, PermissionWhitelist())
register_whitelist(Project, ProjectWhitelist())
register_whitelist(Ownership, OwnershipWhitelist())
register_whitelist(PropertyCertificate, PropertyCertificateWhitelist())
register_whitelist(UserRoleAssignment, UserRoleAssignmentWhitelist())
register_whitelist(ResourcePermission, ResourcePermissionWhitelist())
register_whitelist(PermissionGrant, PermissionGrantWhitelist())
register_whitelist(PermissionAuditLog, PermissionAuditLogWhitelist())
register_whitelist(AsyncTask, AsyncTaskWhitelist())
register_whitelist(ExcelTaskConfig, ExcelTaskConfigWhitelist())

# Additional models can be registered as needed with explicit whitelists
# Security: Models without whitelists will use EmptyWhitelist (deny all fields)
# To enable field access for a model, create a whitelist class and register it:
# from .field_whitelist import ModelNameWhitelist
# from ..models.model_name import ModelName
# register_whitelist(ModelName, ModelNameWhitelist())

__all__ = [
    "asset_crud",
    "asset_management_history_crud",
    "project_crud",
    "party_crud",
    "crud_authz",
    "project_asset_crud",
    "permission_grant_crud",
]
