"""
数据库模型模块
"""

from .asset import Asset  # noqa: F401
from .asset_history import AssetDocument, AssetHistory  # noqa: F401
from .asset_search_index import AssetSearchIndex  # noqa: F401
from .associations import property_cert_assets, rent_contract_assets  # noqa: F401
from .auth import AuditLog, User, UserSession  # noqa: F401
from .collection import (  # noqa: F401
    CollectionMethod,
    CollectionRecord,
    CollectionStatus,
)
from .contact import Contact, ContactType  # noqa: F401
from .enum_field import (  # noqa: F401
    EnumFieldHistory,
    EnumFieldType,
    EnumFieldUsage,
    EnumFieldValue,
)
from .notification import (  # noqa: F401
    Notification,
    NotificationPriority,
    NotificationType,
)
from .organization import (  # noqa: F401
    Employee,
    Organization,
    OrganizationHistory,
    Position,
)
from .ownership import Ownership  # noqa: F401
from .project import Project  # noqa: F401
from .project_relations import ProjectOwnershipRelation  # noqa: F401
from .property_certificate import (  # noqa: F401
    CertificateType,
    OwnerType,
    PropertyCertificate,
    PropertyOwner,
)
from .rbac import (  # noqa: F401
    Permission,
    PermissionAuditLog,
    PermissionGrant,
    ResourcePermission,
    Role,
    UserRoleAssignment,
)
from .rent_contract import (  # noqa: F401
    ContractType,
    DepositTransactionType,
    PaymentCycle,
    RentContract,
    RentContractAttachment,
    RentContractHistory,
    RentDepositLedger,
    RentLedger,
    RentTerm,
    ServiceFeeLedger,
)
from .security_event import (  # noqa: F401
    SecurityEvent,
    SecurityEventType,
    SecuritySeverity,
)
from .system_dictionary import AssetCustomField, SystemDictionary  # noqa: F401
from .task import AsyncTask, ExcelTaskConfig, TaskHistory  # noqa: F401

__all__ = [
    "Asset",
    "AssetHistory",
    "AssetDocument",
    "Ownership",
    "Project",
    "ProjectOwnershipRelation",
    "SystemDictionary",
    "AssetCustomField",
    "AssetSearchIndex",
    "Organization",
    "OrganizationHistory",
    "Position",
    "Employee",
    "User",
    "UserSession",
    "AuditLog",
    "Role",
    "Permission",
    "UserRoleAssignment",
    "ResourcePermission",
    "PermissionGrant",
    "PermissionAuditLog",
    "EnumFieldType",
    "EnumFieldValue",
    "EnumFieldUsage",
    "EnumFieldHistory",
    "RentContract",
    "RentTerm",
    "RentLedger",
    "RentContractHistory",
    "RentContractAttachment",
    "RentDepositLedger",
    "ServiceFeeLedger",
    "ContractType",
    "DepositTransactionType",
    "PaymentCycle",
    "rent_contract_assets",
    "property_cert_assets",
    # Contact models
    "Contact",
    "ContactType",
    # Collection models
    "CollectionRecord",
    "CollectionMethod",
    "CollectionStatus",
    # Notification models
    "Notification",
    "NotificationType",
    "NotificationPriority",
    # Property Certificate models
    "CertificateType",
    "OwnerType",
    "PropertyCertificate",
    "PropertyOwner",
    # Task models
    "AsyncTask",
    "ExcelTaskConfig",
    "TaskHistory",
    # Security Event models
    "SecurityEvent",
    "SecurityEventType",
    "SecuritySeverity",
]
