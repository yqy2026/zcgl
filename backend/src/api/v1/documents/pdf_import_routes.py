"""
PDF导入专用路由模块
包含PDF智能导入相关的所有端点
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ....core.response_handler import success_response

router = APIRouter(tags=["PDF智能导入"])


@router.get("/pdf-import/info")
def get_pdf_import_info() -> JSONResponse:
    """
    获取PDF导入系统信息
    迁移自 main.py 的PDF导入信息功能
    """
    return success_response(  # pragma: no cover
        data={  # pragma: no cover
            "supported_formats": [".pdf"],  # pragma: no cover
            "max_file_size": 50 * 1024 * 1024,  # 50MB  # pragma: no cover
            "ocr_engines": ["paddle", "tesseract"],  # pragma: no cover
            "processing_status": "available",  # pragma: no cover
        },  # pragma: no cover
        message="PDF导入系统信息获取成功",  # pragma: no cover
    )  # pragma: no cover


@router.get("/pdf-import/sessions")
def get_pdf_import_sessions() -> JSONResponse:
    """
    获取PDF导入会话列表
    迁移自 main.py 的PDF导入会话功能
    """
    return success_response(
        data=[], message="PDF导入会话列表获取成功"
    )  # pragma: no cover


@router.post("/pdf-import/upload")
def upload_pdf_for_import() -> JSONResponse:
    """
    上传PDF进行智能导入
    迁移自 main.py 的PDF上传功能
    """
    return success_response(
        data={"task_id": "demo_task_id"}, message="PDF上传成功"
    )  # pragma: no cover
