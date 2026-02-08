"""
Field Whitelist Configuration for QueryBuilder

Defines which fields can be safely used for filtering, searching, and sorting
in dynamic queries. Prevents unauthorized access to sensitive fields.

Security Design:
- Separate whitelists for filter, search, and sort operations
- Explicit block lists for sensitive fields
- Per-model configurations for flexibility
- Registry pattern for centralized management
"""

import logging
from typing import ClassVar

from ..constants.business_constants import DateTimeFields

logger = logging.getLogger(__name__)


class ModelFieldWhitelist:
    """
    Field whitelist configuration for a single model.

    Design:
    - Separate lists for filter, search, sort operations
    - Explicit control over each operation type
    - Easy to extend with new operations
    """

    # Fields allowed for equality/range filters
    filter_fields: ClassVar[set[str]] = set()

    # Fields allowed for text search (ILIKE operations)
    search_fields: ClassVar[set[str]] = set()

    # Fields allowed for sorting
    sort_fields: ClassVar[set[str]] = set()

    # Blocked fields (explicitly denied, even if in model)
    blocked_fields: ClassVar[set[str]] = set()

    def can_filter(self, field_name: str) -> bool:
        """Check if field can be used for filtering."""
        if field_name in self.blocked_fields:
            return False
        return field_name in self.filter_fields

    def can_search(self, field_name: str) -> bool:
        """Check if field can be used for searching."""
        if field_name in self.blocked_fields:
            return False
        return field_name in self.search_fields

    def can_sort(self, field_name: str) -> bool:
        """Check if field can be used for sorting."""
        if field_name in self.blocked_fields:
            return False
        return field_name in self.sort_fields


# ============================================================================
# Asset Model Whitelist
# ============================================================================


class AssetWhitelist(ModelFieldWhitelist):
    """
    Whitelist for Asset model.

    Security considerations:
    - BLOCKED: PII fields and operational intelligence fields
    - ALLOWED: Basic classification and status fields
    - ALLOWED: Area/date/public text fields for list retrieval
    """

    # Safe filtering fields (public/internal metadata)
    filter_fields: ClassVar[set[str]] = {
        # Basic identifiers
        "id",
        # Primary property identifier (public name)
        "property_name",
        # Public classification fields
        "ownership_status",
        "property_nature",
        "usage_status",
        "business_category",  # High-level business classification
        "management_entity",
        "is_litigated",
        "data_status",
        "is_active",
        # Project/ownership references (IDs only, not names)
        "project_id",
        "ownership_id",
        # Area fields (public metrics)
        "land_area",
        "actual_property_area",
        "rentable_area",
        "rented_area",
        "cached_occupancy_rate",
        "non_commercial_area",
        # Boolean flags
        "include_in_occupancy_rate",
        "is_sublease",
        # Status enums
        "tenant_type",
        # System fields
        "version",
        "tags",
        # Date fields (non-sensitive)
        DateTimeFields.CREATED_AT,
        DateTimeFields.UPDATED_AT,
        # Usage classification
        "certificated_usage",
        "actual_usage",
        # Business model
        "business_model",
    }

    # Search fields (text fields for partial matching)
    search_fields: ClassVar[set[str]] = {
        "property_name",  # Primary identifier
        "address",  # Address is public record for properties
        "project_name",  # Project names are public
        "notes",  # User's own notes
        "property_nature",
        "usage_status",
        "ownership_status",
        "certificated_usage",
        "actual_usage",
        "business_model",
        "business_category",
    }

    # Sort fields (numeric/date fields for ordering)
    sort_fields: ClassVar[set[str]] = {
        # Time-based sorting
        DateTimeFields.CREATED_AT,
        DateTimeFields.UPDATED_AT,
        # Numeric sorting
        "land_area",
        "actual_property_area",
        "rentable_area",
        "rented_area",
        "cached_occupancy_rate",
        # Alphabetic sorting
        "property_name",
        "project_name",
        # Version tracking
        "version",
    }

    # BLOCKED: Never allowed in dynamic queries
    blocked_fields: ClassVar[set[str]] = {
        # PII - Personal identifiable information
        "manager_name",  # PII: Manager name
        "tenant_name",  # PII: Tenant name
        "project_phone",  # PII: Phone number (encrypted)
        # Operational intelligence
        "operation_status",  # Business sensitive
        "lease_contract_number",  # Contract details
        # Audit trail (should not be filterable by users)
        "created_by",  # User discovery risk
        "updated_by",  # User discovery risk
    }


