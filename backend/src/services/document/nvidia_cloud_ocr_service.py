#!/usr/bin/env python3
"""
NVIDIA Cloud PaddleOCR Service [DEPRECATED]

Cloud-based OCR service using NVIDIA NIM PaddleOCR API.
Provides remote OCR capabilities for PDF/image text extraction.

⚠️ DEPRECATED (2026-01):
    本模块已被标记为废弃。推荐使用 LLM Vision 提取方案：
    - Qwen3-VL-Flash (推荐): services/core/qwen_vision_service.py
    - DeepSeek-OCR: services/core/deepseek_vision_service.py

    使用 extractors/factory.py 进行统一调用。
"""

import base64
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)


@dataclass
class NvidiaOCRConfig:
    """NVIDIA OCR API configuration."""

    api_key: str
    base_url: str = "https://ai.api.nvidia.com/v1/cv/baidu/paddleocr"
    timeout: int = 60
    max_retries: int = 3


@dataclass
class TextDetection:
    """Single text detection result."""

    text: str
    confidence: float
    bounding_box: list[dict[str, float]] = field(default_factory=list)


@dataclass
class OCRResult:
    """OCR processing result."""

    success: bool
    text_detections: list[TextDetection] = field(default_factory=list)
    full_text: str = ""
    confidence_score: float = 0.0
    error: str | None = None
    processing_time_ms: float = 0.0


