"""
CRUD操作模块
"""

from ..models.asset import Asset, AssetCustomField, Ownership, Project, SystemDictionary
from ..models.collection import CollectionRecord
from ..models.dynamic_permission import DynamicPermission
from ..models.llm_prompt import PromptTemplate
from ..models.organization import Organization
from ..models.property_certificate import PropertyCertificate, PropertyOwner
from ..models.rbac import PermissionAuditLog, ResourcePermission, UserRoleAssignment
from ..models.rbac import Permission
from ..models.rent_contract import RentContract, RentLedger, RentTerm
from ..models.task import AsyncTask, ExcelTaskConfig
from .asset import asset_crud
from .collection import collection_crud
from .dynamic_permission import dynamic_permission_crud

# Security: Register field whitelists for models
from .field_whitelist import (
    AssetCustomFieldWhitelist,
    AssetWhitelist,
    CollectionRecordWhitelist,
    DynamicPermissionWhitelist,
    ExcelTaskConfigWhitelist,
    OrganizationWhitelist,
    OwnershipWhitelist,
    AsyncTaskWhitelist,
    PermissionWhitelist,
    PermissionAuditLogWhitelist,
    ProjectWhitelist,
    PromptTemplateWhitelist,
    PropertyCertificateWhitelist,
    PropertyOwnerWhitelist,
    RentLedgerWhitelist,
    RentTermWhitelist,
    ResourcePermissionWhitelist,
    RentContractWhitelist,
    SystemDictionaryWhitelist,
    UserRoleAssignmentWhitelist,
    register_whitelist,
)
from .project import project_crud
from .rent_contract import rent_contract, rent_ledger, rent_term
from .llm_prompt import prompt_template_crud

# Register whitelists for each model to prevent unauthorized field access
register_whitelist(Asset, AssetWhitelist())
register_whitelist(RentContract, RentContractWhitelist())
register_whitelist(Ownership, OwnershipWhitelist())
register_whitelist(SystemDictionary, SystemDictionaryWhitelist())
register_whitelist(AssetCustomField, AssetCustomFieldWhitelist())
register_whitelist(Permission, PermissionWhitelist())
register_whitelist(CollectionRecord, CollectionRecordWhitelist())
register_whitelist(DynamicPermission, DynamicPermissionWhitelist())
register_whitelist(PromptTemplate, PromptTemplateWhitelist())
register_whitelist(Project, ProjectWhitelist())
register_whitelist(Organization, OrganizationWhitelist())
register_whitelist(PropertyCertificate, PropertyCertificateWhitelist())
register_whitelist(PropertyOwner, PropertyOwnerWhitelist())
register_whitelist(RentTerm, RentTermWhitelist())
register_whitelist(RentLedger, RentLedgerWhitelist())
register_whitelist(UserRoleAssignment, UserRoleAssignmentWhitelist())
register_whitelist(ResourcePermission, ResourcePermissionWhitelist())
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
    "collection_crud",
    "dynamic_permission_crud",
    "project_crud",
    "prompt_template_crud",
    "rent_contract",
    "rent_ledger",
    "rent_term",
]
