"""合同组/合同路由导出。"""

from . import contract_groups

contract_groups_router = contract_groups.router

__all__ = ["contract_groups_router"]
