#!/usr/bin/env python3
"""
测试 ExtractionResult 验证器的边缘案例
验证 Pydantic 模型验证器的状态一致性检查
"""

import pytest
from pydantic import ValidationError

from src.services.document.base import ExtractionResult, ExtractionStatus


class TestExtractionResultValidator:
    """测试 ExtractionResult 验证器边缘案例"""

    def test_success_true_with_error_message_raises_error(self):
        """测试 success=True 但有 error 消息时抛出验证错误"""

        with pytest.raises(ValidationError) as exc_info:
            ExtractionResult(
                success=True,
                status=ExtractionStatus.SUCCESS,
                error="Some error occurred",  # 不应该有错误
                extracted_fields={"contract_number": "CT001"},
            )

        # 验证错误消息包含冲突信息（中文错误消息）
        assert "success=True 时 error 必须为 None" in str(exc_info.value)

    def test_success_false_without_error_raises_error(self):
        """测试 success=False 但没有 error 消息时抛出验证错误"""

        with pytest.raises(ValidationError) as exc_info:
            ExtractionResult(
                success=False,
                status=ExtractionStatus.FAILED,
                error=None,  # 应该有错误消息
                extracted_fields={},
            )

        assert "success=False 时必须提供 error" in str(exc_info.value)

    def test_success_false_with_success_status_auto_corrects(self):
        """测试 success=False 但 status=SUCCESS 时自动修正为 FAILED"""

        result = ExtractionResult(
            success=False,
            status=ExtractionStatus.SUCCESS,  # 不一致的状态
            error="Extraction failed",
            extracted_fields={},
        )

        # 验证状态被自动修正
        assert result.status == ExtractionStatus.FAILED
        assert result.success is False
        assert result.error == "Extraction failed"

    def test_partial_success_with_error_message(self):
        """测试部分成功场景（有数据但也有错误）"""

        # PARTIAL 状态不会被自动修正，只有 SUCCESS 状态会被修正为 FAILED
        result = ExtractionResult(
            success=False,
            status=ExtractionStatus.PARTIAL,
            error="Some fields failed to extract",
            extracted_fields={"contract_number": "CT001"},  # 部分数据提取成功
        )

        # 验证部分状态保持不变（只有 SUCCESS 会被自动修正为 FAILED）
        assert result.status == ExtractionStatus.PARTIAL
        assert result.success is False
        assert result.error == "Some fields failed to extract"
        assert result.extracted_fields["contract_number"] == "CT001"

    def test_success_true_with_empty_fields_but_skipped_status(self):
        """测试 success=True 且 status=SKIPPED 时允许空字段"""

        result = ExtractionResult(
            success=True,
            status=ExtractionStatus.SKIPPED,
            error=None,
            extracted_fields={},  # 空字段但被跳过
        )

        # 验证跳过状态下允许空字段
        assert result.success is True
        assert result.status == ExtractionStatus.SKIPPED
        assert result.extracted_fields == {}

    def test_success_true_with_empty_fields_in_success_status(self):
        """测试 success=True 且 status=SUCCESS 但字段为空（应抛出验证错误）"""

        with pytest.raises(ValidationError) as exc_info:
            ExtractionResult(
                success=True,
                status=ExtractionStatus.SUCCESS,
                error=None,
                extracted_fields={},  # 空字段
            )

        assert "success=True 时 extracted_fields 不能为空" in str(exc_info.value)

    def test_valid_success_case(self):
        """测试有效的成功案例"""

        result = ExtractionResult(
            success=True,
            status=ExtractionStatus.SUCCESS,
            error=None,
            extracted_fields={
                "contract_number": "CT001",
                "tenant_name": "Test Tenant",
                "start_date": "2024-01-01",
            },
        )

        assert result.success is True
        assert result.status == ExtractionStatus.SUCCESS
        assert result.error is None
        assert len(result.extracted_fields) == 3

    def test_valid_failure_case(self):
        """测试有效的失败案例"""

        result = ExtractionResult(
            success=False,
            status=ExtractionStatus.FAILED,
            error="Vision failed to process PDF",
            extracted_fields={},
        )

        assert result.success is False
        assert result.status == ExtractionStatus.FAILED
        assert result.error == "Vision failed to process PDF"
        assert result.extracted_fields == {}

    def test_skipped_status_allowed(self):
        """测试 SKIPPED 状态的有效性"""

        # SKIPPED 状态应该是成功状态（文件被跳过，不是错误）
        result = ExtractionResult(
            success=True,
            status=ExtractionStatus.SKIPPED,
            error=None,
            extracted_fields={},
        )

        # 跳过状态允许空字段
        assert result.status == ExtractionStatus.SKIPPED
        assert result.success is True
        assert result.error is None
        assert result.extracted_fields == {}

    def test_confidence_validation(self):
        """测试置信度分数的边界值"""

        # 有效的置信度分数
        result = ExtractionResult(
            success=True,
            status=ExtractionStatus.SUCCESS,
            error=None,
            extracted_fields={"test": "data"},
            confidence=0.85,
        )
        assert result.confidence == 0.85

        # 边界值：0
        result_min = ExtractionResult(
            success=True,
            status=ExtractionStatus.SUCCESS,
            error=None,
            extracted_fields={"test": "data"},
            confidence=0.0,
        )
        assert result_min.confidence == 0.0

        # 边界值：1
        result_max = ExtractionResult(
            success=True,
            status=ExtractionStatus.SUCCESS,
            error=None,
            extracted_fields={"test": "data"},
            confidence=1.0,
        )
        assert result_max.confidence == 1.0

    def test_extraction_metadata_preservation(self):
        """测试提取元数据的保留"""

        # ExtractionResult 使用具体字段而不是通用 metadata 字段
        result = ExtractionResult(
            success=True,
            status=ExtractionStatus.SUCCESS,
            error=None,
            extracted_fields={"contract_number": "CT001"},
            pdf_analysis={"page_count": 5, "has_images": True},
            usage={"tokens": 1000, "cost": 0.01},
            processing_time_ms=5200,
        )

        assert result.pdf_analysis == {"page_count": 5, "has_images": True}
        assert result.usage == {"tokens": 1000, "cost": 0.01}
        assert result.processing_time_ms == 5200
