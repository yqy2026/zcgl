"""
合同Excel导入导出模块
"""

import logging
import os
import tempfile
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse

from ....constants.message_constants import ErrorIDs
from ....core.exception_handler import (
    BaseBusinessError,
    internal_error,
    service_unavailable,
)
from ....middleware.auth import get_current_active_user
from ....models.auth import User

logger = logging.getLogger(__name__)

router = APIRouter()

# 尝试导入Excel服务
try:
    from ....services.document.rent_contract_excel import rent_contract_excel_service

    EXCEL_SERVICE_AVAILABLE = True
except ImportError as e:
    logger.error(
        "无法导入rent_contract_excel_service，可能缺少依赖",
        extra={
            "error_id": ErrorIDs.System.RESOURCE_EXHAUSTED,
            "import_error": str(e),
        },
    )
    rent_contract_excel_service = None
    EXCEL_SERVICE_AVAILABLE = False
except SyntaxError as e:
    logger.critical(
        "rent_contract_excel_service存在语法错误",
        extra={
            "error_id": ErrorIDs.System.RESOURCE_EXHAUSTED,
            "syntax_error": str(e),
        },
    )
    rent_contract_excel_service = None
    EXCEL_SERVICE_AVAILABLE = False


@router.get("/excel/template", summary="下载Excel导入模板")
def download_excel_template(
    current_user: User = Depends(get_current_active_user),
) -> FileResponse:
    """
    下载租金合同Excel导入模板
    """
    if not EXCEL_SERVICE_AVAILABLE:
        raise service_unavailable("Excel服务不可用")

    try:
        result = rent_contract_excel_service.download_contract_template()
        if not result["success"]:
            raise internal_error(result["message"])

        return FileResponse(
            result["file_path"],
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=result["file_name"],
        )
    except BaseBusinessError:
        raise
    except Exception as e:
        logger.error(
            "下载模板时发生未预期错误",
            exc_info=True,
            extra={
                "error_id": ErrorIDs.Excel.TEMPLATE_DOWNLOAD_ERROR,
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
        )
        raise internal_error(f"下载模板失败: {str(e)}")


@router.post("/excel/import", summary="Excel导入合同数据")
def import_contracts_from_excel(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    import_terms: bool = Form(True, description="是否导入租金条款"),
    import_ledger: bool = Form(False, description="是否导入台账数据"),
    overwrite_existing: bool = Form(False, description="是否覆盖已存在的数据"),
) -> dict[str, Any]:
    """
    从Excel文件导入租金合同数据
    """
    if not EXCEL_SERVICE_AVAILABLE:
        raise service_unavailable("Excel服务不可用")

    from typing import cast

    try:
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, file.filename or "upload.xlsx")

        with open(file_path, "wb") as buffer:
            content = file.file.read()
            buffer.write(content)

        result = rent_contract_excel_service.import_contracts_from_excel(
            file_path=file_path,
            import_terms=import_terms,
            import_ledger=import_ledger,
            overwrite_existing=overwrite_existing,
        )

        rent_contract_excel_service.cleanup_file(file_path)

        return cast(dict[str, Any], result)

    except BaseBusinessError:
        raise
    except Exception as e:
        logger.error(
            "导入合同时发生未预期错误",
            exc_info=True,
            extra={
                "error_id": ErrorIDs.Excel.IMPORT_FAILED,
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
        )
        raise internal_error(f"导入失败: {str(e)}")


@router.get("/excel/export", summary="Excel导出合同数据")
def export_contracts_to_excel(
    contract_ids: list[str] | None = Query(None, description="要导出的合同ID列表"),
    current_user: User = Depends(get_current_active_user),
    include_terms: bool = Query(True, description="是否包含租金条款"),
    include_ledger: bool = Query(True, description="是否包含台账数据"),
    start_date: date | None = Query(None, description="开始日期"),
    end_date: date | None = Query(None, description="结束日期"),
) -> FileResponse:
    """
    导出租金合同数据到Excel文件
    """
    if not EXCEL_SERVICE_AVAILABLE:
        raise service_unavailable("Excel服务不可用")

    try:
        result = rent_contract_excel_service.export_contracts_to_excel(
            contract_ids=contract_ids,
            include_terms=include_terms,
            include_ledger=include_ledger,
            start_date=start_date,
            end_date=end_date,
        )

        if not result["success"]:
            raise internal_error(result["message"])

        return FileResponse(
            result["file_path"],
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=result["file_name"],
        )

    except BaseBusinessError:
        raise
    except Exception as e:
        logger.error(
            "导出合同时发生未预期错误",
            exc_info=True,
            extra={
                "error_id": ErrorIDs.Excel.EXPORT_FAILED,
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
        )
        raise internal_error(f"导出失败: {str(e)}")
