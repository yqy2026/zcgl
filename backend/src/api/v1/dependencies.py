from typing import Protocol


class PDFProcessingServiceProtocol(Protocol):
    """Protocol for PDF processing service"""

    async def process(self, file_path: str) -> dict[str, object]: ...


class PDFSessionServiceProtocol(Protocol):
    """Protocol for PDF session service"""

    def get_session(self, session_id: str) -> object: ...


from ...core.performance import PerformanceMonitor
from ...services.document.pdf_import_service import PDFImportService

# ============================================================================
# 服务依赖工厂
# ============================================================================


def get_pdf_import_service() -> PDFImportService:
    """
    获取 PDF 导入服务实例

    这是全局单例，与原 pdf_import_unified.py 保持一致
    """
    return PDFImportService()


def get_performance_monitor() -> PerformanceMonitor:
    """
    获取性能监控器实例

    这是全局单例，从 core.performance 导入
    """
    from ...core.performance import performance_monitor

    return performance_monitor


# ============================================================================
# 可选服务依赖（支持优雅降级）
# ============================================================================


class OptionalServices:
    """
    可选服务容器

    某些 PDF 处理服务可能未安装（如 LLM Vision API），
    这些服务应标记为可选并提供降级方案
    """

    def __init__(self) -> None:
        self.pdf_processing_service: PDFProcessingServiceProtocol | None = None
        self.pdf_session_service: type[PDFSessionServiceProtocol] | None = None

        # 尝试导入可选服务
        try:
            from ...services.document.pdf_processing_service import (
                pdf_processing_service,
            )

            self.pdf_processing_service = pdf_processing_service
        except ImportError:
            pass

        try:
            from ...services.document.pdf_session_service import (
                PDFSessionService,
            )

            # PDFSessionService 需要 db 参数，不能直接实例化
            # 将在运行时按需创建
            self.pdf_session_service = PDFSessionService
        except ImportError:
            pass


# 创建可选服务容器
_optional_services = OptionalServices()


def get_optional_services() -> OptionalServices:
    """获取可选服务容器"""
    return _optional_services


# ============================================================================
# 数据库会话依赖
# ============================================================================

# Note: Use get_db from database.py directly for FastAPI dependency injection
# from ...database import get_db

# ============================================================================
# 类型别名（用于类型提示）
# ============================================================================

# 便捷类型别名
PDFServiceDep = PDFImportService
PerformanceMonitorDep = PerformanceMonitor
OptionalServicesDep = OptionalServices
