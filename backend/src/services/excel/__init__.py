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

try:
    from .excel_preview_service import ExcelPreviewService as ExcelPreviewService

    __all__.append("ExcelPreviewService")
except Exception:  # nosec - B110: Intentional graceful degradation
    _log_import_error("excel.excel_preview_service.ExcelPreviewService")

try:
    from .excel_config_service import ExcelConfigService as ExcelConfigService

    __all__.append("ExcelConfigService")
except Exception:  # nosec - B110: Intentional graceful degradation
    _log_import_error("excel.excel_config_service.ExcelConfigService")

try:
    from .excel_status_service import ExcelStatusService as ExcelStatusService

    __all__.append("ExcelStatusService")
except Exception:  # nosec - B110: Intentional graceful degradation
    _log_import_error("excel.excel_status_service.ExcelStatusService")

try:
    from .excel_task_service import ExcelTaskService as ExcelTaskService

    __all__.append("ExcelTaskService")
except Exception:  # nosec - B110: Intentional graceful degradation
    _log_import_error("excel.excel_task_service.ExcelTaskService")
