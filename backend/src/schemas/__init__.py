"""
Pydantic数据验证模型模块
"""

from .asset import (
    AssetBase,
    AssetCreate,
    AssetUpdate,
    AssetResponse,
    AssetHistoryResponse,
    AssetDocumentResponse,
    OwnershipStatus,
    UsageStatus,
    PropertyNature,
)

__all__ = [
    "AssetBase",
    "AssetCreate", 
    "AssetUpdate",
    "AssetResponse",
    "AssetHistoryResponse",
    "AssetDocumentResponse",
    "OwnershipStatus",
    "UsageStatus", 
    "PropertyNature",
]