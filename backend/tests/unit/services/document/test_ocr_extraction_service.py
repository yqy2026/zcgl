from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from src.services.document.config import LLMProvider
from src.services.document.ocr_extraction_service import OCRExtractionService


@pytest.mark.asyncio
async def test_ocr_llm_uses_vision_model_provider(monkeypatch):
    """OCR text fallback must use the same VISION_MODEL provider SSOT as vision extraction."""
    monkeypatch.setenv("VISION_MODEL", "qwen")
    monkeypatch.setenv("LLM_PROVIDER", "glm")

    service = OCRExtractionService()
    llm_service = SimpleNamespace(
        chat_completion=AsyncMock(
            return_value=SimpleNamespace(content='{"contract_number": "C-001"}')
        )
    )

    with patch(
        "src.services.document.ocr_extraction_service.create_llm_service",
        return_value=llm_service,
    ) as create_service:
        result = await service._extract_with_llm("prompt", "ocr text")

    create_service.assert_called_once_with(LLMProvider.QWEN)
    assert result == {"contract_number": "C-001"}
