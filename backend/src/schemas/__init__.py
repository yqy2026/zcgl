"""
Pydantic数据验证模型模块
"""

from .asset import (  # noqa: F401
    AssetBase,
    AssetCreate,
    AssetDocumentResponse,
    AssetHistoryResponse,
    AssetListItemResponse,
    AssetResponse,
    AssetUpdate,
)
from .asset_management_history import (  # noqa: F401
    AssetManagementHistoryBase,
    AssetManagementHistoryCreate,
    AssetManagementHistoryResponse,
    AssetManagementHistoryUpdate,
)
from .project import (  # noqa: F401
    ProjectBase,
    ProjectCreate,
    ProjectDeleteResponse,
    ProjectListResponse,
    ProjectResponse,
    ProjectSearchRequest,
    ProjectStatisticsResponse,
    ProjectUpdate,
)
from .project_asset import (  # noqa: F401
    ProjectAssetBindRequest,
    ProjectAssetResponse,
    ProjectAssetUnbindRequest,
)

__all__ = [
    "AssetBase",
    "AssetCreate",
    "AssetUpdate",
    "AssetResponse",
    "AssetListItemResponse",
    "AssetHistoryResponse",
    "AssetDocumentResponse",
    "AssetManagementHistoryBase",
    "AssetManagementHistoryCreate",
    "AssetManagementHistoryUpdate",
    "AssetManagementHistoryResponse",
    "ProjectBase",
    "ProjectCreate",
    "ProjectUpdate",
    "ProjectResponse",
    "ProjectListResponse",
    "ProjectDeleteResponse",
    "ProjectSearchRequest",
    "ProjectStatisticsResponse",
    "ProjectAssetBindRequest",
    "ProjectAssetUnbindRequest",
    "ProjectAssetResponse",
]
