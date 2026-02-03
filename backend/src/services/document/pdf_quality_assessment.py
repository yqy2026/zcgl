"""
PDF quality assessment.

Provides lightweight heuristics for PDF readability and extraction suitability.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .pdf_analyzer import analyze_pdf


class PDFQualityAssessment:
    """Assess PDF quality for extraction workflows."""

    def assess(self, pdf_path: str | Path) -> dict[str, Any]:
        analysis = analyze_pdf(pdf_path)

        # Simple heuristic: favor text-based PDFs
        text_ratio = float(analysis.get("text_ratio", 0))
        has_images = bool(analysis.get("has_images", False))

        if text_ratio >= 0.6 and not has_images:
            quality_score = 0.9
        elif text_ratio >= 0.3:
            quality_score = 0.7
        else:
            quality_score = 0.4

        return {
            "success": True,
            "quality_score": round(quality_score, 2),
            "analysis": analysis,
        }
