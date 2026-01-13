"""
阿里通义千问 Qwen-VL 多模态视觉服务
Alibaba Qwen-VL Multimodal Vision Service

支持图片直接输入进行合同信息提取
Supports direct image input for contract information extraction

DashScope API Documentation:
https://help.aliyun.com/zh/model-studio/developer-reference/qwen-vl-api
"""

import base64
import logging
import os
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class QwenVisionResponse(BaseModel):
    """Response from Qwen vision model"""

    content: str
    raw_response: Any
    usage: dict[str, Any] = {}


class QwenVisionService:
    """
    阿里通义千问 Qwen-VL 多模态视觉服务

    Environment Variables:
    - DASHSCOPE_API_KEY: 阿里云 DashScope API密钥 (required)
    - QWEN_VISION_MODEL: 视觉模型 (default: qwen3-vl-flash)
    - QWEN_TIMEOUT: API timeout in seconds (default: 120)

    Available Models (2026.01 最新):
    - qwen3-vl-flash: 性价比最高 $0.05/M输入 (推荐)
    - qwen-vl-max: 最强视觉理解 $0.23/M输入
    - qwen-vl-plus: 平衡性价比 $0.08/M输入
    """

    DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    def __init__(self) -> None:
        # 优先使用 centralized config，fallback 到环境变量
        try:
            from src.core.config import settings

            self.api_key = settings.DASHSCOPE_API_KEY or os.getenv("DASHSCOPE_API_KEY")
            self.base_url = settings.DASHSCOPE_BASE_URL or os.getenv(
                "DASHSCOPE_BASE_URL", self.DEFAULT_BASE_URL
            )
            self.model = settings.QWEN_VISION_MODEL or os.getenv(
                "QWEN_VISION_MODEL", "qwen3-vl-flash"
            )
        except ImportError:
            # Fallback for standalone usage
            self.api_key = os.getenv("DASHSCOPE_API_KEY")
            self.base_url = os.getenv("DASHSCOPE_BASE_URL", self.DEFAULT_BASE_URL)
            self.model = os.getenv("QWEN_VISION_MODEL", "qwen3-vl-flash")

        self.timeout = int(os.getenv("QWEN_TIMEOUT", "120"))

        if not self.api_key:
            logger.warning(
                "DASHSCOPE_API_KEY not set, Qwen vision service will be disabled"
            )
        else:
            logger.info(f"QwenVisionService initialized with model: {self.model}")

    @property
    def is_available(self) -> bool:
        """Check if service is configured and available"""
        return bool(self.api_key)

    def _encode_image(self, image_path: str) -> str:
        """Encode image file to base64 string"""
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def _get_mime_type(self, image_path: str) -> str:
        """Get MIME type from file extension"""
        ext = Path(image_path).suffix.lower()
        mime_map = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        return mime_map.get(ext, "image/png")

    async def extract_from_images(
        self,
        image_paths: list[str],
        prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> QwenVisionResponse:
        """
        Send images to Qwen-VL for contract extraction.

        Args:
            image_paths: List of image file paths (PNG/JPG)
            prompt: Extraction prompt (Chinese preferred)
            temperature: Model temperature (0.0-1.0)
            max_tokens: Maximum tokens in response

        Returns:
            QwenVisionResponse with extracted content

        Raises:
            RuntimeError: If API key not configured
            httpx.HTTPStatusError: If API request fails
        """
        if not self.is_available:
            raise RuntimeError("DASHSCOPE_API_KEY not configured")

        # Build multimodal content array (OpenAI-compatible format)
        content: list[dict[str, Any]] = []

        for img_path in image_paths:
            img_base64 = self._encode_image(img_path)
            mime_type = self._get_mime_type(img_path)
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime_type};base64,{img_base64}"},
                }
            )

        # Add text prompt
        content.append({"type": "text", "text": prompt})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": content}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        logger.info(f"Sending {len(image_paths)} images to {self.model}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions", json=payload, headers=headers
                )
                response.raise_for_status()
                data = response.json()

                result_content = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})

                logger.info(f"Qwen vision extraction complete. Tokens used: {usage}")

                return QwenVisionResponse(
                    content=result_content, raw_response=data, usage=usage
                )

        except httpx.HTTPStatusError as e:
            logger.error(
                f"DashScope API error: {e.response.status_code} - {e.response.text}"
            )
            raise
        except Exception as e:
            logger.error(f"Qwen vision extraction failed: {e}")
            raise


# Singleton instance
_qwen_vision_service: QwenVisionService | None = None


def get_qwen_vision_service() -> QwenVisionService:
    """Get or create singleton QwenVisionService instance"""
    global _qwen_vision_service
    if _qwen_vision_service is None:
        _qwen_vision_service = QwenVisionService()
    return _qwen_vision_service
