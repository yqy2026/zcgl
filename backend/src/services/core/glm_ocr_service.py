"""
GLM-OCR layout parsing service.

Uses Zhipu GLM-OCR layout_parsing endpoint to extract markdown text
and layout metadata from PDF/image files.
"""

from __future__ import annotations

import base64
import logging
import os
from pathlib import Path
from typing import Any

import httpx
from httpx import HTTPStatusError, NetworkError, TimeoutException

from ...core.exception_handler import ConfigurationError
from .base_vision_service import (
    VisionAPIError,
    handle_http_status_error,
    handle_network_error,
)

logger = logging.getLogger(__name__)


class GLMOCRService:
    """GLM-OCR layout parsing service."""

    DEFAULT_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
    DEFAULT_MODEL = "glm-ocr"

    def __init__(self) -> None:
        try:
            from src.core.config import settings

            self.api_key = settings.GLM_OCR_API_KEY or os.getenv("GLM_OCR_API_KEY")
            self.base_url = (
                settings.GLM_OCR_BASE_URL
                or os.getenv("GLM_OCR_BASE_URL", self.DEFAULT_BASE_URL)
            )
            self.model = settings.GLM_OCR_MODEL or os.getenv(
                "GLM_OCR_MODEL", self.DEFAULT_MODEL
            )
            timeout_from_env = os.getenv("GLM_OCR_TIMEOUT")
            timeout_from_settings = settings.GLM_OCR_TIMEOUT
            self.timeout = (
                int(timeout_from_env)
                if timeout_from_env is not None
                else int(timeout_from_settings or 120)
            )
            self.enabled = bool(settings.GLM_OCR_ENABLE)
        except Exception:
            self.api_key = os.getenv("GLM_OCR_API_KEY")
            self.base_url = os.getenv("GLM_OCR_BASE_URL", self.DEFAULT_BASE_URL)
            self.model = os.getenv("GLM_OCR_MODEL", self.DEFAULT_MODEL)
            self.timeout = int(os.getenv("GLM_OCR_TIMEOUT", "120"))
            self.enabled = os.getenv("GLM_OCR_ENABLE", "false").lower() in {
                "1",
                "true",
                "yes",
            }

        self.base_url = self.base_url.rstrip("/")

        if not self.api_key:
            logger.warning("GLM_OCR_API_KEY not set, GLM-OCR service disabled")
        else:
            logger.info("GLM-OCR service initialized with model: %s", self.model)

    @property
    def is_available(self) -> bool:
        return bool(self.api_key) and self.enabled

    def _encode_file(self, file_path: str | Path) -> str:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        if not path.is_file():
            raise ValueError(f"Path is not a file: {path}")
        with open(path, "rb") as handle:
            return base64.b64encode(handle.read()).decode("utf-8")

    def _get_mime_type(self, file_path: str | Path) -> str:
        suffix = Path(file_path).suffix.lower()
        if suffix == ".pdf":
            return "application/pdf"
        if suffix in {".jpg", ".jpeg"}:
            return "image/jpeg"
        if suffix == ".png":
            return "image/png"
        return "application/octet-stream"

    def _resolve_file_payload(self, file_path: str | None) -> str:
        if not file_path:
            raise ValueError("file_path is required")
        if file_path.startswith("http://") or file_path.startswith("https://"):
            return file_path
        encoded = self._encode_file(file_path)
        mime = self._get_mime_type(file_path)
        return f"data:{mime};base64,{encoded}"

    async def layout_parsing(
        self,
        *,
        file_path: str | None,
        start_page_id: int | None = None,
        end_page_id: int | None = None,
        return_crop_images: bool | None = None,
        need_layout_visualization: bool | None = None,
        request_id: str | None = None,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        if not self.is_available:
            raise ConfigurationError(
                "GLM_OCR_API_KEY not configured or GLM_OCR_ENABLE=false",
                config_key="GLM_OCR_API_KEY",
            )

        payload: dict[str, Any] = {
            "model": self.model,
            "file": self._resolve_file_payload(file_path),
        }
        if start_page_id is not None:
            payload["start_page_id"] = start_page_id
        if end_page_id is not None:
            payload["end_page_id"] = end_page_id
        if return_crop_images is not None:
            payload["return_crop_images"] = return_crop_images
        if need_layout_visualization is not None:
            payload["need_layout_visualization"] = need_layout_visualization
        if request_id:
            payload["request_id"] = request_id
        if user_id:
            payload["user_id"] = user_id

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/layout_parsing",
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()

            return {
                "success": True,
                "id": data.get("id"),
                "created": data.get("created"),
                "model": data.get("model", self.model),
                "md_results": data.get("md_results"),
                "layout_details": data.get("layout_details"),
                "layout_visualization": data.get("layout_visualization"),
                "data_info": data.get("data_info"),
                "usage": data.get("usage"),
                "request_id": data.get("request_id"),
                "raw_response": data,
            }
        except HTTPStatusError as exc:
            error = handle_http_status_error(exc)
            logger.error("GLM-OCR API error: %s", error, exc_info=True)
            raise error from exc
        except (NetworkError, TimeoutException, ConnectionError) as exc:
            error = handle_network_error(exc)
            logger.error("GLM-OCR network error: %s", error, exc_info=True)
            raise error from exc
        except VisionAPIError:
            raise
        except Exception as exc:
            logger.error("GLM-OCR request failed: %s", exc, exc_info=True)
            raise VisionAPIError(
                message=f"Unexpected GLM-OCR error: {exc}",
                status_code=None,
                retryable=False,
            ) from exc


_glm_ocr_service: GLMOCRService | None = None


def get_glm_ocr_service() -> GLMOCRService:
    global _glm_ocr_service
    if _glm_ocr_service is None:
        _glm_ocr_service = GLMOCRService()
    return _glm_ocr_service
