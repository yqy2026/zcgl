"""
PDF导入API - 主路由

统一入口，包含以下子模块:
- pdf_upload: 文件上传和处理
- pdf_sessions: 会话管理
- pdf_system: 系统信息

从原 pdf_import_unified.py (1,128 lines) 拆分而成，遵循单一职责原则。
"""

import importlib
import logging
from importlib.util import find_spec
from types import ModuleType

from fastapi import APIRouter, Depends

from ....middleware.auth import AuthzContext, require_authz
from . import pdf_system, pdf_upload

logger = logging.getLogger(__name__)

try:
    pdf_sessions_module: ModuleType | None
    pdf_sessions_spec = (
        find_spec(f"{__package__}.pdf_sessions") if __package__ is not None else None
    )
    if pdf_sessions_spec is not None:
        pdf_sessions_module = importlib.import_module(
            ".pdf_sessions", package=__package__
        )
    else:
        logger.debug("PDF会话模块未启用: %s.pdf_sessions", __package__)
        pdf_sessions_module = None
except Exception as exc:
    logger.warning("PDF会话模块加载失败: %s", exc)
    pdf_sessions_module = None

# 创建主路由器
router = APIRouter()
_AUTHZ_CONTEXT_CLS = AuthzContext
_RENT_CONTRACT_CREATE_UNSCOPED_PARTY_ID = "__unscoped__:rent_contract:create"
_RENT_CONTRACT_CREATE_RESOURCE_CONTEXT: dict[str, str] = {
    "party_id": _RENT_CONTRACT_CREATE_UNSCOPED_PARTY_ID,
    "owner_party_id": _RENT_CONTRACT_CREATE_UNSCOPED_PARTY_ID,
    "manager_party_id": _RENT_CONTRACT_CREATE_UNSCOPED_PARTY_ID,
}

# 包含子路由器
router.include_router(
    pdf_upload.router,
    tags=["PDF上传"],
    dependencies=[
        Depends(
            require_authz(
                action="create",
                resource_type="rent_contract",
                resource_context=_RENT_CONTRACT_CREATE_RESOURCE_CONTEXT,
            )
        )
    ],
)
if pdf_sessions_module is not None:
    router.include_router(
        pdf_sessions_module.router,
        tags=["PDF会话管理"],
        dependencies=[
            Depends(
                require_authz(
                    action="read",
                    resource_type="rent_contract",
                )
            )
        ],
    )
router.include_router(
    pdf_system.router,
    tags=["PDF系统信息"],
    dependencies=[
        Depends(
            require_authz(
                action="read",
                resource_type="rent_contract",
            )
        )
    ],
)

module_count = 2 + (1 if pdf_sessions_module is not None else 0)
logger.info("PDF导入API主路由初始化完成，包含%s个子模块", module_count)
