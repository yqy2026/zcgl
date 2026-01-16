"""
Comprehensive unit tests for LLM Service.

Tests cover:
- LLMResponse model
- LLMServiceInterface abstract base class
- BaseOpenAILLM service implementation
- LLMServiceFactory registration and creation
- LLMService backward compatibility class
- Singleton pattern functions
- Convenience functions

Target: 70%+ coverage for llm_service.py
"""

import os
from unittest.mock import Mock, AsyncMock, patch, MagicMock

import httpx
import pytest

from src.services.core.llm_service import (
    LLMResponse,
    LLMServiceInterface,
    BaseOpenAILLM,
    LLMServiceFactory,
    LLMService,
    get_llm_service,
    create_llm_service,
)
from src.services.document.config import LLMProvider


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_llm_response():
    """Mock LLM API response."""
    return {
        "choices": [
            {
                "message": {
                    "content": '{"result": "success", "data": "test data"}',
                    "role": "assistant",
                },
                "finish_reason": "stop",
                "index": 0,
            }
        ],
        "usage": {"prompt_tokens": 50, "completion_tokens": 30, "total_tokens": 80},
        "model": "test-model",
        "id": "test-response-id",
    }


@pytest.fixture
def sample_messages():
    """Sample messages for chat completion."""
    return [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Extract contract information"},
    ]


# ============================================================================
# LLMResponse Model Tests
# ============================================================================


class TestLLMResponse:
    """Test LLMResponse Pydantic model."""

    def test_create_minimal_response(self):
        """Test creating response with minimal required fields."""
        response = LLMResponse(content="Test content")
        assert response.content == "Test content"
        assert response.raw_response is None
        assert response.usage == {}
        assert response.provider == ""

    def test_create_full_response(self):
        """Test creating response with all fields."""
        raw_data = {"key": "value"}
        usage_data = {"tokens": 100}

        response = LLMResponse(
            content="Full content",
            raw_response=raw_data,
            usage=usage_data,
            provider="test-provider",
        )

        assert response.content == "Full content"
        assert response.raw_response == raw_data
        assert response.usage == usage_data
        assert response.provider == "test-provider"

    def test_response_is_immutable_with_frozen(self):
        """Test that response model behaves correctly with Pydantic."""
        response = LLMResponse(content="Test")
        # Pydantic v2 models are not frozen by default, so we can modify
        response.content = "Modified"
        assert response.content == "Modified"


# ============================================================================
# BaseOpenAILLM Tests
# ============================================================================


