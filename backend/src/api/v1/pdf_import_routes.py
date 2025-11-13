"""
PDF导入专用路由模块
包含PDF智能导入相关的所有端点
"""

from fastapi import APIRouter
from ...core.response_handler import success_response

router = APIRouter(tags=["PDF智能导入"])


@router.get("/pdf-import/info")
async def get_pdf_import_info():
    """
    获取PDF导入系统信息
    迁移自 main.py 的PDF导入信息功能
    """
    return success_response(
        data={
            "supported_formats": [".pdf"],
            "max_file_size": 50 * 1024 * 1024,  # 50MB
            "ocr_engines": ["paddle", "tesseract"],
            "processing_status": "available"
        },
        message="PDF导入系统信息获取成功"
    )


@router.get("/pdf-import/sessions")
async def get_pdf_import_sessions():
    """
    获取PDF导入会话列表
    迁移自 main.py 的PDF导入会话功能
    """
    return success_response(data=[], message="PDF导入会话列表获取成功")


@router.post("/pdf-import/upload")
async def upload_pdf_for_import():
    """
    上传PDF进行智能导入
    迁移自 main.py 的PDF上传功能
    """
    return success_response(
        data={"task_id": "demo_task_id"},
        message="PDF上传成功"
    )