# ============================================================================
# RentContract Whitelist
# ============================================================================


class RentContractWhitelist(ModelFieldWhitelist):
    """Whitelist for RentContract model."""

    filter_fields: ClassVar[set[str]] = {
        # Basic identifiers
        "id",
        # Contract fields
        "contract_number",
        "contract_status",
        # References
        "ownership_id",
        # Date fields
        "start_date",
        "end_date",
        # Payment terms
        "payment_cycle",
        "rent_increase_rate",
        # Booleans
        "is_active",
        # System fields
        "created_at",
        "updated_at",
    }

    search_fields: ClassVar[set[str]] = {
        "contract_number",
        "notes",
    }

    sort_fields: ClassVar[set[str]] = {
        # Time-based
        "created_at",
        "updated_at",
        "start_date",
        "end_date",
        # Financial (sorting allowed)
        "monthly_rent_base",
        "total_deposit",
    }

    blocked_fields: ClassVar[set[str]] = {
        # PII (even if encrypted, should not be discoverable)
        "owner_phone",
        "tenant_phone",
        "tenant_name",  # Business sensitive
        # Audit trail
        "created_by",
        "updated_by",
    }


# ============================================================================
# Ownership Whitelist
# ============================================================================


class OwnershipWhitelist(ModelFieldWhitelist):
    """Whitelist for Ownership model."""

    filter_fields: ClassVar[set[str]] = {
        # Basic identifiers
        "id",
        # Name fields
        "name",
        "short_name",
        "code",
        # Status
        "is_active",
        "data_status",
        # System
        "created_at",
        "updated_at",
    }

    search_fields: ClassVar[set[str]] = {
        "name",
        "short_name",
        "notes",
    }

    sort_fields: ClassVar[set[str]] = {
        "name",
        "code",
        "created_at",
        "updated_at",
    }

    blocked_fields: ClassVar[set[str]] = {
        # Contact information
        "address",
        # Audit trail
        "created_by",
        "updated_by",
    }


class RoleWhitelist(ModelFieldWhitelist):
    filter_fields: ClassVar[set[str]] = {
        "id",
        "name",
        "display_name",
        "category",
        "is_active",
        "organization_id",
        "is_system_role",
        "scope",
        "scope_id",
        "level",
        "created_at",
        "updated_at",
    }

    search_fields: ClassVar[set[str]] = {
        "name",
        "display_name",
        "description",
    }

    sort_fields: ClassVar[set[str]] = {
        "id",
        "name",
        "display_name",
        "level",
        "created_at",
        "updated_at",
    }

    blocked_fields: ClassVar[set[str]] = {
        "created_by",
        "updated_by",
    }


# ============================================================================
# SystemDictionary Whitelist
# ============================================================================


class SystemDictionaryWhitelist(ModelFieldWhitelist):
    """Whitelist for SystemDictionary model."""

    filter_fields: ClassVar[set[str]] = {
        "id",
        "dict_type",
        "dict_code",
        "dict_label",
        "dict_value",
        "is_active",
        DateTimeFields.CREATED_AT,
        DateTimeFields.UPDATED_AT,
    }

    search_fields: ClassVar[set[str]] = {
        "dict_type",
        "dict_code",
        "dict_label",
        "dict_value",
    }

    sort_fields: ClassVar[set[str]] = {
        "sort_order",
        "dict_label",
        "dict_code",
        DateTimeFields.CREATED_AT,
        DateTimeFields.UPDATED_AT,
    }

    blocked_fields: ClassVar[set[str]] = set()


# ============================================================================
# AssetCustomField Whitelist
# ============================================================================


class AssetCustomFieldWhitelist(ModelFieldWhitelist):
    """Whitelist for AssetCustomField model."""

    filter_fields: ClassVar[set[str]] = {
        "id",
        "field_name",
        "display_name",
        "field_type",
        "is_required",
        "is_active",
        DateTimeFields.CREATED_AT,
        DateTimeFields.UPDATED_AT,
    }

    search_fields: ClassVar[set[str]] = {
        "field_name",
        "display_name",
        "description",
        "help_text",
    }

    sort_fields: ClassVar[set[str]] = {
        "sort_order",
        "field_name",
        "display_name",
        DateTimeFields.CREATED_AT,
        DateTimeFields.UPDATED_AT,
    }

    blocked_fields: ClassVar[set[str]] = set()