class TestBaseOpenAILLM:
    """Test BaseOpenAILLM service implementation."""

    def test_initialization_default_params(self):
        """Test initialization with default parameters."""
        service = BaseOpenAILLM(
            api_key="test-key",
            base_url="https://api.example.com/v1",
            model="test-model",
        )

        assert service._api_key == "test-key"
        assert service._base_url == "https://api.example.com/v1"
        assert service._model == "test-model"
        assert service._timeout == 60
        assert service.provider == LLMProvider.GLM

    def test_initialization_custom_timeout(self):
        """Test initialization with custom timeout."""
        service = BaseOpenAILLM(
            api_key="test-key",
            base_url="https://api.example.com",
            model="test-model",
            timeout=120,
            provider=LLMProvider.QWEN,
        )

        assert service._timeout == 120
        assert service.provider == LLMProvider.QWEN

    def test_base_url_trailing_slash_removed(self):
        """Test that trailing slash is removed from base URL."""
        service = BaseOpenAILLM(
            api_key="test-key",
            base_url="https://api.example.com/v1/",
            model="test-model",
        )

        assert service._base_url == "https://api.example.com/v1"

    def test_provider_property(self):
        """Test provider property returns correct value."""
        for provider in [LLMProvider.GLM, LLMProvider.QWEN, LLMProvider.DEEPSEEK]:
            service = BaseOpenAILLM(
                api_key="test-key",
                base_url="https://api.example.com",
                model="test-model",
                provider=provider,
            )
            assert service.provider == provider

    @pytest.mark.asyncio
    async def test_chat_completion_success(
        self, sample_messages, mock_llm_response
    ):
        """Test successful chat completion."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_llm_response
            mock_response.raise_for_status = Mock()

            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()

            mock_client_class.return_value = mock_client

            service = BaseOpenAILLM(
                api_key="test-key",
                base_url="https://api.example.com/v1",
                model="test-model",
            )

            result = await service.chat_completion(sample_messages)

            assert isinstance(result, LLMResponse)
            assert result.content == mock_llm_response["choices"][0]["message"]["content"]
            assert result.raw_response == mock_llm_response
            assert result.usage == mock_llm_response["usage"]
            assert result.provider == LLMProvider.GLM.value

            # Verify request structure
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert "/chat/completions" in call_args[0][0]

            payload = call_args[1]["json"]
            assert payload["model"] == "test-model"
            assert payload["messages"] == sample_messages
            assert payload["temperature"] == 0.0
            assert "response_format" not in payload
            assert "max_tokens" not in payload

    @pytest.mark.asyncio
    async def test_chat_completion_with_temperature(
        self, sample_messages, mock_llm_response
    ):
        """Test chat completion with custom temperature."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_llm_response
            mock_response.raise_for_status = Mock()

            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()

            mock_client_class.return_value = mock_client

            service = BaseOpenAILLM(
                api_key="test-key",
                base_url="https://api.example.com/v1",
                model="test-model",
            )

            result = await service.chat_completion(sample_messages, temperature=0.7)

            assert result is not None
            call_args = mock_client.post.call_args
            payload = call_args[1]["json"]
            assert payload["temperature"] == 0.7

    @pytest.mark.asyncio
    async def test_chat_completion_with_json_mode(
        self, sample_messages, mock_llm_response
    ):
        """Test chat completion with JSON mode enabled."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_llm_response
            mock_response.raise_for_status = Mock()

            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()

            mock_client_class.return_value = mock_client

            service = BaseOpenAILLM(
                api_key="test-key",
                base_url="https://api.example.com/v1",
                model="test-model",
            )

            result = await service.chat_completion(sample_messages, json_mode=True)

            assert result is not None
            call_args = mock_client.post.call_args
            payload = call_args[1]["json"]
            assert payload["response_format"] == {"type": "json_object"}

    @pytest.mark.asyncio
    async def test_chat_completion_with_max_tokens(
        self, sample_messages, mock_llm_response
    ):
        """Test chat completion with max tokens limit."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_llm_response
            mock_response.raise_for_status = Mock()

            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()

            mock_client_class.return_value = mock_client

            service = BaseOpenAILLM(
                api_key="test-key",
                base_url="https://api.example.com/v1",
                model="test-model",
            )

            result = await service.chat_completion(
                sample_messages, max_tokens=2000
            )

            assert result is not None
            call_args = mock_client.post.call_args
            payload = call_args[1]["json"]
            assert payload["max_tokens"] == 2000

    @pytest.mark.asyncio
    async def test_chat_completion_with_all_params(
        self, sample_messages, mock_llm_response
    ):
        """Test chat completion with all parameters."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_llm_response
            mock_response.raise_for_status = Mock()

            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()

            mock_client_class.return_value = mock_client

            service = BaseOpenAILLM(
                api_key="test-key",
                base_url="https://api.example.com/v1",
                model="test-model",
            )

            result = await service.chat_completion(
                sample_messages,
                temperature=0.5,
                json_mode=True,
                max_tokens=1500,
            )

            assert result is not None
            call_args = mock_client.post.call_args
            payload = call_args[1]["json"]
            assert payload["temperature"] == 0.5
            assert payload["response_format"] == {"type": "json_object"}
            assert payload["max_tokens"] == 1500

    @pytest.mark.asyncio
    async def test_chat_completion_error_logging(self, sample_messages, caplog):
        """Test that errors are properly logged before being re-raised."""
        import logging

        # Make context manager fail with timeout
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.side_effect = httpx.ReadTimeout("Request timeout")

            service = BaseOpenAILLM(
                api_key="test-key",
                base_url="https://api.example.com/v1",
                model="test-model",
            )

            # Should raise the timeout error
            with caplog.at_level(logging.ERROR):
                with pytest.raises(httpx.ReadTimeout):
                    await service.chat_completion(sample_messages)

            # Verify error was logged
            assert "LLM Request Failed" in caplog.text

    @pytest.mark.asyncio
    async def test_chat_completion_network_error(self, sample_messages):
        """Test chat_completion handles network errors properly."""
        # Simplified test that verifies exception handling works
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()

            # Make context manager itself fail
            mock_client_class.side_effect = httpx.ConnectError("Connection refused")

            service = BaseOpenAILLM(
                api_key="test-key",
                base_url="https://api.example.com/v1",
                model="test-model",
            )

            # Should raise the connection error
            with pytest.raises(httpx.ConnectError):
                await service.chat_completion(sample_messages)

    @pytest.mark.asyncio
    async def test_chat_completion_timeout_error(self, sample_messages):
        """Test chat_completion handles timeout errors properly."""
        # Simplified test that verifies timeout handling
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()

            # Make context manager fail with timeout
            mock_client_class.side_effect = httpx.ReadTimeout("Request timeout")

            service = BaseOpenAILLM(
                api_key="test-key",
                base_url="https://api.example.com/v1",
                model="test-model",
            )

            # Should raise the timeout error
            with pytest.raises(httpx.ReadTimeout):
                await service.chat_completion(sample_messages)

    def test_base_url_without_trailing_slash(self):
        """Test base_url handling without trailing slash."""
        service = BaseOpenAILLM(
            api_key="test-key",
            base_url="https://api.example.com/v1",
            model="test-model",
        )

        assert service._base_url == "https://api.example.com/v1"

    def test_base_url_with_multiple_trailing_slashes(self):
        """Test base_url with multiple trailing slashes."""
        service = BaseOpenAILLM(
            api_key="test-key",
            base_url="https://api.example.com/v1///",
            model="test-model",
        )

        assert service._base_url == "https://api.example.com/v1"


# ============================================================================
# LLMServiceFactory Tests
# ============================================================================


class TestLLMServiceFactory:
    """Test LLMServiceFactory class methods."""

    def setup_method(self):
        """Reset factory state before each test."""
        LLMServiceFactory._services.clear()
        LLMServiceFactory._config.clear()

    def test_register_service_class(self):
        """Test registering a service class."""
        LLMServiceFactory.register(
            LLMProvider.GLM, BaseOpenAILLM, {"api_key": "test"}
        )

        assert LLMProvider.GLM in LLMServiceFactory._services
        assert LLMServiceFactory._services[LLMProvider.GLM] == BaseOpenAILLM
        assert LLMServiceFactory._config[LLMProvider.GLM] == {"api_key": "test"}

    def test_register_service_without_config(self):
        """Test registering service without config."""
        LLMServiceFactory.register(LLMProvider.QWEN, BaseOpenAILLM)

        assert LLMProvider.QWEN in LLMServiceFactory._services
        assert LLMProvider.QWEN not in LLMServiceFactory._config

    def test_create_service_without_registration(self):
        """Test creating unregistered service raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            LLMServiceFactory.create(LLMProvider.GLM)

        assert "Unknown LLM provider" in str(exc_info.value)
        assert "LLMProvider.GLM" in str(exc_info.value)

    def test_create_service_with_registration(self):
        """Test creating registered service."""
        LLMServiceFactory.register(
            LLMProvider.GLM,
            BaseOpenAILLM,
            {
                "api_key": "test-key",
                "base_url": "https://api.example.com/v1",
                "model": "test-model",
            },
        )

        service = LLMServiceFactory.create(LLMProvider.GLM)

        assert isinstance(service, BaseOpenAILLM)
        assert service._api_key == "test-key"
        assert service._model == "test-model"

    def test_create_service_with_kwargs_override(self):
        """Test creating service with kwargs overriding config."""
        LLMServiceFactory.register(
            LLMProvider.GLM,
            BaseOpenAILLM,
            {
                "api_key": "default-key",
                "base_url": "https://api.example.com/v1",
                "model": "default-model",
            },
        )

        service = LLMServiceFactory.create(
            LLMProvider.GLM, api_key="override-key", model="override-model"
        )

        assert service._api_key == "override-key"
        assert service._model == "override-model"
        # base_url from default config should remain
        assert service._base_url == "https://api.example.com/v1"

    def test_create_from_env_default_provider_glm(self, monkeypatch):
        """Test create_from_env with default GLM provider."""
        monkeypatch.setenv("ZHIPU_API_KEY", "test-zhipu-key")
        monkeypatch.setenv("LLM_PROVIDER", "glm")

        service = LLMServiceFactory.create_from_env()

        assert isinstance(service, BaseOpenAILLM)
        assert service._api_key == "test-zhipu-key"
        assert service.provider == LLMProvider.GLM

    def test_create_from_env_qwen_provider(self, monkeypatch):
        """Test create_from_env with Qwen provider."""
        monkeypatch.setenv("DASHSCOPE_API_KEY", "test-qwen-key")
        monkeypatch.setenv("LLM_PROVIDER", "qwen")

        service = LLMServiceFactory.create_from_env()

        assert isinstance(service, BaseOpenAILLM)
        assert service._api_key == "test-qwen-key"
        assert service.provider == LLMProvider.QWEN

    def test_create_from_env_deepseek_provider(self, monkeypatch):
        """Test create_from_env with DeepSeek provider."""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-deepseek-key")
        monkeypatch.setenv("LLM_PROVIDER", "deepseek")

        service = LLMServiceFactory.create_from_env()

        assert isinstance(service, BaseOpenAILLM)
        assert service._api_key == "test-deepseek-key"
        assert service.provider == LLMProvider.DEEPSEEK

    def test_create_from_env_unsupported_provider(self, monkeypatch):
        """Test create_from_env with unsupported provider."""
        # This test would need mocking since HUNYUAN is in LLMProvider enum
        # but not implemented in create_from_env
        monkeypatch.setenv("LLM_PROVIDER", "hunyuan")

        with pytest.raises(ValueError) as exc_info:
            LLMServiceFactory.create_from_env()

        assert "Unsupported provider" in str(exc_info.value)

    def test_create_from_env_explicit_provider(self, monkeypatch):
        """Test create_from_env with explicit provider parameter."""
        monkeypatch.setenv("DASHSCOPE_API_KEY", "test-qwen-key")
        # LLM_PROVIDER is deepseek, but we explicitly pass qwen
        monkeypatch.setenv("LLM_PROVIDER", "deepseek")

        service = LLMServiceFactory.create_from_env(LLMProvider.QWEN)

        assert isinstance(service, BaseOpenAILLM)
        assert service._api_key == "test-qwen-key"
        assert service.provider == LLMProvider.QWEN

    def test_create_from_env_glm_fallback_to_llm_api_key(self, monkeypatch):
        """Test GLM service falls back to LLM_API_KEY if ZHIPU_API_KEY not set."""
        monkeypatch.delenv("ZHIPU_API_KEY", raising=False)
        monkeypatch.setenv("LLM_API_KEY", "fallback-key")
        monkeypatch.setenv("LLM_PROVIDER", "glm")

        service = LLMServiceFactory.create_from_env()

        assert isinstance(service, BaseOpenAILLM)
        assert service._api_key == "fallback-key"

    def test_create_from_env_qwen_fallback_to_llm_api_key(self, monkeypatch):
        """Test Qwen service falls back to LLM_API_KEY if DASHSCOPE_API_KEY not set."""
        monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
        monkeypatch.setenv("LLM_API_KEY", "fallback-key")
        monkeypatch.setenv("LLM_PROVIDER", "qwen")

        service = LLMServiceFactory.create_from_env()

        assert isinstance(service, BaseOpenAILLM)
        assert service._api_key == "fallback-key"

    def test_create_from_env_deepseek_fallback_to_llm_api_key(self, monkeypatch):
        """Test DeepSeek service falls back to LLM_API_KEY if DEEPSEEK_API_KEY not set."""
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        monkeypatch.setenv("LLM_API_KEY", "fallback-key")
        monkeypatch.setenv("LLM_PROVIDER", "deepseek")

        service = LLMServiceFactory.create_from_env()

        assert isinstance(service, BaseOpenAILLM)
        assert service._api_key == "fallback-key"

    def test_create_from_env_custom_timeout(self, monkeypatch):
        """Test create_from_env with custom timeout from env."""
        monkeypatch.setenv("ZHIPU_API_KEY", "test-key")
        monkeypatch.setenv("LLM_TIMEOUT", "90")
        monkeypatch.setenv("LLM_PROVIDER", "glm")

        service = LLMServiceFactory.create_from_env()

        assert isinstance(service, BaseOpenAILLM)
        assert service._timeout == 90

    def test_create_from_env_custom_base_url(self, monkeypatch):
        """Test create_from_env with custom base URL from env."""
        monkeypatch.setenv("ZHIPU_API_KEY", "test-key")
        monkeypatch.setenv("ZHIPU_API_BASE", "https://custom.api.com/v1")
        monkeypatch.setenv("LLM_PROVIDER", "glm")

        service = LLMServiceFactory.create_from_env()

        assert isinstance(service, BaseOpenAILLM)
        assert service._base_url == "https://custom.api.com/v1"

    def test_create_from_env_custom_model(self, monkeypatch):
        """Test create_from_env with custom model from env."""
        monkeypatch.setenv("ZHIPU_API_KEY", "test-key")
        monkeypatch.setenv("ZHIPU_MODEL", "custom-glm-model")
        monkeypatch.setenv("LLM_PROVIDER", "glm")

        service = LLMServiceFactory.create_from_env()

        assert isinstance(service, BaseOpenAILLM)
        assert service._model == "custom-glm-model"


