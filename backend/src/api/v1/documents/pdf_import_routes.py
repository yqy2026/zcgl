"""
PDF导入专用路由模块
包含PDF智能导入相关的所有端点
"""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from ....constants.file_size_constants import DEFAULT_MAX_FILE_SIZE
from ....core.response_handler import success_response
from ....middleware.auth import AuthzContext, get_current_active_user, require_authz
from ....models.auth import User

router = APIRouter(tags=["PDF智能导入"])
_CONTRACT_CREATE_UNSCOPED_PARTY_ID = "__unscoped__:contract:create"
_CONTRACT_CREATE_RESOURCE_CONTEXT: dict[str, str] = {
    "party_id": _CONTRACT_CREATE_UNSCOPED_PARTY_ID,
    "owner_party_id": _CONTRACT_CREATE_UNSCOPED_PARTY_ID,
    "manager_party_id": _CONTRACT_CREATE_UNSCOPED_PARTY_ID,
}


@router.get("/info")
def get_pdf_import_info(
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="contract",
        )
    ),
) -> JSONResponse:
    """
    获取PDF导入系统信息
    迁移自 main.py 的PDF导入信息功能
    """
    _ = current_user, _authz_ctx
    return success_response(  # pragma: no cover
        data={  # pragma: no cover
            "supported_formats": [".pdf"],  # pragma: no cover
            "max_file_size": DEFAULT_MAX_FILE_SIZE,  # pragma: no cover
            "vision_providers": [
                "glm",
                "qwen",
                "deepseek",
                "hunyuan",
            ],  # pragma: no cover
            "processing_status": "available",  # pragma: no cover
        },  # pragma: no cover
        message="PDF导入系统信息获取成功",  # pragma: no cover
    )  # pragma: no cover


@router.get("/sessions")
def get_pdf_import_sessions(
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="contract",
        )
    ),
) -> JSONResponse:
    """
    获取PDF导入会话列表
    迁移自 main.py 的PDF导入会话功能
    """
    _ = current_user, _authz_ctx
    return success_response(
        data=[], message="PDF导入会话列表获取成功"
    )  # pragma: no cover


@router.post("/upload")
def upload_pdf_for_import(
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="create",
            resource_type="contract",
            resource_context=_CONTRACT_CREATE_RESOURCE_CONTEXT,
        )
    ),
) -> JSONResponse:
    """
    上传PDF进行智能导入
    迁移自 main.py 的PDF上传功能
    """
    _ = current_user, _authz_ctx
    return success_response(
        data={"task_id": "demo_task_id"}, message="PDF上传成功"
    )  # pragma: no cover
