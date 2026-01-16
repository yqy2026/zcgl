"""
Data lifecycle status constants.

Provides status constants for data entities and their lifecycle states.
"""

from typing import Final


class DataStatusValues:
    """
    Data lifecycle status values.

    These constants define the status values for data entities throughout
    their lifecycle (normal, abnormal, deleted, etc.).
    """

    # Asset data statuses (Chinese values)
    ASSET_NORMAL: Final[str] = "正常"
    ASSET_ABNORMAL: Final[str] = "异常"
    ASSET_DELETED: Final[str] = "已删除"
    ASSET_ARCHIVED: Final[str] = "已归档"

    # Ownership statuses
    OWNERSHIP_CONFIRMED: Final[str] = "已确权"
    OWNERSHIP_UNCONFIRMED: Final[str] = "未确权"
    OWNERSHIP_PARTIAL: Final[str] = "部分确权"

    # Property nature
    PROPERTY_OPERATIONAL: Final[str] = "经营性"
    PROPERTY_NON_OPERATIONAL: Final[str] = "非经营性"

    # Usage status
    USAGE_RENTED: Final[str] = "出租"
    USAGE_SELF_USE: Final[str] = "自用"
    USAGE_VACANT: Final[str] = "空置"
    USAGE_OTHER: Final[str] = "其他"

    # Contract statuses
    CONTRACT_ACTIVE: Final[str] = "生效"
    CONTRACT_EXPIRED: Final[str] = "过期"
    CONTRACT_TERMINATED: Final[str] = "终止"
    CONTRACT_PENDING: Final[str] = "待生效"

    @classmethod
    def get_active_asset_statuses(cls) -> list[str]:
        """Get list of active asset statuses (not deleted or archived)."""
        return [cls.ASSET_NORMAL, cls.ASSET_ABNORMAL]

    @classmethod
    def is_asset_active(cls, status: str) -> bool:
        """Check if an asset status is active."""
        return status in cls.get_active_asset_statuses()

    @classmethod
    def get_ownership_statuses(cls) -> list[str]:
        """Get all ownership status values."""
        return [cls.OWNERSHIP_CONFIRMED, cls.OWNERSHIP_UNCONFIRMED, cls.OWNERSHIP_PARTIAL]


# Legacy compatibility aliases (deprecated, will be removed in v2.0)
ASSET_STATUS_NORMAL = DataStatusValues.ASSET_NORMAL
ASSET_STATUS_ABNORMAL = DataStatusValues.ASSET_ABNORMAL
OWNERSHIP_STATUS_CONFIRMED = DataStatusValues.OWNERSHIP_CONFIRMED