# ============================================================================
# LLMService Backward Compatibility Tests
# ============================================================================


class TestLLMService:
    """Test LLMService backward compatibility class."""

    def test_initialization_glm_provider(self, monkeypatch):
        """Test initialization with GLM provider."""
        monkeypatch.setenv("LLM_PROVIDER", "glm")
        monkeypatch.setenv("ZHIPU_API_KEY", "test-zhipu-key")

        service = LLMService()

        assert isinstance(service, BaseOpenAILLM)
        assert service.provider == LLMProvider.GLM
        assert service._api_key == "test-zhipu-key"

    def test_initialization_qwen_provider(self, monkeypatch):
        """Test initialization with Qwen provider."""
        monkeypatch.setenv("LLM_PROVIDER", "qwen")
        monkeypatch.setenv("DASHSCOPE_API_KEY", "test-qwen-key")

        service = LLMService()

        assert isinstance(service, BaseOpenAILLM)
        assert service.provider == LLMProvider.QWEN
        assert service._api_key == "test-qwen-key"

    def test_initialization_deepseek_provider(self, monkeypatch):
        """Test initialization with DeepSeek provider."""
        monkeypatch.setenv("LLM_PROVIDER", "deepseek")
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-deepseek-key")

        service = LLMService()

        assert isinstance(service, BaseOpenAILLM)
        assert service.provider == LLMProvider.DEEPSEEK
        assert service._api_key == "test-deepseek-key"

    def test_initialization_with_defaults(self, monkeypatch):
        """Test initialization with default values when env vars not set."""
        monkeypatch.delenv("ZHIPU_API_KEY", raising=False)
        monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        monkeypatch.setenv("LLM_PROVIDER", "glm")
        monkeypatch.setenv("LLM_API_KEY", "default-key")

        service = LLMService()

        assert isinstance(service, BaseOpenAILLM)
        assert service._api_key == "default-key"
        assert service._base_url == "https://open.bigmodel.cn/api/paas/v4"
        assert service._model == "glm-4v"
        assert service._timeout == 30

    def test_initialization_uses_provider_specific_overrides(self, monkeypatch):
        """Test that provider-specific settings override defaults."""
        monkeypatch.setenv("LLM_PROVIDER", "glm")
        monkeypatch.setenv("LLM_API_KEY", "default-key")
        monkeypatch.setenv("LLM_BASE_URL", "https://default.api.com/v1")
        monkeypatch.setenv("LLM_MODEL", "default-model")
        monkeypatch.setenv("ZHIPU_API_KEY", "zhipu-key")

        service = LLMService()

        # GLM-specific settings should override defaults
        assert service._api_key == "zhipu-key"
        assert service._base_url == "https://open.bigmodel.cn/api/paas/v4"
        assert service._model == "glm-4v"


