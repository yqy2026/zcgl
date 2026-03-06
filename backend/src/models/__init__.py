"""
数据库模型模块
"""

from .abac import (  # noqa: F401
    ABACAction,
    ABACEffect,
    ABACPolicy,
    ABACPolicyRule,
    ABACRolePolicy,
)
from .asset import Asset  # noqa: F401
from .asset_history import AssetDocument, AssetHistory  # noqa: F401
from .asset_management_history import AssetManagementHistory  # noqa: F401
from .asset_search_index import AssetSearchIndex  # noqa: F401
from .associations import (  # noqa: F401  # noqa: F401
    contract_assets,
    contract_group_assets,
    property_cert_assets,
    rent_contract_assets,
)
from .auth import AuditLog, User, UserSession  # noqa: F401
from .certificate_party_relation import (  # noqa: F401
    CertificatePartyRelation,
    CertificateRelationRole,
)
from .collection import (  # noqa: F401
    CollectionMethod,
    CollectionRecord,
    CollectionStatus,
)
from .contact import Contact, ContactType  # noqa: F401
from .contract_group import (  # noqa: F401
    AgencyAgreementDetail,
    Contract,
    ContractDirection,
    ContractGroup,
    ContractLifecycleStatus,
    ContractRelation,
    ContractRelationType,
    ContractReviewStatus,
    GroupRelationType,
    LeaseContractDetail,
    RevenueMode,
)
from .enum_field import (  # noqa: F401
    EnumFieldHistory,
    EnumFieldType,
    EnumFieldUsage,
    EnumFieldValue,
)
from .llm_prompt import (  # noqa: F401
    ExtractionFeedback,
    PromptMetrics,
    PromptStatus,
    PromptTemplate,
    PromptVersion,
)
from .notification import (  # noqa: F401
    Notification,
    NotificationPriority,
    NotificationType,
)
from .organization import (  # noqa: F401
    Organization,
    OrganizationHistory,
)
from .ownership import Ownership  # noqa: F401
from .party import Party, PartyContact, PartyHierarchy, PartyType  # noqa: F401
from .party_role import PartyRoleBinding, PartyRoleDef  # noqa: F401
from .project import Project  # noqa: F401
from .project_asset import ProjectAsset  # noqa: F401
from .project_relations import ProjectOwnershipRelation  # noqa: F401
from .property_certificate import (  # noqa: F401
    CertificateType,
    OwnerType,
    PropertyCertificate,
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
from .user_party_binding import RelationType, UserPartyBinding  # noqa: F401

__all__ = [
    "Asset",
    "AssetManagementHistory",
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
    # 合同组体系（REQ-RNT-001）
    "ContractGroup",
    "Contract",
    "LeaseContractDetail",
    "AgencyAgreementDetail",
    "ContractRelation",
    "RevenueMode",
    "ContractDirection",
    "GroupRelationType",
    "ContractLifecycleStatus",
    "ContractReviewStatus",
    "ContractRelationType",
    "contract_group_assets",
    "contract_assets",
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
    # LLM Prompt models
    "PromptTemplate",
    "PromptVersion",
    "ExtractionFeedback",
    "PromptMetrics",
    "PromptStatus",
    "PartyType",
    "Party",
    "PartyHierarchy",
    "PartyContact",
    "PartyRoleDef",
    "PartyRoleBinding",
    "RelationType",
    "UserPartyBinding",
    "ProjectAsset",
    "CertificateRelationRole",
    "CertificatePartyRelation",
    "ABACEffect",
    "ABACAction",
    "ABACPolicy",
    "ABACPolicyRule",
    "ABACRolePolicy",
    # Property Certificate models
    "CertificateType",
    "OwnerType",
    "PropertyCertificate",
    # Task models
    "AsyncTask",
    "ExcelTaskConfig",
    "TaskHistory",
    # Security Event models
    "SecurityEvent",
    "SecurityEventType",
    "SecuritySeverity",
]
