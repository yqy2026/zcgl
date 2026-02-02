"""
Unit tests for processing_result schemas
"""

import pytest
from pydantic import ValidationError

from src.schemas.processing_result import (
    ProcessingResultEnvelope,
    QualityAssessment,
    QualityMetrics,
)


class TestProcessingResultSchemas:
    def test_quality_assessment_confidence_range(self):
        QualityAssessment(confidence_score=0.0)
        QualityAssessment(confidence_score=1.0)
        with pytest.raises(ValidationError):
            QualityAssessment(confidence_score=1.5)

    def test_processing_result_defaults(self):
        result = ProcessingResultEnvelope()
        assert result.is_success is True
        assert result.extra == {}

    def test_processing_result_extra_is_isolated(self):
        first = ProcessingResultEnvelope()
        second = ProcessingResultEnvelope()
        first.extra["key"] = "value"
        assert "key" not in second.extra

    def test_processing_result_nested_models(self):
        assessment = QualityAssessment(overall_quality="high", confidence_score=0.9)
        metrics = QualityMetrics(concurrency_used=2, pages_per_second=3.5)
        result = ProcessingResultEnvelope(
            text="ok",
            total_pages=2,
            quality_assessment=assessment,
            metrics=metrics,
        )
        assert result.metrics.pages_per_second == 3.5
        assert result.quality_assessment.overall_quality == "high"
