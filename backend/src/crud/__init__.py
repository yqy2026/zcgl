"""
CRUD操作模块
"""

from ..models.asset import Asset, Ownership
from ..models.rent_contract import RentContract
from .asset import asset_crud

# Security: Register field whitelists for models
from .field_whitelist import (
    AssetWhitelist,
    OwnershipWhitelist,
    RentContractWhitelist,
    register_whitelist,
)
from .project import project_crud
from .rent_contract import rent_contract, rent_ledger, rent_term

# Register whitelists for each model to prevent unauthorized field access
register_whitelist(Asset, AssetWhitelist())
register_whitelist(RentContract, RentContractWhitelist())
register_whitelist(Ownership, OwnershipWhitelist())

# Additional models can be registered as needed with explicit whitelists
# Security: Models without whitelists will use EmptyWhitelist (deny all fields)
# To enable field access for a model, create a whitelist class and register it:
# from .field_whitelist import ModelNameWhitelist
# from ..models.model_name import ModelName
# register_whitelist(ModelName, ModelNameWhitelist())

__all__ = ["asset_crud", "project_crud", "rent_contract", "rent_term", "rent_ledger"]
