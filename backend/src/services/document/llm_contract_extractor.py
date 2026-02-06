import logging
from typing import Any

from ...core.config import settings
from .extractors.factory import get_llm_extractor
from .ocr_extraction_service import OCRExtractionService
from .pdf_analyzer import get_extraction_recommendation_async

logger = logging.getLogger(__name__)


class LLMContractExtractor:
    """
    Facade for LLM Contract Extraction using the configured provider (Adapter Pattern).
    Delegates actual work to GLMAdapter, QwenAdapter etc. based on config.
    """

    def __init__(self) -> None:
        self.adapter = get_llm_extractor()
        self.ocr_extractor = OCRExtractionService()

    async def extract(self, markdown_content: str) -> dict[str, Any]:
        """
        Legacy text-only extraction (keeps backward compatibility).
        Ideally, adapters should handle both text and vision, but for now
        we primarily route 'vision' calls to the new adapters.

        Note: This method is deprecated. Use extract_smart() instead.
        """
        # For pure text/markdown extraction, we might still want to use
        # the original prompt logic or delegate if the adapter supports text-only.
        # Here we assume the adapter *can* handle text if we implement it,
        # but for safety let's keep the original logic OR just warn.

        # ACTUALLY: The best way is to make the adapter handle it.
        # But Qwen-VL is vision-first.
        # Let's keep the legacy LLMService logic here strictly for "text mode"
        # OR better: Assume 'extract' in this class is for the "Text Mode" path
        # and 'extract_from_pdf_vision' is for "Vision Mode".

        # For this refactor, I will DELEGATE vision calls to the adapter,
        # but keep the original text-based extract() here if needed,
        # or (better) move it to a specific TextAdapter.
        # To avoid breaking too much, I'll allow this class to hold the legacy text logic
        # but usage of 'extract_from_pdf_vision' will go to the adapter.

        # Note: Text-only extraction is intentionally unimplemented.
        # The system uses Vision-based extraction via extract_smart() which provides
        # better accuracy for contract documents. This method exists only for
        # backward compatibility with the legacy API interface.
        raise NotImplementedError(
            "Text-only extraction not implemented. Use extract_smart() instead."
        )

    async def extract_smart(
        self, pdf_path: str, force_method: str | None = None
    ) -> dict[str, Any]:
        """
        Smart extraction routing.
        """
        force_method_normalized = force_method.lower() if force_method else None

        if force_method_normalized == "ocr":
            return await self._extract_with_ocr(pdf_path)

        if (
            settings.GLM_OCR_ENABLE
            and settings.GLM_OCR_AUTO
            and force_method_normalized in (None, "smart")
        ):
            recommendation = await get_extraction_recommendation_async(pdf_path)
            if recommendation == "vision":
                ocr_result = await self._extract_with_ocr(pdf_path)
                if ocr_result.get("success"):
                    return ocr_result

        try:
            return await self.adapter.extract(pdf_path, force_method=force_method)
        except Exception as e:
            logger.error(f"Smart extraction failed via adapter: {e}")
            return {"success": False, "error": str(e)}

    async def _extract_with_ocr(self, pdf_path: str) -> dict[str, Any]:
        ocr_result = await self.ocr_extractor.extract_contract(pdf_path)
        if not ocr_result.get("success"):
            logger.warning("OCR extraction failed, fallback to vision")
        return ocr_result


# Singleton getter (keeps existing API compatible)
_llm_extractor = None


def get_llm_contract_extractor() -> LLMContractExtractor:
    global _llm_extractor
    if _llm_extractor is None:
        _llm_extractor = LLMContractExtractor()
    return _llm_extractor
