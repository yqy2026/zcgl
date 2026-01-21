"""
Comprehensive unit tests for vision services.

Tests cover:
- zhipu_vision_service.py
- deepseek_vision_service.py
- hunyuan_vision_service.py
- qwen_vision_service.py

Target: 70%+ coverage for each service
"""

import base64
from io import BytesIO
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
from PIL import Image

from src.services.core.base_vision_service import VisionAPIError
from src.services.core.deepseek_vision_service import (
    DeepSeekVisionResponse,
    DeepSeekVisionService,
    get_deepseek_vision_service,
)
from src.services.core.hunyuan_vision_service import (
    HunyuanVisionResponse,
    HunyuanVisionService,
    get_hunyuan_vision_service,
)
from src.services.core.qwen_vision_service import (
    QwenVisionResponse,
    QwenVisionService,
    get_qwen_vision_service,
)

# Import all vision services and their response models
from src.services.core.zhipu_vision_service import (
    ZhipuVisionService,
    get_zhipu_vision_service,
)

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def temp_image_file(tmp_path):
    """Create a temporary test image file."""
    image = Image.new("RGB", (100, 100), color="red")
    image_path = tmp_path / "test_image.png"
    image.save(image_path, "PNG")
    return str(image_path)


@pytest.fixture
def temp_jpeg_file(tmp_path):
    """Create a temporary test JPEG file."""
    image = Image.new("RGB", (100, 100), color="blue")
    image_path = tmp_path / "test_image.jpg"
    image.save(image_path, "JPEG")
    return str(image_path)


@pytest.fixture
def sample_base64_image():
    """Create a sample base64 encoded image."""
    image = Image.new("RGB", (100, 100), color="red")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