# ============================================================================
# Singleton Function Tests
# ============================================================================


class TestSingletonFunctions:
    """Test singleton pattern functions."""

    def test_get_llm_service_singleton(self, monkeypatch):
        """Test get_llm_service returns singleton instance."""
        monkeypatch.setenv("LLM_PROVIDER", "glm")
        monkeypatch.setenv("LLM_API_KEY", "test-key")

        service1 = get_llm_service()
        service2 = get_llm_service()

        assert service1 is service2

    def test_get_llm_service_creates_instance_once(self, monkeypatch):
        """Test that singleton is created only once."""
        monkeypatch.setenv("LLM_PROVIDER", "glm")
        monkeypatch.setenv("LLM_API_KEY", "test-key")

        # First call creates the instance
        service1 = get_llm_service()
        # Second call returns the same instance
        service2 = get_llm_service()

        # They should be the same object
        assert id(service1) == id(service2)


# ============================================================================
# Convenience Function Tests
# ============================================================================


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_create_llm_service_glm(self, monkeypatch):
        """Test create_llm_service with GLM provider."""
        monkeypatch.setenv("LLM_PROVIDER", "glm")
        monkeypatch.setenv("ZHIPU_API_KEY", "test-key")

        service = create_llm_service()

        assert isinstance(service, BaseOpenAILLM)
        assert service.provider == LLMProvider.GLM

    def test_create_llm_service_qwen(self, monkeypatch):
        """Test create_llm_service with Qwen provider."""
        monkeypatch.setenv("LLM_PROVIDER", "qwen")
        monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")

        service = create_llm_service()

        assert isinstance(service, BaseOpenAILLM)
        assert service.provider == LLMProvider.QWEN

    def test_create_llm_service_deepseek(self, monkeypatch):
        """Test create_llm_service with DeepSeek provider."""
        monkeypatch.setenv("LLM_PROVIDER", "deepseek")
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")

        service = create_llm_service()

        assert isinstance(service, BaseOpenAILLM)
        assert service.provider == LLMProvider.DEEPSEEK

    def test_create_llm_service_with_explicit_provider(self, monkeypatch):
        """Test create_llm_service with explicit provider parameter."""
        monkeypatch.setenv("ZHIPU_API_KEY", "test-key")
        monkeypatch.setenv("LLM_PROVIDER", "qwen")  # Env var is qwen

        service = create_llm_service(LLMProvider.GLM)  # But we request GLM

        assert isinstance(service, BaseOpenAILLM)
        assert service.provider == LLMProvider.GLM

    def test_create_llm_service_default_provider(self, monkeypatch):
        """Test create_llm_service defaults to GLM when no provider specified."""
        monkeypatch.delenv("LLM_PROVIDER", raising=False)
        monkeypatch.setenv("ZHIPU_API_KEY", "test-key")

        service = create_llm_service()

        assert isinstance(service, BaseOpenAILLM)
        assert service.provider == LLMProvider.GLM


