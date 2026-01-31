"""
Excel Services

Excel导入导出服务层
"""

import logging

__all__: list[str] = []
logger = logging.getLogger(__name__)


def _log_import_error(service_name: str) -> None:
    logger.warning(f"Service import failed: {service_name}", exc_info=True)


# 使用安全导入模式
try:
    from .excel_import_service import ExcelImportService as ExcelImportService

    __all__.append("ExcelImportService")
except Exception:  # nosec - B110: Intentional graceful degradation
    _log_import_error("excel.excel_import_service.ExcelImportService")

try:
    from .excel_export_service import ExcelExportService as ExcelExportService

    __all__.append("ExcelExportService")
except Exception:  # nosec - B110: Intentional graceful degradation
    _log_import_error("excel.excel_export_service.ExcelExportService")

try:
    from .excel_template_service import ExcelTemplateService as ExcelTemplateService

    __all__.append("ExcelTemplateService")
except Exception:  # nosec - B110: Intentional graceful degradation
    _log_import_error("excel.excel_template_service.ExcelTemplateService")
