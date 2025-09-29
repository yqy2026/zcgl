"""
CRUD操作模块
"""

from .asset import asset_crud
from .project import project
from .rent_contract import rent_contract, rent_term, rent_ledger

__all__ = ["asset_crud", "project", "rent_contract", "rent_term", "rent_ledger"]
