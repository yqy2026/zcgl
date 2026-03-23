"""
权属方财务统计服务单元测试

测试 OwnershipFinancialService 的所有主要方法
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.asset.ownership_financial_service import (
    ContractSummary,
    FinancialSummary,
    OwnershipFinancialResult,
    OwnershipFinancialService,
)

TEST_OWNERSHIP_ID = "ownership_123"
TEST_OWNERSHIP_NAME = "测试权属方"


def _mock_scalar_result(value):
    result = MagicMock()
    result.scalar.return_value = value
    return result


def _set_execute_side_effect(mock_db, values):
    mock_db.execute = AsyncMock(side_effect=[_mock_scalar_result(v) for v in values])


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

    async def test_get_financial_summary_uses_new_contract_group_crud(
        self, service, mock_db
    ):
        """必须改走新 contracts/contract_groups/contract_ledger_entries 聚合路径。"""
        with (
            patch(
                "src.services.asset.ownership_financial_service.contract_group_crud.sum_due_amount_by_ownership_async",
                new=AsyncMock(return_value=10000.0),
            ) as mock_due,
            patch(
                "src.services.asset.ownership_financial_service.contract_group_crud.sum_paid_amount_by_ownership_async",
                new=AsyncMock(return_value=8000.0),
            ) as mock_paid,
            patch(
                "src.services.asset.ownership_financial_service.contract_group_crud.sum_overdue_amount_by_ownership_async",
                new=AsyncMock(return_value=2000.0),
            ) as mock_overdue,
            patch(
                "src.services.asset.ownership_financial_service.contract_group_crud.count_by_ownership_async",
                new=AsyncMock(return_value=10),
            ) as mock_count,
            patch(
                "src.services.asset.ownership_financial_service.contract_group_crud.count_active_by_ownership_async",
                new=AsyncMock(return_value=8),
            ) as mock_active_count,
        ):
            result = await service.get_financial_summary(
                mock_db,
                TEST_OWNERSHIP_ID,
                TEST_OWNERSHIP_NAME,
            )

        assert result.financial_summary.total_due_amount == 10000.0
        assert result.financial_summary.total_paid_amount == 8000.0
        assert result.financial_summary.total_arrears_amount == 2000.0
        assert result.contract_summary.total_contracts == 10
        assert result.contract_summary.active_contracts == 8
        mock_due.assert_awaited_once_with(mock_db, TEST_OWNERSHIP_ID)
        mock_paid.assert_awaited_once_with(mock_db, TEST_OWNERSHIP_ID)
        mock_overdue.assert_awaited_once_with(mock_db, TEST_OWNERSHIP_ID)
        mock_count.assert_awaited_once_with(mock_db, TEST_OWNERSHIP_ID)
        mock_active_count.assert_awaited_once_with(mock_db, TEST_OWNERSHIP_ID)

    async def test_get_financial_summary_success(self, service, mock_db):
        """测试成功获取财务汇总"""
        _set_execute_side_effect(mock_db, [10000.0, 8000.0, 2000.0, 10, 8])

        result = await service.get_financial_summary(
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

    async def test_get_financial_summary_empty_data(self, service, mock_db):
        """测试空数据情况"""
        _set_execute_side_effect(mock_db, [None, None, None, 0, 0])

        result = await service.get_financial_summary(
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

    async def test_get_financial_summary_zero_due_amount(self, service, mock_db):
        """测试应收为零时收款率计算"""
        _set_execute_side_effect(mock_db, [0, 0, 0, 5, 3])

        result = await service.get_financial_summary(
            mock_db,
            TEST_OWNERSHIP_ID,
            TEST_OWNERSHIP_NAME,
        )

        # 应收为零时，收款率应为 0
        assert result.financial_summary.payment_rate == 0.0

    async def test_get_financial_summary_full_payment(self, service, mock_db):
        """测试全额付款情况"""
        _set_execute_side_effect(mock_db, [10000.0, 10000.0, 0.0, 5, 5])

        result = await service.get_financial_summary(
            mock_db,
            TEST_OWNERSHIP_ID,
            TEST_OWNERSHIP_NAME,
        )

        assert result.financial_summary.payment_rate == 100.0
        assert result.financial_summary.total_arrears_amount == 0.0

    async def test_get_financial_summary_partial_payment(self, service, mock_db):
        """测试部分付款情况"""
        _set_execute_side_effect(mock_db, [20000.0, 15000.0, 5000.0, 3, 2])

        result = await service.get_financial_summary(
            mock_db,
            TEST_OWNERSHIP_ID,
            TEST_OWNERSHIP_NAME,
        )

        # 15000 / 20000 * 100 = 75%
        assert result.financial_summary.payment_rate == 75.0

    async def test_get_financial_summary_no_active_contracts(self, service, mock_db):
        """测试无活跃合同情况"""
        _set_execute_side_effect(mock_db, [5000.0, 5000.0, 0.0, 10, 0])

        result = await service.get_financial_summary(
            mock_db,
            TEST_OWNERSHIP_ID,
            TEST_OWNERSHIP_NAME,
        )

        assert result.contract_summary.total_contracts == 10
        assert result.contract_summary.active_contracts == 0

    async def test_get_financial_summary_large_amounts(self, service, mock_db):
        """测试大金额情况"""
        large_due = 999999999.99
        large_paid = 888888888.88

        _set_execute_side_effect(
            mock_db, [large_due, large_paid, large_due - large_paid, 100, 95]
        )

        result = await service.get_financial_summary(
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

    async def test_empty_ownership_name(self, service, mock_db):
        """测试空权属方名称"""
        _set_execute_side_effect(mock_db, [0, 0, 0, 0, 0])

        result = await service.get_financial_summary(
            mock_db,
            TEST_OWNERSHIP_ID,
            "",  # 空名称
        )

        assert result.ownership_name == ""

    async def test_special_characters_in_ownership_name(self, service, mock_db):
        """测试权属方名称包含特殊字符"""
        _set_execute_side_effect(mock_db, [0, 0, 0, 0, 0])

        special_name = "测试公司（中国）有限公司 & Partners"
        result = await service.get_financial_summary(
            mock_db,
            TEST_OWNERSHIP_ID,
            special_name,
        )

        assert result.ownership_name == special_name
