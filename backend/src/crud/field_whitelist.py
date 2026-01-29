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
    - BLOCKED: All PII fields (manager_name, tenant_name), contact info
    - BLOCKED: Financial data (monthly_rent, deposit) for filtering
    - BLOCKED: Operational intelligence (operation_status)
    - ALLOWED: Basic classification and status fields
    - SPECIAL: monthly_rent, deposit allowed for SORTING only (display)
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
        "ownership_entity",  # Organization name (public info)
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
        "contract_start_date",
        "contract_end_date",
        # Numeric sorting
        "land_area",
        "actual_property_area",
        "rentable_area",
        "rented_area",
        # Financial: allowed for SORTING (display) but not FILTERING (discovery)
        "monthly_rent",
        "deposit",
        # Alphabetic sorting
        "property_name",
        "ownership_entity",
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
        # Financial - Business sensitive (BLOCKED for filtering, allowed for sorting)
        # Note: monthly_rent and deposit are in sort_fields but NOT in filter_fields
        # This allows sorting for display but prevents filtering for discovery
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
        "monthly_rent",
        "deposit",
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
        from ..models.asset import Asset, Ownership
        from ..models.rbac import Role
        from ..models.rent_contract import RentContract

        register_whitelist(Asset, AssetWhitelist())
        register_whitelist(Ownership, OwnershipWhitelist())
        register_whitelist(RentContract, RentContractWhitelist())
        register_whitelist(Role, RoleWhitelist())
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
