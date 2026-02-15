"""
V2 合同CRUD测试
测试多对多资产关系和V2新功能
"""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.crud.rent_contract import rent_contract
from src.models.rent_contract import (
    ContractType,
    PaymentCycle,
    RentContract,
    RentTerm,
)

# ===================== Fixtures =====================


@pytest.fixture
def sample_contract():
    """示例合同数据"""
    contract = RentContract(
        id="contract_123",
        contract_number="CT2024001",
        contract_type=ContractType.LEASE_DOWNSTREAM,
        ownership_id="ownership_123",
        tenant_name="Test Tenant",
        sign_date=date(2024, 1, 1),
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
        payment_cycle=PaymentCycle.MONTHLY,
        total_deposit=Decimal("5000"),
        contract_status="有效",
    )
    return contract


@pytest.fixture
def sample_assets():
    """示例资产列表"""
    return [
        MagicMock(id="asset_1", asset_name="Asset 1"),
        MagicMock(id="asset_2", asset_name="Asset 2"),
        MagicMock(id="asset_3", asset_name="Asset 3"),
    ]


# ===================== V2 Multi-Asset Relationship Tests =====================
@pytest.mark.asyncio
class TestContractV2MultiAsset:
    """测试V2多对多资产关系"""

    async def test_get_contracts_by_asset_id(self, mock_db, sample_contract):
        """测试通过资产ID筛选合同"""
        mock_items_result = MagicMock()
        mock_items_scalars = MagicMock()
        mock_items_scalars.all.return_value = [sample_contract]
        mock_items_result.scalars.return_value = mock_items_scalars

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1
        mock_db.execute = AsyncMock(side_effect=[mock_items_result, mock_count_result])

        contracts, count = await rent_contract.get_multi_with_filters_async(
            db=mock_db,
            asset_id="asset_1",
            skip=0,
            limit=10,
        )

        assert contracts == [sample_contract]
        assert count == 1
        assert mock_db.execute.await_count == 2
        items_stmt = mock_db.execute.await_args_list[0].args[0]
        count_stmt = mock_db.execute.await_args_list[1].args[0]
        assert "rent_contract_assets" in str(items_stmt)
        assert "rent_contract_assets" in str(count_stmt)

    async def test_get_contracts_without_asset_filter(self, mock_db, sample_contract):
        """测试不带资产筛选的查询"""
        mock_items_result = MagicMock()
        mock_items_scalars = MagicMock()
        mock_items_scalars.all.return_value = [sample_contract]
        mock_items_result.scalars.return_value = mock_items_scalars

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1
        mock_db.execute = AsyncMock(side_effect=[mock_items_result, mock_count_result])

        contracts, count = await rent_contract.get_multi_with_filters_async(
            db=mock_db,
            skip=0,
            limit=10,
        )

        assert contracts == [sample_contract]
        assert count == 1
        items_stmt = mock_db.execute.await_args_list[0].args[0]
        count_stmt = mock_db.execute.await_args_list[1].args[0]
        assert "rent_contract_assets" not in str(items_stmt)
        assert "rent_contract_assets" not in str(count_stmt)

    async def test_contract_with_ownership_join(self, mock_db):
        """测试合同与权属方的关联查询"""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.first.return_value = None
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await rent_contract.get_with_details_async(mock_db, "contract_123")

        assert result is None
        stmt = mock_db.execute.await_args.args[0]
        assert "ownerships" in str(stmt)

    async def test_multi_asset_count_query(self, mock_db):
        """测试带资产筛选的count查询"""
        mock_items_result = MagicMock()
        mock_items_scalars = MagicMock()
        mock_items_scalars.all.return_value = []
        mock_items_result.scalars.return_value = mock_items_scalars

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 5
        mock_db.execute = AsyncMock(side_effect=[mock_items_result, mock_count_result])

        contracts, count = await rent_contract.get_multi_with_filters_async(
            db=mock_db,
            asset_id="asset_1",
            skip=0,
            limit=10,
        )

        assert contracts == []
        assert count == 5
        count_stmt = mock_db.execute.await_args_list[1].args[0]
        assert "rent_contract_assets" in str(count_stmt)


class TestContractAsyncRelations:
    """测试异步查询时关系加载"""

    @pytest.fixture
    def anyio_backend(self):
        return "asyncio"

    @pytest.mark.anyio
    async def test_get_multi_with_filters_async_uses_selectinload(self):
        mock_db = AsyncMock()
        mock_items_result = MagicMock()
        mock_items_scalars = MagicMock()
        mock_items_scalars.all.return_value = []
        mock_items_result.scalars.return_value = mock_items_scalars

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 0

        mock_db.execute = AsyncMock(side_effect=[mock_items_result, mock_count_result])

        from sqlalchemy.orm import selectinload as sa_selectinload

        with patch("src.crud.rent_contract.selectinload", wraps=sa_selectinload) as selectinload_mock:
            await rent_contract.get_multi_with_filters_async(
                db=mock_db,
                skip=0,
                limit=10,
            )

            called_targets = [call.args[0] for call in selectinload_mock.call_args_list]
            assert any(target is RentContract.assets for target in called_targets)
            assert any(target is RentContract.rent_terms for target in called_targets)