# ============================================================================
# Permission Whitelist
# ============================================================================


class PermissionWhitelist(ModelFieldWhitelist):
    """Whitelist for Permission model."""

    filter_fields: ClassVar[set[str]] = {
        "id",
        "resource",
        "action",
        "is_system_permission",
        "requires_approval",
        "max_level",
        DateTimeFields.CREATED_AT,
        DateTimeFields.UPDATED_AT,
    }

    search_fields: ClassVar[set[str]] = {
        "name",
        "display_name",
        "description",
    }

    sort_fields: ClassVar[set[str]] = {
        "resource",
        "action",
        "name",
        DateTimeFields.CREATED_AT,
        DateTimeFields.UPDATED_AT,
    }

    blocked_fields: ClassVar[set[str]] = set()


# ============================================================================
# CollectionRecord Whitelist
# ============================================================================


class CollectionRecordWhitelist(ModelFieldWhitelist):
    """Whitelist for CollectionRecord model."""

    filter_fields: ClassVar[set[str]] = {
        "id",
        "ledger_id",
        "contract_id",
        "collection_method",
        "collection_status",
        "collection_date",
        "promised_date",
        "next_follow_up_date",
        "operator_id",
        DateTimeFields.CREATED_AT,
        DateTimeFields.UPDATED_AT,
    }

    search_fields: ClassVar[set[str]] = {
        "operator",
    }

    sort_fields: ClassVar[set[str]] = {
        "collection_date",
        "promised_date",
        "next_follow_up_date",
        "promised_amount",
        "actual_payment_amount",
        DateTimeFields.CREATED_AT,
        DateTimeFields.UPDATED_AT,
    }

    blocked_fields: ClassVar[set[str]] = {
        "contact_phone",
        "contacted_person",
        "collection_notes",
    }


# ============================================================================
# PromptTemplate Whitelist
# ============================================================================


class PromptTemplateWhitelist(ModelFieldWhitelist):
    """Whitelist for PromptTemplate model."""

    filter_fields: ClassVar[set[str]] = {
        "id",
        "name",
        "doc_type",
        "provider",
        "status",
        "version",
        "created_by",
        "current_version_id",
        "parent_id",
        DateTimeFields.CREATED_AT,
        DateTimeFields.UPDATED_AT,
    }

    search_fields: ClassVar[set[str]] = {
        "name",
        "description",
    }

    sort_fields: ClassVar[set[str]] = {
        "name",
        "version",
        "avg_accuracy",
        "avg_confidence",
        "total_usage",
        DateTimeFields.CREATED_AT,
        DateTimeFields.UPDATED_AT,
    }

    blocked_fields: ClassVar[set[str]] = {
        "system_prompt",
        "user_prompt_template",
        "few_shot_examples",
        "tags",
    }


# ============================================================================
# Project Whitelist
# ============================================================================


class ProjectWhitelist(ModelFieldWhitelist):
    """Whitelist for Project model."""

    filter_fields: ClassVar[set[str]] = {
        "id",
        "name",
        "short_name",
        "code",
        "project_type",
        "project_scale",
        "project_status",
        "start_date",
        "end_date",
        "expected_completion_date",
        "actual_completion_date",
        "city",
        "district",
        "province",
        "management_entity",
        "ownership_entity",
        "is_active",
        "data_status",
        DateTimeFields.CREATED_AT,
        DateTimeFields.UPDATED_AT,
    }

    search_fields: ClassVar[set[str]] = {
        "name",
        "short_name",
        "code",
        "address",
        "city",
        "district",
        "province",
    }

    sort_fields: ClassVar[set[str]] = {
        "name",
        "code",
        "project_status",
        "start_date",
        "end_date",
        DateTimeFields.CREATED_AT,
        DateTimeFields.UPDATED_AT,
    }

    blocked_fields: ClassVar[set[str]] = {
        "project_phone",
        "project_email",
    }


# ============================================================================
# Organization Whitelist
# ============================================================================