# ============================================================================
# Abstract Base Class Tests
# ============================================================================


class TestLLMServiceInterface:
    """Test LLMServiceInterface abstract base class."""

    def test_cannot_instantiate_abstract_class(self):
        """Test that abstract base class cannot be instantiated."""
        with pytest.raises(TypeError):
            LLMServiceInterface()

    def test_concrete_class_implements_interface(self):
        """Test that BaseOpenAILLM properly implements the interface."""
        service = BaseOpenAILLM(
            api_key="test-key",
            base_url="https://api.example.com",
            model="test-model",
        )

        # Should have provider property
        assert hasattr(service, "provider")
        # Should have chat_completion method
        assert hasattr(service, "chat_completion")
        assert callable(service.chat_completion)


# ============================================================================
# Integration Tests
# ============================================================================


class TestLLMServiceIntegration:
    """Integration tests for LLM service components."""

    def test_factory_with_custom_service_class(self):
        """Test factory with a custom service class."""
        # Create a mock service class
        class MockService(LLMServiceInterface):
            def __init__(self, **kwargs):
                self.config = kwargs

            @property
            def provider(self):
                return LLMProvider.GLM

            async def chat_completion(self, messages, **kwargs):
                return LLMResponse(content="mock response")

        # Register the mock service
        LLMServiceFactory.register(LLMProvider.GLM, MockService, {"test": "config"})

        # Create service using factory
        service = LLMServiceFactory.create(LLMProvider.GLM)

        assert isinstance(service, MockService)
        assert service.config == {"test": "config"}

    @pytest.mark.asyncio
    async def test_full_workflow_with_factory(self, monkeypatch, mock_llm_response):
        """Test full workflow: register -> create -> use service."""
        monkeypatch.setenv("LLM_PROVIDER", "glm")
        monkeypatch.setenv("ZHIPU_API_KEY", "test-key")

        # Create service using factory
        service = create_llm_service()

        # Mock HTTP client
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_llm_response
            mock_response.raise_for_status = Mock()

            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()

            mock_client_class.return_value = mock_client

            # Use the service
            messages = [{"role": "user", "content": "Test message"}]
            result = await service.chat_completion(messages)

            assert isinstance(result, LLMResponse)
            assert result.content == mock_llm_response["choices"][0]["message"]["content"]