class NvidiaCloudOCRService:
    """
    NVIDIA Cloud PaddleOCR Service.

    Provides OCR capabilities through NVIDIA NIM API.
    Supports image and PDF (via page rendering) processing.
    """

    def __init__(self, config: NvidiaOCRConfig | None = None):
        """
        Initialize the NVIDIA Cloud OCR service.

        Args:
            config: OCR configuration, uses environment if not provided.
        """
        if config is None:
            config = self._load_config_from_env()

        self.config = config
        self._client: httpx.AsyncClient | None = None

        logger.info(
            f"NvidiaCloudOCRService initialized with base_url={self.config.base_url}"
        )

    def _load_config_from_env(self) -> NvidiaOCRConfig:
        """Load configuration from environment variables."""
        import os

        api_key = os.getenv("NVIDIA_API_KEY", "")
        base_url = os.getenv(
            "NVIDIA_OCR_BASE_URL",
            "https://ai.api.nvidia.com/v1/cv/baidu/paddleocr",
        )
        timeout = int(os.getenv("NVIDIA_OCR_TIMEOUT", "60"))

        if not api_key:
            logger.warning("NVIDIA_API_KEY not set in environment")

        return NvidiaOCRConfig(api_key=api_key, base_url=base_url, timeout=timeout)

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.timeout),
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def is_available(self) -> bool:
        """Check if the service is configured and available."""
        return bool(self.config.api_key)

    async def health_check(self) -> bool:
        """
        Check NVIDIA API connectivity.

        Returns:
            True if API is accessible, False otherwise.
        """
        if not self.is_available():
            return False

        try:
            client = await self._get_client()
            # Use a minimal test image (1x1 white pixel PNG)
            test_image = (
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42"
                "mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
            )
            payload = {
                "input": [
                    {"type": "image_url", "url": f"data:image/png;base64,{test_image}"}
                ]
            }

            response = await client.post(self.config.base_url, json=payload)
            return response.status_code in (200, 400)  # 400 is expected for tiny image

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    def _encode_image_to_base64(
        self, image_bytes: bytes, image_format: str = "png"
    ) -> str:
        """
        Encode image bytes to base64 data URL.

        Args:
            image_bytes: Raw image bytes.
            image_format: Image format (png or jpeg).

        Returns:
            Base64 data URL string.
        """
        b64_data = base64.b64encode(image_bytes).decode("utf-8")
        return f"data:image/{image_format};base64,{b64_data}"

    async def process_image(
        self, image_bytes: bytes, image_format: str = "png"
    ) -> OCRResult:
        """
        Process a single image through OCR.

        Args:
            image_bytes: Raw image bytes.
            image_format: Image format (png or jpeg).

        Returns:
            OCRResult with text detections.
        """
        import time

        start_time = time.time()

        if not self.is_available():
            return OCRResult(
                success=False,
                error="NVIDIA API key not configured. Set NVIDIA_API_KEY environment variable.",
            )

        try:
            client = await self._get_client()

            # Encode image to base64 data URL
            image_data_url = self._encode_image_to_base64(image_bytes, image_format)

            # Prepare API payload
            payload = {"input": [{"type": "image_url", "url": image_data_url}]}

            logger.debug(f"Sending OCR request to {self.config.base_url}")

            response = await client.post(self.config.base_url, json=payload)
            response.raise_for_status()

            result_data = response.json()
            processing_time = (time.time() - start_time) * 1000

            return self._parse_response(result_data, processing_time)

        except httpx.HTTPStatusError as e:
            logger.error(
                f"NVIDIA API HTTP error: {e.response.status_code} - {e.response.text}"
            )
            return OCRResult(
                success=False,
                error=f"API error: {e.response.status_code}",
                processing_time_ms=(time.time() - start_time) * 1000,
            )
        except httpx.RequestError as e:
            logger.error(f"NVIDIA API request error: {e}")
            return OCRResult(
                success=False,
                error=f"Request failed: {str(e)}",
                processing_time_ms=(time.time() - start_time) * 1000,
            )
        except Exception as e:
            logger.error(f"OCR processing error: {e}")
            return OCRResult(
                success=False,
                error=f"Processing error: {str(e)}",
                processing_time_ms=(time.time() - start_time) * 1000,
            )

    def _parse_response(
        self, response_data: dict[str, Any], processing_time_ms: float
    ) -> OCRResult:
        """
        Parse NVIDIA API response into OCRResult.

        Args:
            response_data: Raw API response.
            processing_time_ms: Processing time in milliseconds.

        Returns:
            Parsed OCRResult.
        """
        text_detections = []
        all_texts = []
        total_confidence = 0.0

        try:
            data = response_data.get("data", [])

            for item in data:
                for detection in item.get("text_detections", []):
                    text_pred = detection.get("text_prediction", {})
                    text = text_pred.get("text", "")
                    confidence = text_pred.get("confidence", 0.0)

                    if text:
                        bbox = detection.get("bounding_box", {}).get("points", [])

                        text_detections.append(
                            TextDetection(
                                text=text,
                                confidence=confidence,
                                bounding_box=bbox,
                            )
                        )
                        all_texts.append(text)
                        total_confidence += confidence

            # Calculate average confidence
            avg_confidence = (
                total_confidence / len(text_detections) if text_detections else 0.0
            )

            # Sort by vertical position (y-coordinate) then horizontal (x-coordinate)
            text_detections.sort(
                key=lambda d: (
                    min(p.get("y", 0) for p in d.bounding_box) if d.bounding_box else 0,
                    min(p.get("x", 0) for p in d.bounding_box) if d.bounding_box else 0,
                )
            )

            # Reconstruct full text in reading order
            full_text = " ".join(d.text for d in text_detections)

            return OCRResult(
                success=True,
                text_detections=text_detections,
                full_text=full_text,
                confidence_score=avg_confidence,
                processing_time_ms=processing_time_ms,
            )

        except Exception as e:
            logger.error(f"Error parsing OCR response: {e}")
            return OCRResult(
                success=False,
                error=f"Response parsing error: {str(e)}",
                processing_time_ms=processing_time_ms,
            )

    async def process_pdf(
        self,
        pdf_path: str,
        max_pages: int = 10,
        dpi: int = 200,
    ) -> dict[str, Any]:
        """
        Process a PDF file through OCR.

        Converts PDF pages to images and processes each through OCR.

        Args:
            pdf_path: Path to the PDF file.
            max_pages: Maximum number of pages to process.
            dpi: Resolution for PDF to image conversion.

        Returns:
            Dictionary with OCR results for each page and combined text.
        """
        import time

        start_time = time.time()

        if not Path(pdf_path).exists():
            return {
                "success": False,
                "error": f"PDF file not found: {pdf_path}",
                "pages": [],
                "full_text": "",
            }

        try:
            # Import pymupdf for PDF processing
            import fitz  # PyMuPDF

            doc = fitz.open(pdf_path)
            total_pages = min(len(doc), max_pages)

            logger.info(f"Processing {total_pages} pages from PDF: {pdf_path}")

            page_results = []
            all_texts = []

            for page_num in range(total_pages):
                page = doc[page_num]

                # Render page to image
                mat = fitz.Matrix(dpi / 72, dpi / 72)
                pix = page.get_pixmap(matrix=mat)

                # Convert to PNG bytes
                image_bytes = pix.tobytes("png")

                # Process through OCR
                ocr_result = await self.process_image(image_bytes, "png")

                page_results.append(
                    {
                        "page": page_num + 1,
                        "success": ocr_result.success,
                        "text": ocr_result.full_text,
                        "confidence": ocr_result.confidence_score,
                        "detections_count": len(ocr_result.text_detections),
                        "error": ocr_result.error,
                    }
                )

                if ocr_result.success:
                    all_texts.append(ocr_result.full_text)

                logger.debug(
                    f"Page {page_num + 1}/{total_pages} processed: "
                    f"{len(ocr_result.text_detections)} detections"
                )

            doc.close()

            processing_time = (time.time() - start_time) * 1000

            return {
                "success": True,
                "pages": page_results,
                "full_text": "\n\n".join(all_texts),
                "total_pages": total_pages,
                "processing_time_ms": processing_time,
                "extraction_method": "nvidia_cloud_paddleocr",
            }

        except ImportError:
            return {
                "success": False,
                "error": "PyMuPDF (fitz) not installed. Required for PDF processing.",
                "pages": [],
                "full_text": "",
            }
        except Exception as e:
            logger.error(f"PDF processing error: {e}")
            return {
                "success": False,
                "error": f"PDF processing error: {str(e)}",
                "pages": [],
                "full_text": "",
            }

    async def extract_contract_text(self, pdf_path: str) -> dict[str, Any]:
        """
        Extract text from a contract PDF for further processing.

        This is a convenience method that processes the PDF and returns
        the combined text suitable for contract field extraction.

        Args:
            pdf_path: Path to the contract PDF.

        Returns:
            Dictionary with extracted text and metadata.
        """
        result = await self.process_pdf(pdf_path)

        if not result.get("success"):
            return result

        return {
            "success": True,
            "text": result.get("full_text", ""),
            "markdown": result.get("full_text", ""),  # For compatibility
            "confidence_score": sum(
                p.get("confidence", 0) for p in result.get("pages", [])
            )
            / max(len(result.get("pages", [])), 1),
            "total_pages": result.get("total_pages", 0),
            "processing_time_ms": result.get("processing_time_ms", 0),
            "extraction_method": "nvidia_cloud_paddleocr",
        }


# Module-level singleton
_nvidia_ocr_service: NvidiaCloudOCRService | None = None


def get_nvidia_ocr_service(
    config: NvidiaOCRConfig | None = None,
) -> NvidiaCloudOCRService:
    """
    Get NVIDIA OCR service singleton.

    Args:
        config: Optional configuration override.

    Returns:
        NvidiaCloudOCRService instance.
    """
    global _nvidia_ocr_service

    if _nvidia_ocr_service is None:
        _nvidia_ocr_service = NvidiaCloudOCRService(config)

    return _nvidia_ocr_service


async def extract_text_from_image(image_bytes: bytes) -> OCRResult:
    """
    Convenience function to extract text from an image.

    Args:
        image_bytes: Raw image bytes.

    Returns:
        OCRResult with extracted text.
    """
    service = get_nvidia_ocr_service()
    return await service.process_image(image_bytes)


async def extract_text_from_pdf(pdf_path: str) -> dict[str, Any]:
    """
    Convenience function to extract text from a PDF.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        Dictionary with extracted text and metadata.
    """
    service = get_nvidia_ocr_service()
    return await service.extract_contract_text(pdf_path)
