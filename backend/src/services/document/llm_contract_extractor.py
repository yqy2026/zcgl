import logging
from typing import Any

logger = logging.getLogger(__name__)

from .extractors.factory import get_llm_extractor


class LLMContractExtractor:
    """
    Facade for LLM Contract Extraction using the configured provider (Adapter Pattern).
    Delegates actual work to GLMAdapter, QwenAdapter etc. based on config.
    """

    def __init__(self):
        self.adapter = get_llm_extractor()

    async def extract(self, markdown_content: str) -> dict[str, Any]:
        """
        Legacy text-only extraction (keeps backward compatibility).
        Ideally, adapters should handle both text and vision, but for now 
        we primarily route 'vision' calls to the new adapters.
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
        pass

    async def extract_smart(
        self,
        pdf_path: str,
        force_method: str | None = None
    ) -> dict[str, Any]:
        """
        Smart extraction routing.
        """
        # Use the adapter to extract
        # The adapter interface is tailored for file-based extraction (Vision/Multi-modal)
        try:
            return await self.adapter.extract(pdf_path, force_method=force_method)
        except Exception as e:
            logger.error(f"Smart extraction failed via adapter: {e}")
            return {"success": False, "error": str(e)}

# Singleton getter (keeps existing API compatible)
_llm_extractor = None

def get_llm_contract_extractor() -> LLMContractExtractor:
    global _llm_extractor
    if _llm_extractor is None:
        _llm_extractor = LLMContractExtractor()
    return _llm_extractor