# ===================== V2 Contract Type Tests =====================
class TestContractV2Types:
    """测试V2合同类型和字段"""

    def test_contract_type_enum(self):
        """测试合同类型枚举"""
        assert ContractType.LEASE_UPSTREAM == "lease_upstream"
        assert ContractType.LEASE_DOWNSTREAM == "lease_downstream"
        assert ContractType.ENTRUSTED == "entrusted"

    def test_payment_cycle_enum(self):
        """测试付款周期枚举"""
        assert PaymentCycle.MONTHLY == "monthly"
        assert PaymentCycle.QUARTERLY == "quarterly"
        assert PaymentCycle.SEMI_ANNUAL == "semi_annual"
        assert PaymentCycle.ANNUAL == "annual"

    def test_contract_v2_fields(self):
        """测试V2新增字段"""
        contract = RentContract(
            contract_type=ContractType.ENTRUSTED,
            service_fee_rate=Decimal("0.0500"),  # 5%服务费率
            upstream_contract_id="upstream_123",
            tenant_usage="办公用途",
            payment_cycle=PaymentCycle.QUARTERLY,
        )

        assert contract.contract_type == ContractType.ENTRUSTED
        assert contract.service_fee_rate == Decimal("0.0500")
        assert contract.upstream_contract_id == "upstream_123"
        assert contract.tenant_usage == "办公用途"
        assert contract.payment_cycle == PaymentCycle.QUARTERLY


# ===================== V2 Rent Term Tests =====================
class TestRentTermV2:
    """测试V2租金条款"""

    def test_rent_term_creation(self):
        """测试租金条款创建"""
        term = RentTerm(
            contract_id="contract_123",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            monthly_rent=Decimal("10000"),
            management_fee=Decimal("500"),
            other_fees=Decimal("200"),
            total_monthly_amount=Decimal("10700"),
        )

        assert term.monthly_rent == Decimal("10000")
        assert term.management_fee == Decimal("500")
        assert term.other_fees == Decimal("200")
        assert term.total_monthly_amount == Decimal("10700")

    def test_rent_term_stepped_rent(self):
        """测试阶梯租金（多个条款）"""
        terms = [
            RentTerm(
                contract_id="contract_123",
                start_date=date(2024, 1, 1),
                end_date=date(2024, 12, 31),
                monthly_rent=Decimal("10000"),
            ),
            RentTerm(
                contract_id="contract_123",
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
                monthly_rent=Decimal("10500"),  # 5%递增
            ),
            RentTerm(
                contract_id="contract_123",
                start_date=date(2026, 1, 1),
                end_date=date(2026, 12, 31),
                monthly_rent=Decimal("11025"),  # 再递增5%
            ),
        ]

        assert len(terms) == 3
        assert terms[0].monthly_rent == Decimal("10000")
        assert terms[1].monthly_rent == Decimal("10500")
        assert terms[2].monthly_rent == Decimal("11025")


# ===================== V2 Query Builder Integration =====================
class TestQueryBuilderIntegration:
    """测试QueryBuilder集成"""

    @pytest.mark.asyncio
    async def test_query_builder_without_db_session_param(self, mock_db):
        """测试QueryBuilder不使用db_session参数（V2更新）"""
        mock_items_result = MagicMock()
        mock_items_scalars = MagicMock()
        mock_items_scalars.all.return_value = []
        mock_items_result.scalars.return_value = mock_items_scalars

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 0

        mock_db.execute = AsyncMock(side_effect=[mock_items_result, mock_count_result])

        contracts, count = await rent_contract.get_multi_with_filters_async(
            db=mock_db, skip=0, limit=10
        )

        # 验证查询成功执行
        assert contracts == []
        assert count == 0
        assert mock_db.execute.await_count == 2


@pytest.mark.asyncio
class TestPriceCalculationQuery:
    """测试统计单价查询构建"""

    async def test_get_contracts_for_price_calculation_with_enum_filters(self, mock_db):
        """传入枚举时应构建兼容 varchar 的合同类型比较条件"""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_result)

        contracts = await rent_contract.get_contracts_for_price_calculation_async(
            db=mock_db,
            contract_type=ContractType.LEASE_DOWNSTREAM,
            contract_status="ACTIVE",
        )

        assert contracts == []
        assert mock_db.execute.await_count == 1
        stmt = mock_db.execute.await_args.args[0]
        stmt_text = str(stmt)
        assert "CAST(rent_contracts.contract_type AS VARCHAR)" in stmt_text
        assert "rent_contracts.contract_status" in stmt_text


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