@pytest.fixture
def mock_zhipu_response():
    """Mock Zhipu API response."""
    return {
        "choices": [
            {
                "message": {
                    "content": '{"contract_number": "TEST-001", "party_a": "Company A"}',
                    "role": "assistant",
                },
                "finish_reason": "stop",
                "index": 0,
            }
        ],
        "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        "model": "glm-4v",
        "id": "test-id",
    }


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI-compatible API response (for DeepSeek, Hunyuan, Qwen)."""
    return {
        "choices": [
            {
                "message": {
                    "content": '{"contract_number": "TEST-001", "party_a": "Company A"}',
                    "role": "assistant",
                },
                "finish_reason": "stop",
                "index": 0,
            }
        ],
        "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        "model": "vision-model",
        "id": "test-id",
    }


# ============================================================================
# Zhipu Vision Service Tests
# ============================================================================


class TestZhipuVisionService:
    """Test Zhipu GLM-4V vision service."""

    def test_initialization_with_custom_timeout(self, monkeypatch):
        """Test service initialization with custom timeout."""
        monkeypatch.setenv("ZHIPU_TIMEOUT", "60")
        monkeypatch.setenv("ZHIPU_API_KEY", "test-key")
        service = ZhipuVisionService()

        assert service.timeout == 60

    @pytest.mark.asyncio
    async def test_extract_from_images_success(
        self, temp_image_file, mock_zhipu_response, monkeypatch
    ):
        """Test successful image extraction."""
        monkeypatch.setenv("ZHIPU_API_KEY", "test-key")

        with patch("src.services.core.zhipu_vision_service.httpx") as mock_httpx:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_zhipu_response
            mock_response.raise_for_status = Mock()

            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()

            mock_httpx.AsyncClient = Mock(return_value=mock_client)

            service = ZhipuVisionService()
            result = await service.extract_from_images(
                [temp_image_file], "Extract contract information"
            )

            assert result == mock_zhipu_response["choices"][0]["message"]["content"]
            mock_client.post.assert_called_once()

            # Verify request structure
            call_args = mock_client.post.call_args
            assert "chat/completions" in call_args[0][0]
            payload = call_args[1]["json"]
            assert payload["model"] == "glm-4v"
            assert payload["temperature"] == 0.1
            assert len(payload["messages"][0]["content"]) == 2  # image + text

    @pytest.mark.asyncio
    async def test_extract_from_images_with_custom_params(
        self, temp_image_file, mock_zhipu_response, monkeypatch
    ):
        """Test image extraction with custom parameters."""
        monkeypatch.setenv("ZHIPU_API_KEY", "test-key")

        with patch("src.services.core.zhipu_vision_service.httpx") as mock_httpx:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_zhipu_response
            mock_response.raise_for_status = Mock()

            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()

            mock_httpx.AsyncClient = Mock(return_value=mock_client)

            service = ZhipuVisionService()
            result = await service.extract_from_images(
                [temp_image_file],
                "Extract contract information",
                temperature=0.5,
                max_tokens=2048,
            )

            assert result is not None
            call_args = mock_client.post.call_args
            payload = call_args[1]["json"]
            assert payload["temperature"] == 0.5

    @pytest.mark.asyncio
    async def test_extract_from_images_multiple_images(
        self, temp_image_file, temp_jpeg_file, mock_zhipu_response, monkeypatch
    ):
        """Test extraction with multiple images."""
        monkeypatch.setenv("ZHIPU_API_KEY", "test-key")

        with patch("src.services.core.zhipu_vision_service.httpx") as mock_httpx:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_zhipu_response
            mock_response.raise_for_status = Mock()

            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()

            mock_httpx.AsyncClient = Mock(return_value=mock_client)

            service = ZhipuVisionService()
            result = await service.extract_from_images(
                [temp_image_file, temp_jpeg_file], "Extract from both images"
            )

            assert result is not None
            call_args = mock_client.post.call_args
            payload = call_args[1]["json"]
            # Should have 2 images + 1 text prompt
            assert len(payload["messages"][0]["content"]) == 3

    @pytest.mark.asyncio
    async def test_extract_from_images_http_401_error(
        self, temp_image_file, monkeypatch
    ):
        """Test extraction with HTTP 401 authentication error."""
        monkeypatch.setenv("ZHIPU_API_KEY", "invalid-key")

        with patch("src.services.core.zhipu_vision_service.httpx") as mock_httpx:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.text = "Unauthorized"
            mock_response.json.return_value = {"error": "Invalid API key"}

            error = httpx.HTTPStatusError(
                "Authentication failed", request=Mock(), response=mock_response
            )

            # Make raise_for_status() raise the error, not post()
            # Track calls and verify error is raised
            def track_raise(*args, **kwargs):
                print(f"DEBUG: raise_for_status called, will raise: {error}")
                raise error

            mock_response.raise_for_status = Mock(side_effect=track_raise)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()

            mock_httpx.AsyncClient = Mock(return_value=mock_client)

            service = ZhipuVisionService()

            with pytest.raises(VisionAPIError) as exc_info:
                await service.extract_from_images([temp_image_file], "Extract")
            assert exc_info.value.status_code == 401
            assert exc_info.value.retryable is False

    @pytest.mark.asyncio
    async def test_extract_from_images_http_429_error(
        self, temp_image_file, monkeypatch
    ):
        """Test extraction with HTTP 429 rate limit error (should be retryable)."""
        monkeypatch.setenv("ZHIPU_API_KEY", "test-key")

        with patch("src.services.core.zhipu_vision_service.httpx") as mock_httpx:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 429
            mock_response.text = "Too many requests"
            mock_response.json.return_value = {"error": "Rate limit"}

            error = httpx.HTTPStatusError(
                "Rate limit exceeded", request=Mock(), response=mock_response
            )

            # Track calls and verify error is raised
            def track_raise(*args, **kwargs):
                print(f"DEBUG: raise_for_status called, will raise: {error}")
                raise error

            mock_response.raise_for_status = Mock(side_effect=track_raise)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()

            mock_httpx.AsyncClient = Mock(return_value=mock_client)

            service = ZhipuVisionService()

            with pytest.raises(VisionAPIError) as exc_info:
                await service.extract_from_images([temp_image_file], "Extract")

            assert exc_info.value.status_code == 429
            assert exc_info.value.retryable is True

    @pytest.mark.asyncio
    async def test_extract_from_images_http_500_error(
        self, temp_image_file, monkeypatch
    ):
        """Test extraction with HTTP 500 server error (should be retryable)."""
        monkeypatch.setenv("ZHIPU_API_KEY", "test-key")

        with patch("src.services.core.zhipu_vision_service.httpx") as mock_httpx:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.text = "Internal server error"
            mock_response.json.side_effect = Exception("No JSON")

            error = httpx.HTTPStatusError(
                "Server error", request=Mock(), response=mock_response
            )
            mock_client.post = AsyncMock(side_effect=error)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()

            mock_httpx.AsyncClient = Mock(return_value=mock_client)

            service = ZhipuVisionService()

            with pytest.raises(VisionAPIError) as exc_info:
                await service.extract_from_images([temp_image_file], "Extract")

            assert exc_info.value.status_code == 500
            assert exc_info.value.retryable is True

    @pytest.mark.asyncio
    async def test_extract_from_images_network_error(
        self, temp_image_file, monkeypatch
    ):
        """Test extraction with network error."""
        monkeypatch.setenv("ZHIPU_API_KEY", "test-key")

        with patch("src.services.core.zhipu_vision_service.httpx") as mock_httpx:
            mock_client = AsyncMock()

            error = httpx.ConnectError("Connection refused")
            mock_client.post = AsyncMock(side_effect=error)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()

            mock_httpx.AsyncClient = Mock(return_value=mock_client)

            service = ZhipuVisionService()

            with pytest.raises(VisionAPIError) as exc_info:
                await service.extract_from_images([temp_image_file], "Extract")

            assert exc_info.value.retryable is True
            assert exc_info.value.status_code is None

    @pytest.mark.asyncio
    async def test_extract_from_images_timeout_error(
        self, temp_image_file, monkeypatch
    ):
        """Test extraction with timeout error."""
        monkeypatch.setenv("ZHIPU_API_KEY", "test-key")

        with patch("src.services.core.zhipu_vision_service.httpx") as mock_httpx:
            mock_client = AsyncMock()

            error = httpx.ReadTimeout("Request timeout")
            mock_client.post = AsyncMock(side_effect=error)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()

            mock_httpx.AsyncClient = Mock(return_value=mock_client)

            service = ZhipuVisionService()

            with pytest.raises(VisionAPIError) as exc_info:
                await service.extract_from_images([temp_image_file], "Extract")

            assert exc_info.value.retryable is True

    @pytest.mark.asyncio
    async def test_extract_from_images_empty_choices(
        self, temp_image_file, monkeypatch
    ):
        """Test extraction when API returns empty choices."""
        monkeypatch.setenv("ZHIPU_API_KEY", "test-key")

        with patch("src.services.core.zhipu_vision_service.httpx") as mock_httpx:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"choices": []}
            mock_response.raise_for_status = Mock()

            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()

            mock_httpx.AsyncClient = Mock(return_value=mock_client)

            service = ZhipuVisionService()

            with pytest.raises(VisionAPIError) as exc_info:
                await service.extract_from_images([temp_image_file], "Extract")

            assert "no choices" in str(exc_info.value).lower()
            assert exc_info.value.retryable is True

    @pytest.mark.asyncio
    async def test_extract_from_images_invalid_choice_format(
        self, temp_image_file, monkeypatch
    ):
        """Test extraction when API returns invalid choice format."""
        monkeypatch.setenv("ZHIPU_API_KEY", "test-key")

        with patch("src.services.core.zhipu_vision_service.httpx") as mock_httpx:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"choices": ["invalid"]}
            mock_response.raise_for_status = Mock()

            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()

            mock_httpx.AsyncClient = Mock(return_value=mock_client)

            service = ZhipuVisionService()

            with pytest.raises(VisionAPIError) as exc_info:
                await service.extract_from_images([temp_image_file], "Extract")

            assert "invalid choice format" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_extract_from_images_invalid_message_format(
        self, temp_image_file, monkeypatch
    ):
        """Test extraction when API returns invalid message format."""
        monkeypatch.setenv("ZHIPU_API_KEY", "test-key")

        with patch("src.services.core.zhipu_vision_service.httpx") as mock_httpx:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"choices": [{"message": "not a dict"}]}
            mock_response.raise_for_status = Mock()

            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()

            mock_httpx.AsyncClient = Mock(return_value=mock_client)

            service = ZhipuVisionService()

            with pytest.raises(VisionAPIError) as exc_info:
                await service.extract_from_images([temp_image_file], "Extract")

            assert "invalid message format" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_extract_from_images_unexpected_error(
        self, temp_image_file, monkeypatch
    ):
        """Test extraction with unexpected error."""
        monkeypatch.setenv("ZHIPU_API_KEY", "test-key")

        with patch("src.services.core.zhipu_vision_service.httpx") as mock_httpx:
            mock_client = AsyncMock()

            error = Exception("Unexpected error")
            mock_client.post = AsyncMock(side_effect=error)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()

            mock_httpx.AsyncClient = Mock(return_value=mock_client)

            service = ZhipuVisionService()

            with pytest.raises(VisionAPIError) as exc_info:
                await service.extract_from_images([temp_image_file], "Extract")

            assert exc_info.value.retryable is False
            assert exc_info.value.status_code is None

    def test_singleton_getter(self, monkeypatch):
        """Test singleton pattern for service getter."""
        monkeypatch.setenv("ZHIPU_API_KEY", "test-key")

        service1 = get_zhipu_vision_service()
        service2 = get_zhipu_vision_service()

        assert service1 is service2


# ============================================================================
# DeepSeek Vision Service Tests
# ============================================================================


class TestDeepSeekVisionService:
    """Test DeepSeek-VL vision service."""

    def test_initialization_with_custom_timeout(self, monkeypatch):
        """Test service initialization with custom timeout."""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
        monkeypatch.setenv("DEEPSEEK_TIMEOUT", "90")
        service = DeepSeekVisionService()

        assert service.timeout == 90

    def test_encode_image(self, temp_image_file, monkeypatch):
        """Test image encoding to base64."""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
        service = DeepSeekVisionService()

        encoded = service._encode_image(temp_image_file)
        assert isinstance(encoded, str)
        assert len(encoded) > 0

    def test_encode_image_file_not_found(self, monkeypatch):
        """Test encoding non-existent file raises error."""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
        service = DeepSeekVisionService()

        with pytest.raises(FileNotFoundError):
            service._encode_image("/nonexistent/file.png")

    def test_get_mime_type(self, temp_image_file, temp_jpeg_file, monkeypatch):
        """Test MIME type detection."""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
        service = DeepSeekVisionService()

        assert service._get_mime_type(temp_image_file) == "image/png"
        assert service._get_mime_type(temp_jpeg_file) == "image/jpeg"

    @pytest.mark.asyncio
    async def test_extract_from_images_success(
        self, temp_image_file, mock_openai_response, monkeypatch
    ):
        """Test successful image extraction."""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")

        with patch("src.services.core.deepseek_vision_service.httpx") as mock_httpx:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_openai_response
            mock_response.raise_for_status = Mock()

            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()

            mock_httpx.AsyncClient = Mock(return_value=mock_client)

            service = DeepSeekVisionService()
            result = await service.extract_from_images(
                [temp_image_file], "Extract contract information"
            )

            assert isinstance(result, DeepSeekVisionResponse)
            assert (
                result.content
                == mock_openai_response["choices"][0]["message"]["content"]
            )
            assert result.usage == mock_openai_response["usage"]
            mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_extract_from_images_with_custom_params(
        self, temp_image_file, mock_openai_response, monkeypatch
    ):
        """Test extraction with custom parameters."""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")

        with patch("src.services.core.deepseek_vision_service.httpx") as mock_httpx:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_openai_response
            mock_response.raise_for_status = Mock()

            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()

            mock_httpx.AsyncClient = Mock(return_value=mock_client)

            service = DeepSeekVisionService()
            result = await service.extract_from_images(
                [temp_image_file],
                "Extract",
                temperature=0.7,
                max_tokens=2048,
            )

            assert result is not None
            call_args = mock_client.post.call_args
            payload = call_args[1]["json"]
            assert payload["temperature"] == 0.7
            assert payload["max_tokens"] == 2048

    @pytest.mark.asyncio
    async def test_extract_from_images_not_configured(
        self, temp_image_file, monkeypatch
    ):
        """Test extraction when API key is not configured."""
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

        service = DeepSeekVisionService()

        with pytest.raises(RuntimeError) as exc_info:
            await service.extract_from_images([temp_image_file], "Extract")

        assert "DEEPSEEK_API_KEY not configured" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_extract_from_images_http_error(self, temp_image_file, monkeypatch):
        """Test extraction with HTTP error."""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")

        with patch("src.services.core.deepseek_vision_service.httpx") as mock_httpx:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.text = "Unauthorized"

            error = httpx.HTTPStatusError(
                "Auth failed", request=Mock(), response=mock_response
            )
            mock_client.post = AsyncMock(side_effect=error)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()

            mock_httpx.AsyncClient = Mock(return_value=mock_client)

            service = DeepSeekVisionService()

            with pytest.raises(httpx.HTTPStatusError):
                await service.extract_from_images([temp_image_file], "Extract")

    @pytest.mark.asyncio
    async def test_extract_from_images_network_error(
        self, temp_image_file, monkeypatch
    ):
        """Test extraction with network error."""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")

        with patch("src.services.core.deepseek_vision_service.httpx") as mock_httpx:
            mock_client = AsyncMock()

            error = httpx.ConnectError("Network error")
            mock_client.post = AsyncMock(side_effect=error)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()

            mock_httpx.AsyncClient = Mock(return_value=mock_client)

            service = DeepSeekVisionService()

            with pytest.raises(httpx.ConnectError):
                await service.extract_from_images([temp_image_file], "Extract")

    def test_singleton_getter(self, monkeypatch):
        """Test singleton pattern for service getter."""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")

        service1 = get_deepseek_vision_service()
        service2 = get_deepseek_vision_service()

        assert service1 is service2


# ============================================================================
# Hunyuan Vision Service Tests
# ============================================================================


class TestHunyuanVisionService:
    """Test Hunyuan-Vision service."""

    def test_initialization_with_custom_timeout(self, monkeypatch):
        """Test service initialization with custom timeout."""
        monkeypatch.setenv("HUNYUAN_API_KEY", "test-key")
        monkeypatch.setenv("HUNYUAN_TIMEOUT", "180")
        service = HunyuanVisionService()

        assert service.timeout == 180

    def test_encode_image(self, temp_image_file, monkeypatch):
        """Test image encoding to base64."""
        monkeypatch.setenv("HUNYUAN_API_KEY", "test-key")
        service = HunyuanVisionService()

        encoded = service._encode_image(temp_image_file)
        assert isinstance(encoded, str)
        assert len(encoded) > 0

    def test_encode_image_file_not_found(self, monkeypatch):
        """Test encoding non-existent file raises error."""
        monkeypatch.setenv("HUNYUAN_API_KEY", "test-key")
        service = HunyuanVisionService()

        with pytest.raises(FileNotFoundError):
            service._encode_image("/nonexistent/file.png")

    def test_get_mime_type(self, temp_image_file, temp_jpeg_file, monkeypatch):
        """Test MIME type detection."""
        monkeypatch.setenv("HUNYUAN_API_KEY", "test-key")
        service = HunyuanVisionService()

        assert service._get_mime_type(temp_image_file) == "image/png"
        assert service._get_mime_type(temp_jpeg_file) == "image/jpeg"

    @pytest.mark.asyncio
    async def test_extract_from_images_success(
        self, temp_image_file, mock_openai_response, monkeypatch
    ):
        """Test successful image extraction."""
        monkeypatch.setenv("HUNYUAN_API_KEY", "test-key")

        with patch("src.services.core.hunyuan_vision_service.httpx") as mock_httpx:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_openai_response
            mock_response.raise_for_status = Mock()

            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()

            mock_httpx.AsyncClient = Mock(return_value=mock_client)

            service = HunyuanVisionService()
            result = await service.extract_from_images(
                [temp_image_file], "Extract contract information"
            )

            assert isinstance(result, HunyuanVisionResponse)
            assert (
                result.content
                == mock_openai_response["choices"][0]["message"]["content"]
            )
            assert result.usage == mock_openai_response["usage"]
            mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_extract_from_images_with_custom_params(
        self, temp_image_file, mock_openai_response, monkeypatch
    ):
        """Test extraction with custom parameters."""
        monkeypatch.setenv("HUNYUAN_API_KEY", "test-key")

        with patch("src.services.core.hunyuan_vision_service.httpx") as mock_httpx:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_openai_response
            mock_response.raise_for_status = Mock()

            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()

            mock_httpx.AsyncClient = Mock(return_value=mock_client)

            service = HunyuanVisionService()
            result = await service.extract_from_images(
                [temp_image_file],
                "Extract",
                temperature=0.3,
                max_tokens=3000,
            )

            assert result is not None
            call_args = mock_client.post.call_args
            payload = call_args[1]["json"]
            assert payload["temperature"] == 0.3
            assert payload["max_tokens"] == 3000

    @pytest.mark.asyncio
    async def test_extract_from_images_not_configured(
        self, temp_image_file, monkeypatch
    ):
        """Test extraction when API key is not configured."""
        monkeypatch.delenv("HUNYUAN_API_KEY", raising=False)

        service = HunyuanVisionService()

        with pytest.raises(RuntimeError) as exc_info:
            await service.extract_from_images([temp_image_file], "Extract")

        assert "HUNYUAN_API_KEY not configured" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_extract_from_images_http_error(self, temp_image_file, monkeypatch):
        """Test extraction with HTTP error."""
        monkeypatch.setenv("HUNYUAN_API_KEY", "test-key")

        with patch("src.services.core.hunyuan_vision_service.httpx") as mock_httpx:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 403
            mock_response.text = "Forbidden"

            error = httpx.HTTPStatusError(
                "Forbidden", request=Mock(), response=mock_response
            )
            mock_client.post = AsyncMock(side_effect=error)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()

            mock_httpx.AsyncClient = Mock(return_value=mock_client)

            service = HunyuanVisionService()

            with pytest.raises(httpx.HTTPStatusError):
                await service.extract_from_images([temp_image_file], "Extract")

    def test_singleton_getter(self, monkeypatch):
        """Test singleton pattern for service getter."""
        monkeypatch.setenv("HUNYUAN_API_KEY", "test-key")

        service1 = get_hunyuan_vision_service()
        service2 = get_hunyuan_vision_service()

        assert service1 is service2


# ============================================================================
# Qwen Vision Service Tests
# ============================================================================


class TestQwenVisionService:
    """Test Qwen-VL vision service."""

    def test_initialization_with_custom_timeout(self, monkeypatch):
        """Test service initialization with custom timeout."""
        monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
        monkeypatch.setenv("QWEN_TIMEOUT", "150")
        service = QwenVisionService()

        assert service.timeout == 150

    def test_encode_image(self, temp_image_file, monkeypatch):
        """Test image encoding to base64."""
        monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
        service = QwenVisionService()

        encoded = service._encode_image(temp_image_file)
        assert isinstance(encoded, str)
        assert len(encoded) > 0

    def test_encode_image_file_not_found(self, monkeypatch):
        """Test encoding non-existent file raises error."""
        monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
        service = QwenVisionService()

        with pytest.raises(FileNotFoundError):
            service._encode_image("/nonexistent/file.png")

    def test_get_mime_type(self, temp_image_file, temp_jpeg_file, monkeypatch):
        """Test MIME type detection."""
        monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
        service = QwenVisionService()

        assert service._get_mime_type(temp_image_file) == "image/png"
        assert service._get_mime_type(temp_jpeg_file) == "image/jpeg"

    @pytest.mark.asyncio
    async def test_extract_from_images_success(
        self, temp_image_file, mock_openai_response, monkeypatch
    ):
        """Test successful image extraction."""
        monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")

        with patch("src.services.core.qwen_vision_service.httpx") as mock_httpx:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_openai_response
            mock_response.raise_for_status = Mock()

            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()

            mock_httpx.AsyncClient = Mock(return_value=mock_client)

            service = QwenVisionService()
            result = await service.extract_from_images(
                [temp_image_file], "Extract contract information"
            )

            assert isinstance(result, QwenVisionResponse)
            assert (
                result.content
                == mock_openai_response["choices"][0]["message"]["content"]
            )
            assert result.usage == mock_openai_response["usage"]
            mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_extract_from_images_with_custom_params(
        self, temp_image_file, mock_openai_response, monkeypatch
    ):
        """Test extraction with custom parameters."""
        monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")

        with patch("src.services.core.qwen_vision_service.httpx") as mock_httpx:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_openai_response
            mock_response.raise_for_status = Mock()

            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()

            mock_httpx.AsyncClient = Mock(return_value=mock_client)

            service = QwenVisionService()
            result = await service.extract_from_images(
                [temp_image_file],
                "Extract",
                temperature=0.2,
                max_tokens=5000,
            )

            assert result is not None
            call_args = mock_client.post.call_args
            payload = call_args[1]["json"]
            assert payload["temperature"] == 0.2
            assert payload["max_tokens"] == 5000

    @pytest.mark.asyncio
    async def test_extract_from_images_not_configured(
        self, temp_image_file, monkeypatch
    ):
        """Test extraction when API key is not configured."""
        monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)

        service = QwenVisionService()

        with pytest.raises(RuntimeError) as exc_info:
            await service.extract_from_images([temp_image_file], "Extract")

        assert "DASHSCOPE_API_KEY not configured" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_extract_from_images_http_error(self, temp_image_file, monkeypatch):
        """Test extraction with HTTP error."""
        monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")

        with patch("src.services.core.qwen_vision_service.httpx") as mock_httpx:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.text = "Not found"

            error = httpx.HTTPStatusError(
                "Not found", request=Mock(), response=mock_response
            )
            mock_client.post = AsyncMock(side_effect=error)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()

            mock_httpx.AsyncClient = Mock(return_value=mock_client)

            service = QwenVisionService()

            with pytest.raises(httpx.HTTPStatusError):
                await service.extract_from_images([temp_image_file], "Extract")

    def test_singleton_getter(self, monkeypatch):
        """Test singleton pattern for service getter."""
        monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")

        service1 = get_qwen_vision_service()
        service2 = get_qwen_vision_service()

        assert service1 is service2


# ============================================================================
# Common Tests Across All Services
# ============================================================================


class TestVisionServiceCommonPatterns:
    """Test common patterns across all vision services."""

    @pytest.mark.parametrize(
        "service_class,env_key,getter_func",
        [
            (ZhipuVisionService, "ZHIPU_API_KEY", get_zhipu_vision_service),
            (DeepSeekVisionService, "DEEPSEEK_API_KEY", get_deepseek_vision_service),
            (HunyuanVisionService, "HUNYUAN_API_KEY", get_hunyuan_vision_service),
            (QwenVisionService, "DASHSCOPE_API_KEY", get_qwen_vision_service),
        ],
    )
    def test_all_services_support_is_available_property(
        self, service_class, env_key, getter_func, monkeypatch
    ):
        """Test all services support is_available property."""
        # Without API key
        monkeypatch.delenv(env_key, raising=False)
        service = service_class()
        # Manually clear API key if it was set from settings
        if service.api_key:
            service.api_key = None
        assert service.is_available is False

        # With API key
        monkeypatch.setenv(env_key, "test-key")
        service_with_key = service_class()
        assert service_with_key.is_available is True

    @pytest.mark.parametrize(
        "service_class,env_key",
        [
            (ZhipuVisionService, "ZHIPU_API_KEY"),
            (DeepSeekVisionService, "DEEPSEEK_API_KEY"),
            (HunyuanVisionService, "HUNYUAN_API_KEY"),
            (QwenVisionService, "DASHSCOPE_API_KEY"),
        ],
    )
    def test_all_services_encode_images_to_base64(
        self, service_class, env_key, temp_image_file, monkeypatch
    ):
        """Test all services can encode images to base64."""
        monkeypatch.setenv(env_key, "test-key")
        service = service_class()

        # Zhipu uses base class method, others have their own
        if hasattr(service, "_encode_image"):
            encoded = service._encode_image(temp_image_file)
            assert isinstance(encoded, str)
            assert len(encoded) > 0

    @pytest.mark.parametrize(
        "service_class,env_key",
        [
            (ZhipuVisionService, "ZHIPU_API_KEY"),
            (DeepSeekVisionService, "DEEPSEEK_API_KEY"),
            (HunyuanVisionService, "HUNYUAN_API_KEY"),
            (QwenVisionService, "DASHSCOPE_API_KEY"),
        ],
    )
    def test_all_services_detect_mime_types(
        self, service_class, env_key, temp_image_file, temp_jpeg_file, monkeypatch
    ):
        """Test all services can detect MIME types."""
        monkeypatch.setenv(env_key, "test-key")
        service = service_class()

        # All services should have MIME type detection
        if hasattr(service, "_get_mime_type"):
            assert service._get_mime_type(temp_image_file) == "image/png"
            assert service._get_mime_type(temp_jpeg_file) == "image/jpeg"

    @pytest.mark.parametrize(
        "service_class,env_key",
        [
            (ZhipuVisionService, "ZHIPU_API_KEY"),
            (DeepSeekVisionService, "DEEPSEEK_API_KEY"),
            (HunyuanVisionService, "HUNYUAN_API_KEY"),
            (QwenVisionService, "DASHSCOPE_API_KEY"),
        ],
    )
    def test_all_services_raise_error_without_api_key(
        self, service_class, env_key, temp_image_file, monkeypatch
    ):
        """Test all services raise RuntimeError when API key not configured."""
        import asyncio

        monkeypatch.delenv(env_key, raising=False)
        service = service_class()
        # Manually clear API key if it was set from settings
        if service.api_key:
            service.api_key = None

        async def test_extract():
            return await service.extract_from_images([temp_image_file], "Extract")

        with pytest.raises(RuntimeError) as exc_info:
            asyncio.run(test_extract())

        assert "API_KEY not configured" in str(exc_info.value)
