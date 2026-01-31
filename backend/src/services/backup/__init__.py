"""
Backup Services

数据备份和恢复服务层
"""

import logging

__all__: list[str] = []
logger = logging.getLogger(__name__)


def _log_import_error(service_name: str) -> None:
    logger.warning(f"Service import failed: {service_name}", exc_info=True)


# 使用安全导入模式
try:
    from .backup_service import BackupService as BackupService

    __all__.append("BackupService")
except Exception:  # nosec - B110: Intentional graceful degradation
    _log_import_error("backup.backup_service.BackupService")
