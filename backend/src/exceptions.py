"""
自定义异常类
"""


class AssetNotFoundError(Exception):
    """资产未找到异常"""
    def __init__(self, asset_id: str):
        self.asset_id = asset_id
        super().__init__(f"Asset with id {asset_id} not found")


class DuplicateAssetError(Exception):
    """重复资产异常"""
    def __init__(self, property_name: str):
        self.property_name = property_name
        super().__init__(f"Asset with name {property_name} already exists")


class BusinessLogicError(Exception):
    """业务逻辑异常"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)