class OrganizationWhitelist(ModelFieldWhitelist):
    """Whitelist for Organization model."""

    filter_fields: ClassVar[set[str]] = {
        "id",
        "name",
        "code",
        "level",
        "sort_order",
        "type",
        "status",
        "parent_id",
        "path",
        "is_deleted",
        DateTimeFields.CREATED_AT,
        DateTimeFields.UPDATED_AT,
    }

    search_fields: ClassVar[set[str]] = {
        "name",
        "code",
        "description",
        "path",
    }

    sort_fields: ClassVar[set[str]] = {
        "name",
        "code",
        "level",
        "sort_order",
        DateTimeFields.CREATED_AT,
        DateTimeFields.UPDATED_AT,
    }

    blocked_fields: ClassVar[set[str]] = set()


# ============================================================================
# PropertyCertificate Whitelist
# ============================================================================


class PropertyCertificateWhitelist(ModelFieldWhitelist):
    """Whitelist for PropertyCertificate model."""

    filter_fields: ClassVar[set[str]] = {
        "id",
        "certificate_number",
        "certificate_type",
        "extraction_source",
        "is_verified",
        "registration_date",
        "property_type",
        "land_use_type",
        "land_use_term_start",
        "land_use_term_end",
        DateTimeFields.CREATED_AT,
        DateTimeFields.UPDATED_AT,
    }

    search_fields: ClassVar[set[str]] = {
        "certificate_number",
        "property_address",
        "property_type",
        "land_use_type",
        "co_ownership",
    }

    sort_fields: ClassVar[set[str]] = {
        "certificate_number",
        "extraction_confidence",
        "registration_date",
        DateTimeFields.CREATED_AT,
        DateTimeFields.UPDATED_AT,
    }

    blocked_fields: ClassVar[set[str]] = {
        "restrictions",
        "remarks",
    }


class PropertyOwnerWhitelist(ModelFieldWhitelist):
    """Whitelist for PropertyOwner model."""

    filter_fields: ClassVar[set[str]] = {
        "id",
        "owner_type",
        "name",
        "organization_id",
        DateTimeFields.CREATED_AT,
        DateTimeFields.UPDATED_AT,
    }

    search_fields: ClassVar[set[str]] = {
        "name",
        "address",
    }

    sort_fields: ClassVar[set[str]] = {
        "name",
        DateTimeFields.CREATED_AT,
        DateTimeFields.UPDATED_AT,
    }

    blocked_fields: ClassVar[set[str]] = {
        "id_number",
        "phone",
    }


# ============================================================================
# RentTerm / RentLedger Whitelist
# ============================================================================


class RentTermWhitelist(ModelFieldWhitelist):
    """Whitelist for RentTerm model."""

    filter_fields: ClassVar[set[str]] = {
        "id",
        "contract_id",
        "start_date",
        "end_date",
        "monthly_rent",
        "total_monthly_amount",
        DateTimeFields.CREATED_AT,
        DateTimeFields.UPDATED_AT,
    }

    search_fields: ClassVar[set[str]] = {
        "rent_description",
    }

    sort_fields: ClassVar[set[str]] = {
        "start_date",
        "end_date",
        "monthly_rent",
        "total_monthly_amount",
        DateTimeFields.CREATED_AT,
        DateTimeFields.UPDATED_AT,
    }

    blocked_fields: ClassVar[set[str]] = set()


class RentLedgerWhitelist(ModelFieldWhitelist):
    """Whitelist for RentLedger model."""

    filter_fields: ClassVar[set[str]] = {
        "id",
        "contract_id",
        "asset_id",
        "ownership_id",
        "year_month",
        "due_date",
        "payment_status",
        "data_status",
        DateTimeFields.CREATED_AT,
        DateTimeFields.UPDATED_AT,
    }

    search_fields: ClassVar[set[str]] = set()

    sort_fields: ClassVar[set[str]] = {
        "year_month",
        "due_date",
        "due_amount",
        "paid_amount",
        "overdue_amount",
        DateTimeFields.CREATED_AT,
        DateTimeFields.UPDATED_AT,
    }

    blocked_fields: ClassVar[set[str]] = {
        "payment_reference",
        "notes",
    }


# ============================================================================
# RBAC Whitelists
# ============================================================================


