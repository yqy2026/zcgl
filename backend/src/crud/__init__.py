"""
CRUD操作模块
"""

from ..models.asset import Asset
from ..models.ownership import Ownership
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

# TODO: Add registrations for other models as whitelists are created
# from .field_whitelist import ProjectWhitelist, UserWhitelist, RoleWhitelist
# from ..models.project import Project
# from ..models.user import User
# from ..models.role import Role
# register_whitelist(Project, ProjectWhitelist())
# register_whitelist(User, UserWhitelist())
# register_whitelist(Role, RoleWhitelist())

__all__ = ["asset_crud", "project_crud", "rent_contract", "rent_term", "rent_ledger"]
