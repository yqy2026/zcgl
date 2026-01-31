"""
权属方财务统计服务单元测试

测试 OwnershipFinancialService 的所有主要方法
"""

from unittest.mock import MagicMock

import pytest

from src.services.asset.ownership_financial_service import (
    ContractSummary,
    FinancialSummary,
    OwnershipFinancialResult,
    OwnershipFinancialService,
)

TEST_OWNERSHIP_ID = "ownership_123"
TEST_OWNERSHIP_NAME = "测试权属方"


@pytest.fixture
def service():
    """创建服务实例"""
    return OwnershipFinancialService()


# ============================================================================
# 数据类测试
# ============================================================================
class TestDataClasses:
    """测试数据类"""

    def test_financial_summary_creation(self):
        """测试 FinancialSummary 创建"""
        summary = FinancialSummary(
            total_due_amount=10000.0,
            total_paid_amount=8000.0,
            total_arrears_amount=2000.0,
            payment_rate=80.0,
        )

        assert summary.total_due_amount == 10000.0
        assert summary.total_paid_amount == 8000.0
        assert summary.total_arrears_amount == 2000.0
        assert summary.payment_rate == 80.0

    def test_contract_summary_creation(self):
        """测试 ContractSummary 创建"""
        summary = ContractSummary(
            total_contracts=10,
            active_contracts=8,
        )

        assert summary.total_contracts == 10
        assert summary.active_contracts == 8

    def test_ownership_financial_result_creation(self):
        """测试 OwnershipFinancialResult 创建"""
        result = OwnershipFinancialResult(
            ownership_id=TEST_OWNERSHIP_ID,
            ownership_name=TEST_OWNERSHIP_NAME,
            financial_summary=FinancialSummary(
                total_due_amount=10000.0,
                total_paid_amount=8000.0,
                total_arrears_amount=2000.0,
                payment_rate=80.0,
            ),
            contract_summary=ContractSummary(
                total_contracts=10,
                active_contracts=8,
            ),
        )

        assert result.ownership_id == TEST_OWNERSHIP_ID
        assert result.ownership_name == TEST_OWNERSHIP_NAME
        assert result.financial_summary.total_due_amount == 10000.0
        assert result.contract_summary.total_contracts == 10

    def test_ownership_financial_result_to_dict(self):
        """测试 OwnershipFinancialResult.to_dict 方法"""
        result = OwnershipFinancialResult(
            ownership_id=TEST_OWNERSHIP_ID,
            ownership_name=TEST_OWNERSHIP_NAME,
            financial_summary=FinancialSummary(
                total_due_amount=10000.0,
                total_paid_amount=8000.0,
                total_arrears_amount=2000.0,
                payment_rate=80.0,
            ),
            contract_summary=ContractSummary(
                total_contracts=10,
                active_contracts=8,
            ),
        )

        result_dict = result.to_dict()

        assert result_dict["ownership_id"] == TEST_OWNERSHIP_ID
        assert result_dict["ownership_name"] == TEST_OWNERSHIP_NAME
        assert result_dict["financial_summary"]["total_due_amount"] == 10000.0
        assert result_dict["financial_summary"]["total_paid_amount"] == 8000.0
        assert result_dict["financial_summary"]["total_arrears_amount"] == 2000.0
        assert result_dict["financial_summary"]["payment_rate"] == 80.0
        assert result_dict["contract_summary"]["total_contracts"] == 10
        assert result_dict["contract_summary"]["active_contracts"] == 8


