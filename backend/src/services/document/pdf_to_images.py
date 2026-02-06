"""
PDF to images utility.

Uses PyMuPDF if available, otherwise falls back to pdf2image.
"""

from __future__ import annotations

import logging
import tempfile
import uuid
from pathlib import Path

import anyio

logger = logging.getLogger(__name__)

try:  # pragma: no cover - optional dependency
    import fitz  # PyMuPDF

    PYMUPDF_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    fitz = None
    PYMUPDF_AVAILABLE = False

try:  # pragma: no cover - optional dependency
    from pdf2image import convert_from_path

    PDF2IMAGE_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    convert_from_path = None
    PDF2IMAGE_AVAILABLE = False


def _ensure_output_dir() -> Path:
    base_dir = Path(tempfile.gettempdir()) / f"zcgl_pdf_images_{uuid.uuid4().hex}"
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir


def pdf_to_images(
    pdf_path: str,
    *,
    dpi: int = 200,
    max_pages: int = 10,
) -> list[str]:
    """Convert PDF pages to image files and return file paths."""
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    output_dir = _ensure_output_dir()

    if PYMUPDF_AVAILABLE and fitz is not None:
        images: list[str] = []
        zoom = dpi / 72
        matrix = fitz.Matrix(zoom, zoom)
        with fitz.open(str(path)) as doc:
            page_count = min(len(doc), max_pages)
            for page_index in range(page_count):
                page = doc[page_index]
                pix = page.get_pixmap(matrix=matrix)
                image_path = output_dir / f"page_{page_index + 1}.png"
                pix.save(str(image_path))
                images.append(str(image_path))
        return images

    if PDF2IMAGE_AVAILABLE and convert_from_path is not None:
        images = []
        pil_images = convert_from_path(
            str(path),
            dpi=dpi,
            first_page=1,
            last_page=max_pages,
        )
        for idx, image in enumerate(pil_images, start=1):
            image_path = output_dir / f"page_{idx}.png"
            image.save(str(image_path), format="PNG")
            images.append(str(image_path))
        return images

    raise RuntimeError(
        "No PDF rendering backend available. Install pymupdf or pdf2image."
    )


async def pdf_to_images_async(
    pdf_path: str,
    *,
    dpi: int = 200,
    max_pages: int = 10,
) -> list[str]:
    """Async wrapper to avoid blocking the event loop."""
    return await anyio.to_thread.run_sync(
        pdf_to_images,
        pdf_path,
        dpi=dpi,
        max_pages=max_pages,
    )


def cleanup_temp_images(image_paths: list[str]) -> None:
    """Remove temporary images and parent directory if empty."""
    if not image_paths:
        return
    for image_path in image_paths:
        try:
            Path(image_path).unlink(missing_ok=True)
        except Exception as exc:  # pragma: no cover - best effort
            logger.warning("Failed to remove temp image %s: %s", image_path, exc)

    parent = Path(image_paths[0]).parent
    try:
        parent.rmdir()
    except Exception:  # pragma: no cover - best effort
        pass
