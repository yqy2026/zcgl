from types import SimpleNamespace
from unittest.mock import patch

import pytest

from src.core.exception_handler import ConfigurationError
from src.services.core.vision_provider import (
    get_vision_provider,
    resolve_vision_provider,
)
from src.services.document.config import LLMProvider


def test_resolve_vision_provider_prefers_vision_model_env(monkeypatch):
    """VISION_MODEL is the document vision provider SSOT."""
    monkeypatch.setenv("VISION_MODEL", "qwen")

    with patch("src.services.core.vision_provider.settings") as mock_settings:
        mock_settings.VISION_MODEL = None
        mock_settings.EXTRACTION_LLM_PROVIDER = "glm"
        mock_settings.LLM_PROVIDER = "hunyuan"

        assert resolve_vision_provider() == LLMProvider.QWEN


def test_resolve_vision_provider_uses_explicit_provider():
    assert resolve_vision_provider("deepseek-vl") == LLMProvider.DEEPSEEK


def test_get_vision_provider_returns_configured_service(monkeypatch):
    monkeypatch.delenv("VISION_MODEL", raising=False)
    service = SimpleNamespace(is_available=True)

    with patch("src.services.core.vision_provider.settings") as mock_settings:
        mock_settings.VISION_MODEL = "hunyuan"
        mock_settings.EXTRACTION_LLM_PROVIDER = None
        mock_settings.LLM_PROVIDER = "glm"
        with patch.dict(
            "src.services.core.vision_provider.VISION_PROVIDER_GETTERS",
            {LLMProvider.HUNYUAN: lambda: service},
        ):
            assert get_vision_provider() is service


def test_get_vision_provider_fails_loud_when_api_key_missing(monkeypatch):
    monkeypatch.setenv("VISION_MODEL", "qwen")
    service = SimpleNamespace(is_available=False)

    with patch.dict(
        "src.services.core.vision_provider.VISION_PROVIDER_GETTERS",
        {LLMProvider.QWEN: lambda: service},
    ):
        with pytest.raises(ConfigurationError, match="DASHSCOPE_API_KEY"):
            get_vision_provider()