# ============================================================================
# OwnershipFinancialService.get_financial_summary 测试
# ============================================================================
class TestGetFinancialSummary:
    """测试获取财务汇总"""

    def test_get_financial_summary_success(self, service, mock_db):
        """测试成功获取财务汇总"""
        # Mock 查询结果
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.scalar_subquery.return_value = "subquery"

        # 设置各查询的返回值
        mock_query.scalar.side_effect = [
            10000.0,  # due_amount
            8000.0,  # paid_amount
            2000.0,  # arrears_amount
            10,  # total_contracts
            8,  # active_contracts
        ]

        result = service.get_financial_summary(
            mock_db,
            TEST_OWNERSHIP_ID,
            TEST_OWNERSHIP_NAME,
        )

        assert result.ownership_id == TEST_OWNERSHIP_ID
        assert result.ownership_name == TEST_OWNERSHIP_NAME
        assert result.financial_summary.total_due_amount == 10000.0
        assert result.financial_summary.total_paid_amount == 8000.0
        assert result.financial_summary.total_arrears_amount == 2000.0
        assert result.financial_summary.payment_rate == 80.0
        assert result.contract_summary.total_contracts == 10
        assert result.contract_summary.active_contracts == 8

    def test_get_financial_summary_empty_data(self, service, mock_db):
        """测试空数据情况"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.scalar_subquery.return_value = "subquery"

        # 所有查询返回 None 或 0
        mock_query.scalar.side_effect = [
            None,  # due_amount
            None,  # paid_amount
            None,  # arrears_amount
            0,  # total_contracts
            0,  # active_contracts
        ]

        result = service.get_financial_summary(
            mock_db,
            TEST_OWNERSHIP_ID,
            TEST_OWNERSHIP_NAME,
        )

        assert result.financial_summary.total_due_amount == 0.0
        assert result.financial_summary.total_paid_amount == 0.0
        assert result.financial_summary.total_arrears_amount == 0.0
        assert result.financial_summary.payment_rate == 0.0
        assert result.contract_summary.total_contracts == 0
        assert result.contract_summary.active_contracts == 0

    def test_get_financial_summary_zero_due_amount(self, service, mock_db):
        """测试应收为零时收款率计算"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.scalar_subquery.return_value = "subquery"

        mock_query.scalar.side_effect = [
            0,  # due_amount = 0
            0,  # paid_amount
            0,  # arrears_amount
            5,  # total_contracts
            3,  # active_contracts
        ]

        result = service.get_financial_summary(
            mock_db,
            TEST_OWNERSHIP_ID,
            TEST_OWNERSHIP_NAME,
        )

        # 应收为零时，收款率应为 0
        assert result.financial_summary.payment_rate == 0.0

    def test_get_financial_summary_full_payment(self, service, mock_db):
        """测试全额付款情况"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.scalar_subquery.return_value = "subquery"

        mock_query.scalar.side_effect = [
            10000.0,  # due_amount
            10000.0,  # paid_amount (全额付款)
            0.0,  # arrears_amount
            5,  # total_contracts
            5,  # active_contracts
        ]

        result = service.get_financial_summary(
            mock_db,
            TEST_OWNERSHIP_ID,
            TEST_OWNERSHIP_NAME,
        )

        assert result.financial_summary.payment_rate == 100.0
        assert result.financial_summary.total_arrears_amount == 0.0

    def test_get_financial_summary_partial_payment(self, service, mock_db):
        """测试部分付款情况"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.scalar_subquery.return_value = "subquery"

        mock_query.scalar.side_effect = [
            20000.0,  # due_amount
            15000.0,  # paid_amount
            5000.0,  # arrears_amount
            3,  # total_contracts
            2,  # active_contracts
        ]

        result = service.get_financial_summary(
            mock_db,
            TEST_OWNERSHIP_ID,
            TEST_OWNERSHIP_NAME,
        )

        # 15000 / 20000 * 100 = 75%
        assert result.financial_summary.payment_rate == 75.0

    def test_get_financial_summary_no_active_contracts(self, service, mock_db):
        """测试无活跃合同情况"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.scalar_subquery.return_value = "subquery"

        mock_query.scalar.side_effect = [
            5000.0,  # due_amount
            5000.0,  # paid_amount
            0.0,  # arrears_amount
            10,  # total_contracts
            0,  # active_contracts (无活跃)
        ]

        result = service.get_financial_summary(
            mock_db,
            TEST_OWNERSHIP_ID,
            TEST_OWNERSHIP_NAME,
        )

        assert result.contract_summary.total_contracts == 10
        assert result.contract_summary.active_contracts == 0

    def test_get_financial_summary_large_amounts(self, service, mock_db):
        """测试大金额情况"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.scalar_subquery.return_value = "subquery"

        large_due = 999999999.99
        large_paid = 888888888.88

        mock_query.scalar.side_effect = [
            large_due,
            large_paid,
            large_due - large_paid,
            100,
            95,
        ]

        result = service.get_financial_summary(
            mock_db,
            TEST_OWNERSHIP_ID,
            TEST_OWNERSHIP_NAME,
        )

        assert result.financial_summary.total_due_amount == large_due
        assert result.financial_summary.total_paid_amount == large_paid
        expected_rate = (large_paid / large_due) * 100
        assert abs(result.financial_summary.payment_rate - expected_rate) < 0.01


# ============================================================================
# 边界情况测试
# ============================================================================
class TestEdgeCases:
    """测试边界情况"""

    def test_result_to_dict_preserves_precision(self):
        """测试字典转换保持精度"""
        result = OwnershipFinancialResult(
            ownership_id=TEST_OWNERSHIP_ID,
            ownership_name=TEST_OWNERSHIP_NAME,
            financial_summary=FinancialSummary(
                total_due_amount=12345.67,
                total_paid_amount=9876.54,
                total_arrears_amount=2469.13,
                payment_rate=80.0123,
            ),
            contract_summary=ContractSummary(
                total_contracts=999,
                active_contracts=888,
            ),
        )

        result_dict = result.to_dict()

        assert result_dict["financial_summary"]["total_due_amount"] == 12345.67
        assert result_dict["financial_summary"]["payment_rate"] == 80.0123

    def test_empty_ownership_name(self, service, mock_db):
        """测试空权属方名称"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.scalar_subquery.return_value = "subquery"
        mock_query.scalar.side_effect = [0, 0, 0, 0, 0]

        result = service.get_financial_summary(
            mock_db,
            TEST_OWNERSHIP_ID,
            "",  # 空名称
        )

        assert result.ownership_name == ""

    def test_special_characters_in_ownership_name(self, service, mock_db):
        """测试权属方名称包含特殊字符"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.scalar_subquery.return_value = "subquery"
        mock_query.scalar.side_effect = [0, 0, 0, 0, 0]

        special_name = "测试公司（中国）有限公司 & Partners"
        result = service.get_financial_summary(
            mock_db,
            TEST_OWNERSHIP_ID,
            special_name,
        )

        assert result.ownership_name == special_name