class UserRoleAssignmentWhitelist(ModelFieldWhitelist):
    """Whitelist for UserRoleAssignment model."""

    filter_fields: ClassVar[set[str]] = {
        "id",
        "user_id",
        "role_id",
        "assigned_by",
        "assigned_at",
        "expires_at",
        "is_active",
        DateTimeFields.CREATED_AT,
        DateTimeFields.UPDATED_AT,
    }

    search_fields: ClassVar[set[str]] = set()

    sort_fields: ClassVar[set[str]] = {
        "assigned_at",
        "expires_at",
        DateTimeFields.CREATED_AT,
        DateTimeFields.UPDATED_AT,
    }

    blocked_fields: ClassVar[set[str]] = {
        "reason",
        "notes",
        "context",
    }


class ResourcePermissionWhitelist(ModelFieldWhitelist):
    """Whitelist for ResourcePermission model."""

    filter_fields: ClassVar[set[str]] = {
        "id",
        "resource_type",
        "resource_id",
        "user_id",
        "role_id",
        "permission_id",
        "permission_level",
        "granted_at",
        "expires_at",
        "is_active",
        DateTimeFields.CREATED_AT,
        DateTimeFields.UPDATED_AT,
    }

    search_fields: ClassVar[set[str]] = {
        "resource_type",
    }

    sort_fields: ClassVar[set[str]] = {
        "granted_at",
        "expires_at",
        DateTimeFields.CREATED_AT,
        DateTimeFields.UPDATED_AT,
    }

    blocked_fields: ClassVar[set[str]] = {
        "granted_by",
        "reason",
        "conditions",
    }


class PermissionGrantWhitelist(ModelFieldWhitelist):
    """Whitelist for PermissionGrant model."""

    filter_fields: ClassVar[set[str]] = {
        "id",
        "user_id",
        "permission_id",
        "grant_type",
        "effect",
        "scope",
        "scope_id",
        "starts_at",
        "expires_at",
        "priority",
        "is_active",
        "source_type",
        "source_id",
        DateTimeFields.CREATED_AT,
        DateTimeFields.UPDATED_AT,
    }

    search_fields: ClassVar[set[str]] = {
        "grant_type",
        "scope",
        "source_type",
    }

    sort_fields: ClassVar[set[str]] = {
        "priority",
        "starts_at",
        "expires_at",
        DateTimeFields.CREATED_AT,
        DateTimeFields.UPDATED_AT,
    }

    blocked_fields: ClassVar[set[str]] = {
        "conditions",
        "granted_by",
        "reason",
        "revoked_at",
        "revoked_by",
    }


class PermissionAuditLogWhitelist(ModelFieldWhitelist):
    """Whitelist for PermissionAuditLog model."""

    filter_fields: ClassVar[set[str]] = {
        "id",
        "action",
        "resource_type",
        "resource_id",
        "user_id",
        "operator_id",
        DateTimeFields.CREATED_AT,
    }

    search_fields: ClassVar[set[str]] = set()

    sort_fields: ClassVar[set[str]] = {
        DateTimeFields.CREATED_AT,
    }

    blocked_fields: ClassVar[set[str]] = {
        "old_permissions",
        "new_permissions",
        "ip_address",
        "user_agent",
        "reason",
    }


# ============================================================================
# Task Whitelists
# ============================================================================


class AsyncTaskWhitelist(ModelFieldWhitelist):
    """Whitelist for AsyncTask model."""

    filter_fields: ClassVar[set[str]] = {
        "id",
        "task_type",
        "status",
        "created_at",
        "started_at",
        "completed_at",
        "progress",
        "is_active",
        "user_id",
    }

    search_fields: ClassVar[set[str]] = {
        "title",
        "description",
    }

    sort_fields: ClassVar[set[str]] = {
        "created_at",
        "started_at",
        "completed_at",
        "progress",
    }

    blocked_fields: ClassVar[set[str]] = {
        "result_data",
        "error_message",
        "parameters",
        "config",
        "session_id",
    }


class ExcelTaskConfigWhitelist(ModelFieldWhitelist):
    """Whitelist for ExcelTaskConfig model."""

    filter_fields: ClassVar[set[str]] = {
        "id",
        "config_name",
        "config_type",
        "task_type",
        "is_default",
        "is_active",
        "created_by",
        DateTimeFields.CREATED_AT,
        DateTimeFields.UPDATED_AT,
    }

    search_fields: ClassVar[set[str]] = {
        "config_name",
    }

    sort_fields: ClassVar[set[str]] = {
        "config_name",
        DateTimeFields.CREATED_AT,
        DateTimeFields.UPDATED_AT,
    }

    blocked_fields: ClassVar[set[str]] = {
        "field_mapping",
        "validation_rules",
        "format_config",
    }


