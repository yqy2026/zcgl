from typing import Any, Protocol


class IOCRService(Protocol):
    async def process_pdf_document(
        self,
        pdf_path: str,
        max_pages: int = 10,
        max_concurrency: int | None = None,
        use_preprocessing: bool = True,
    ) -> dict[str, Any]:
        ...

    async def process_pdf_page(
        self, page: Any, page_num: int, use_preprocessing: bool = True
    ) -> Any:
        ...

    def get_performance_report(self) -> dict[str, Any]:
        ...