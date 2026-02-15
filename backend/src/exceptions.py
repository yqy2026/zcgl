"""
自定义异常类
"""

from .core.exception_handler import (
    BaseBusinessError,
    DuplicateResourceError,
    ResourceNotFoundError,
)


class AssetNotFoundError(ResourceNotFoundError):
    """资产未找到异常（兼容包装）"""

    def __init__(self, asset_id: str):
        super().__init__("Asset", asset_id)


class DuplicateAssetError(DuplicateResourceError):
    """重复资产异常（兼容包装）"""

    def __init__(self, property_name: str):
        super().__init__("Asset", "property_name", property_name)


class BusinessLogicError(BaseBusinessError):
    """业务逻辑异常"""

    def __init__(self, message: str):
        super().__init__(
            message=message,
            code="BUSINESS_LOGIC_ERROR",
            status_code=400,
        )
