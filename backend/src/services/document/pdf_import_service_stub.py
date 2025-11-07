from typing import Any


class PDFImportService:
    """Minimal stub for PDF import service.

    Provides a safe placeholder to satisfy imports while the full
    implementation is unavailable or fails to load due to environment
    constraints.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.initialized = True

    async def import_pdf(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return {
            "status": "stub",
            "message": "PDFImportService stub executed",
        }


__all__ = ["PDFImportService"]