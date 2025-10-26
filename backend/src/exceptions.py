"""
自定义异常类
"""

from fastapi import status
from .core.exception_handler import BaseBusinessException


class AssetNotFoundError(BaseBusinessException):
    """资产未找到异常"""
    def __init__(self, asset_id: str):
        self.asset_id = asset_id
        super().__init__(
            message=f"Asset with id {asset_id} not found",
            code="ASSET_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND
        )


class DuplicateAssetError(BaseBusinessException):
    """重复资产异常"""
    def __init__(self, property_name: str):
        self.property_name = property_name
        super().__init__(
            message=f"Asset with name {property_name} already exists",
            code="DUPLICATE_ASSET",
            status_code=status.HTTP_409_CONFLICT
        )


class BusinessLogicError(BaseBusinessException):
    """业务逻辑异常"""
    def __init__(self, message: str):
        super().__init__(
            message=message,
            code="BUSINESS_LOGIC_ERROR",
            status_code=status.HTTP_400_BAD_REQUEST
        )