# Registry mapping model classes to their whitelist configurations
WHITELIST_REGISTRY: dict[type, ModelFieldWhitelist] = {}


def register_whitelist(model_class: type, whitelist: ModelFieldWhitelist) -> None:
    """
    Register a whitelist configuration for a model.

    Args:
        model_class: The SQLAlchemy model class
        whitelist: The whitelist configuration instance
    """
    WHITELIST_REGISTRY[model_class] = whitelist
    logger.info(f"Registered whitelist for model: {model_class.__name__}")


def _ensure_whitelists_registered() -> None:
    if WHITELIST_REGISTRY:
        return
    try:
        from ..models.asset import Asset
        from ..models.collection import CollectionRecord
        from ..models.llm_prompt import PromptTemplate
        from ..models.organization import Organization
        from ..models.ownership import Ownership
        from ..models.project import Project
        from ..models.property_certificate import PropertyCertificate, PropertyOwner
        from ..models.rbac import (
            Permission,
            PermissionAuditLog,
            PermissionGrant,
            ResourcePermission,
            Role,
            UserRoleAssignment,
        )
        from ..models.rent_contract import RentContract, RentLedger, RentTerm
        from ..models.system_dictionary import AssetCustomField, SystemDictionary
        from ..models.task import AsyncTask, ExcelTaskConfig

        register_whitelist(Asset, AssetWhitelist())
        register_whitelist(Ownership, OwnershipWhitelist())
        register_whitelist(RentContract, RentContractWhitelist())
        register_whitelist(Role, RoleWhitelist())
        register_whitelist(SystemDictionary, SystemDictionaryWhitelist())
        register_whitelist(AssetCustomField, AssetCustomFieldWhitelist())
        register_whitelist(Permission, PermissionWhitelist())
        register_whitelist(CollectionRecord, CollectionRecordWhitelist())
        register_whitelist(PromptTemplate, PromptTemplateWhitelist())
        register_whitelist(Project, ProjectWhitelist())
        register_whitelist(Organization, OrganizationWhitelist())
        register_whitelist(PropertyCertificate, PropertyCertificateWhitelist())
        register_whitelist(PropertyOwner, PropertyOwnerWhitelist())
        register_whitelist(RentTerm, RentTermWhitelist())
        register_whitelist(RentLedger, RentLedgerWhitelist())
        register_whitelist(UserRoleAssignment, UserRoleAssignmentWhitelist())
        register_whitelist(ResourcePermission, ResourcePermissionWhitelist())
        register_whitelist(PermissionGrant, PermissionGrantWhitelist())
        register_whitelist(PermissionAuditLog, PermissionAuditLogWhitelist())
        register_whitelist(AsyncTask, AsyncTaskWhitelist())
        register_whitelist(ExcelTaskConfig, ExcelTaskConfigWhitelist())
    except Exception as exc:
        logger.warning(f"Failed to initialize whitelist registry: {exc}")


def get_whitelist_for_model(model_class: type) -> ModelFieldWhitelist:
    """
    Get whitelist configuration for a model.

    Returns EmptyWhitelist if no specific configuration exists
    (security-first approach: deny all fields by default).

    Args:
        model_class: The SQLAlchemy model class

    Returns:
        ModelFieldWhitelist instance for the model
    """
    _ensure_whitelists_registered()
    if model_class in WHITELIST_REGISTRY:
        return WHITELIST_REGISTRY[model_class]

    # Return empty whitelist for security (deny all fields by default)
    # Models must have explicit whitelist configuration to allow field access
    logger.info(
        f"No whitelist found for {model_class.__name__}. "
        "Using EmptyWhitelist (denies all fields). "
        "Define explicit whitelist to enable field access."
    )
    return EmptyWhitelist()


# ============================================================================
# Special Whitelist Types
# ============================================================================


class EmptyWhitelist(ModelFieldWhitelist):
    """
    Strict whitelist that denies all fields.

    Use this after migration to enforce explicit whitelists.
    """

    def can_filter(self, field_name: str) -> bool:
        return False  # Deny all unless explicitly allowed

    def can_search(self, field_name: str) -> bool:
        return False

    def can_sort(self, field_name: str) -> bool:
        return False
