"""
测试 AnalyticsService (综合分析服务)
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.contract_group import (
    ContractLifecycleStatus,
    GroupRelationType,
    RevenueMode,
)
from src.models.party import PartyReviewStatus
from src.services.analytics.analytics_service import AnalyticsService


@pytest.fixture
def analytics_service(mock_db):
    """创建 AnalyticsService 实例"""
    return AnalyticsService(mock_db)


class TestAnalyticsService:
    """测试 AnalyticsService 类"""

    def test_init(self, mock_db):
        """测试服务初始化"""
        service = AnalyticsService(mock_db)
        assert service.db == mock_db
        assert service.cache is not None
        assert service.response_handler is not None

    def test_validate_filters_empty(self, analytics_service):
        """测试空筛选条件验证"""
        result = analytics_service._validate_filters({})
        assert result == {}

    def test_validate_filters_with_include_deleted(self, analytics_service):
        """测试包含 include_deleted 的筛选条件"""
        result = analytics_service._validate_filters({"include_deleted": True})
        assert result["include_deleted"] is True

    def test_validate_filters_with_dates(self, analytics_service):
        """测试包含日期的筛选条件"""
        filters = {
            "include_deleted": False,
            "date_from": "2024-01-01",
            "date_to": "2024-12-31",
        }
        result = analytics_service._validate_filters(filters)
        assert result["include_deleted"] is False
        assert result["date_from"] == "2024-01-01"
        assert result["date_to"] == "2024-12-31"

    def test_generate_cache_key(self, analytics_service):
        """测试缓存键生成"""
        filters1 = {"include_deleted": True}
        filters2 = {"include_deleted": True}

        key1 = analytics_service._generate_cache_key(filters1)
        key2 = analytics_service._generate_cache_key(filters2)

        # 相同的筛选条件应该生成相同的键
        assert key1 == key2

        # 不同的筛选条件应该生成不同的键
        filters3 = {"include_deleted": False}
        key3 = analytics_service._generate_cache_key(filters3)
        assert key1 != key3

    @patch(
        "src.services.analytics.analytics_service.AnalyticsService._calculate_analytics",
        new_callable=AsyncMock,
    )
    @patch(
        "src.services.analytics.analytics_service.AnalyticsService._generate_cache_key"
    )
    @pytest.mark.asyncio
    async def test_get_comprehensive_analytics_with_cache(
        self, mock_generate_key, mock_calculate, analytics_service
    ):
        """测试使用缓存的综合分析"""
        # Mock缓存命中
        mock_cache_data = {"total": 100, "timestamp": "2024-01-01"}
        analytics_service.cache.get = MagicMock(return_value=mock_cache_data)
        mock_generate_key.return_value = "test_key"

        result = await analytics_service.get_comprehensive_analytics(
            filters={}, should_use_cache=True
        )

        # 应该返回缓存数据
        assert result == mock_cache_data
        # 不应该调用计算方法
        mock_calculate.assert_not_called()

    @patch(
        "src.services.analytics.analytics_service.AnalyticsService._generate_cache_key"
    )
    @pytest.mark.asyncio
    async def test_get_comprehensive_analytics_without_cache(
        self, mock_generate_key, analytics_service
    ):
        """测试不使用缓存的综合分析"""
        # Mock缓存未命中
        analytics_service.cache.get = MagicMock(return_value=None)
        mock_generate_key.return_value = "test_key"

        # Mock AreaService 和 OccupancyService - 修复导入路径
        with patch("src.services.analytics.area_service.AreaService") as mock_area_cls:
            mock_area_service = MagicMock()
            mock_area_service.calculate_summary_with_aggregation = AsyncMock(
                return_value={"total_assets": 10}
            )
            mock_area_cls.return_value = mock_area_service

            with patch(
                "src.services.analytics.occupancy_service.OccupancyService"
            ) as mock_occupancy_cls:
                mock_occupancy_service = MagicMock()
                mock_occupancy_service.calculate_with_aggregation = AsyncMock(
                    return_value={"rate": 0.85}
                )
                mock_occupancy_cls.return_value = mock_occupancy_service

                mock_assets = [MagicMock(data_status="正常")]
                with (
                    patch(
                        "src.crud.asset.asset_crud.get_multi_with_search_async",
                        new_callable=AsyncMock,
                    ) as mock_get_assets,
                    patch.object(
                        analytics_service,
                        "_list_active_contracts",
                        AsyncMock(return_value=[]),
                    ),
                ):
                    mock_get_assets.return_value = (mock_assets, len(mock_assets))

                    result = await analytics_service.get_comprehensive_analytics(
                        filters={}, should_use_cache=False
                    )

                # 验证结果结构
                assert "total_assets" in result
                assert "timestamp" in result
                assert "area_summary" in result
                assert "occupancy_rate" in result

    @pytest.mark.asyncio
    async def test_clear_cache(self, analytics_service):
        """测试清除缓存"""
        analytics_service.cache.clear = MagicMock(return_value=True)

        result = await analytics_service.clear_cache()

        assert result["status"] == "success"
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_get_cache_stats(self, analytics_service):
        """测试获取缓存统计"""
        mock_stats = {"hits": 100, "misses": 10}
        analytics_service.cache.get_stats = MagicMock(return_value=mock_stats)

        result = await analytics_service.get_cache_stats()

        assert result["cache_type"] == "analytics_cache_shared_backend"
        assert result["stats"] == mock_stats

    @patch(
        "src.services.analytics.analytics_service.AnalyticsService._generate_occupancy_trend"
    )
    @pytest.mark.asyncio
    async def test_calculate_trend_occupancy(self, mock_trend, analytics_service):
        """测试计算出租率趋势"""
        mock_trend_data = [
            {"period": "2024-01", "occupancy_rate": 0.85},
            {"period": "2024-02", "occupancy_rate": 0.87},
        ]
        mock_trend.return_value = mock_trend_data

        mock_assets = [MagicMock(data_status="正常")]
        with patch(
            "src.crud.asset.asset_crud.get_multi_with_search_async",
            new_callable=AsyncMock,
        ) as mock_get_assets:
            mock_get_assets.return_value = (mock_assets, len(mock_assets))

            result = await analytics_service.calculate_trend(
                trend_type="occupancy", time_dimension="monthly", filters={}
            )

        assert result == mock_trend_data

    @patch(
        "src.services.analytics.analytics_service.AnalyticsService._generate_area_trend"
    )
    @pytest.mark.asyncio
    async def test_calculate_trend_area(self, mock_trend, analytics_service):
        """测试计算面积趋势"""
        mock_trend_data = [
            {"period": "2024-01", "total_area": 5000},
            {"period": "2024-02", "total_area": 5100},
        ]
        mock_trend.return_value = mock_trend_data

        mock_assets = [MagicMock(data_status="正常")]
        with patch(
            "src.crud.asset.asset_crud.get_multi_with_search_async",
            new_callable=AsyncMock,
        ) as mock_get_assets:
            mock_get_assets.return_value = (mock_assets, len(mock_assets))

            result = await analytics_service.calculate_trend(
                trend_type="area", time_dimension="monthly", filters={}
            )

        assert result == mock_trend_data

    @pytest.mark.asyncio
    async def test_calculate_distribution(self, analytics_service):
        """测试计算分布数据"""
        # Mock资产数据
        mock_assets = [
            MagicMock(
                property_nature="Commercial",
                rentable_area=1000,
                data_status="正常",
            ),
            MagicMock(
                property_nature="Residential",
                rentable_area=500,
                data_status="正常",
            ),
            MagicMock(
                property_nature="Commercial",
                rentable_area=800,
                data_status="正常",
            ),
        ]
        with patch(
            "src.crud.asset.asset_crud.get_multi_with_search_async",
            new_callable=AsyncMock,
        ) as mock_get_assets:
            mock_get_assets.return_value = (mock_assets, len(mock_assets))

            result = await analytics_service.calculate_distribution(
                distribution_type="property_nature", filters={}
            )

        assert result["distribution_type"] == "property_nature"
        assert "data" in result
        assert result["total"] == 2  # Commercial 和 Residential 两种
        assert result["data"]["Commercial"]["count"] == 2
        assert result["data"]["Commercial"]["area"] == 1800
        assert result["data"]["Residential"]["count"] == 1

    @patch(
        "src.services.analytics.analytics_service.AnalyticsService._calculate_analytics",
        new_callable=AsyncMock,
    )
    @patch(
        "src.services.analytics.analytics_service.AnalyticsService._generate_cache_key"
    )
    @pytest.mark.asyncio
    async def test_cache_is_set_after_calculation(
        self, mock_generate_key, mock_calculate, analytics_service
    ):
        """测试缓存设置逻辑（覆盖第71行）"""
        # Mock缓存未命中，需要计算并设置缓存
        analytics_service.cache.get = MagicMock(return_value=None)
        analytics_service.cache.set = MagicMock()
        mock_generate_key.return_value = "test_key"
        mock_calculate.return_value = {"total": 100}

        # 调用时使用缓存
        result = await analytics_service.get_comprehensive_analytics(
            filters={}, should_use_cache=True
        )

        # 验证缓存被设置
        analytics_service.cache.set.assert_called_once_with(
            "test_key", {"total": 100}, ttl=3600
        )
        assert result == {"total": 100}

    @pytest.mark.asyncio
    async def test_calculate_trend_unknown_type(self, analytics_service):
        """测试未知趋势类型返回空列表（覆盖第213行）"""
        mock_assets = [MagicMock(data_status="正常")]
        with patch(
            "src.crud.asset.asset_crud.get_multi_with_search_async",
            new_callable=AsyncMock,
        ) as mock_get_assets:
            mock_get_assets.return_value = (mock_assets, len(mock_assets))

            result = await analytics_service.calculate_trend(
                trend_type="unknown_type", time_dimension="monthly", filters={}
            )

        assert result == []

    @patch("src.services.analytics.area_service.AreaService")
    @patch("src.services.analytics.occupancy_service.OccupancyService")
    @pytest.mark.asyncio
    async def test_clear_cache_exception_handling(
        self, mock_occupancy_cls, mock_area_cls, analytics_service
    ):
        """测试清除缓存时的异常处理（覆盖第157-158行）"""
        # Mock缓存清除时抛出异常
        analytics_service.cache.clear = MagicMock(side_effect=Exception("Cache error"))

        result = await analytics_service.clear_cache()

        # 异常时应返回 status='failed' 和 error 信息
        assert result["status"] == "failed"
        assert result["cleared_keys"] == 0
        assert "error" in result
        assert "Cache error" in result["error"]
        assert "timestamp" in result

    def test_generate_occupancy_trend_directly(self, analytics_service):
        """测试直接调用出租率趋势生成（覆盖第221行）"""
        mock_assets = [MagicMock(data_status="正常")]
        result = analytics_service._generate_occupancy_trend(mock_assets, "monthly")

        assert isinstance(result, list)
        assert len(result) > 0
        assert result[0]["period"] == "2024-01"
        assert "occupancy_rate" in result[0]

    def test_generate_area_trend_directly(self, analytics_service):
        """测试直接调用面积趋势生成（覆盖第241行）"""
        mock_assets = [MagicMock(data_status="正常")]
        result = analytics_service._generate_area_trend(mock_assets, "monthly")

        assert isinstance(result, list)
        assert len(result) > 0
        assert result[0]["period"] == "2024-01"
        assert "total_rentable_area" in result[0]

    def test_calculate_operational_metrics_should_split_income_and_count_customers(
        self, analytics_service
    ):
        lease_group = MagicMock(revenue_mode=RevenueMode.LEASE, data_status="正常")
        lease_group.operator_party = MagicMock(review_status=PartyReviewStatus.APPROVED.value)
        lease_group.owner_party = MagicMock(review_status=PartyReviewStatus.APPROVED.value)

        agency_group = MagicMock(revenue_mode=RevenueMode.AGENCY, data_status="正常")
        agency_group.contract_group_id = "group-agency"
        agency_group.operator_party = MagicMock(review_status=PartyReviewStatus.APPROVED.value)
        agency_group.owner_party = MagicMock(review_status=PartyReviewStatus.APPROVED.value)

        lease_contract = MagicMock(
            contract_id="contract-lease-1",
            status=MagicMock(),
            data_status="正常",
            group_relation_type=GroupRelationType.DOWNSTREAM,
            contract_group=lease_group,
            lease_detail=MagicMock(rent_amount=Decimal("9999.00")),
            agency_detail=None,
            ledger_entries=[
                MagicMock(year_month="2026-05", amount_due=Decimal("600.00")),
                MagicMock(year_month="2026-06", amount_due=Decimal("400.00")),
            ],
            service_fee_ledgers=[],
            lessee_party_id="customer-1",
            lessor_party=MagicMock(review_status=PartyReviewStatus.APPROVED.value),
            lessee_party=MagicMock(review_status=PartyReviewStatus.APPROVED.value),
        )
        lease_contract.status = ContractLifecycleStatus.ACTIVE

        entrusted_contract = MagicMock(
            contract_id="contract-agency-entrusted",
            status=MagicMock(),
            data_status="正常",
            group_relation_type=GroupRelationType.ENTRUSTED,
            contract_group=agency_group,
            lease_detail=None,
            agency_detail=MagicMock(service_fee_ratio=Decimal("0.1000")),
            lessee_party_id="operator-1",
            lessor_party=MagicMock(review_status=PartyReviewStatus.APPROVED.value),
            lessee_party=MagicMock(review_status=PartyReviewStatus.APPROVED.value),
        )
        entrusted_contract.status = ContractLifecycleStatus.ACTIVE

        direct_contract = MagicMock(
            contract_id="contract-agency-direct-1",
            status=MagicMock(),
            data_status="正常",
            group_relation_type=GroupRelationType.DIRECT_LEASE,
            contract_group=agency_group,
            lease_detail=MagicMock(rent_amount=Decimal("9999.00")),
            agency_detail=None,
            ledger_entries=[],
            service_fee_ledgers=[
                MagicMock(
                    year_month="2026-05",
                    amount_due=Decimal("150.00"),
                    payment_status="paid",
                ),
                MagicMock(
                    year_month="2026-06",
                    amount_due=Decimal("50.00"),
                    payment_status="unpaid",
                ),
            ],
            lessee_party_id="customer-2",
            lessor_party=MagicMock(review_status=PartyReviewStatus.APPROVED.value),
            lessee_party=MagicMock(review_status=PartyReviewStatus.APPROVED.value),
        )
        direct_contract.status = ContractLifecycleStatus.ACTIVE

        metrics = analytics_service._calculate_operational_metrics(
            [lease_contract, entrusted_contract, direct_contract],
            {},
        )

        assert metrics["self_operated_rent_income"] == 1000.0
        assert metrics["agency_service_income"] == 200.0
        assert metrics["total_income"] == 1200.0
        assert metrics["customer_entity_count"] == 2
        assert metrics["customer_contract_count"] == 2
        assert metrics["metrics_version"]

    @pytest.mark.asyncio
    async def test_get_comprehensive_analytics_should_apply_date_window_to_ledger_backed_income_fields(
        self, analytics_service
    ):
        lease_group = MagicMock(revenue_mode=RevenueMode.LEASE, data_status="正常")
        lease_group.operator_party = MagicMock(review_status=PartyReviewStatus.APPROVED.value)
        lease_group.owner_party = MagicMock(review_status=PartyReviewStatus.APPROVED.value)

        agency_group = MagicMock(revenue_mode=RevenueMode.AGENCY, data_status="正常")
        agency_group.contract_group_id = "group-agency"
        agency_group.operator_party = MagicMock(review_status=PartyReviewStatus.APPROVED.value)
        agency_group.owner_party = MagicMock(review_status=PartyReviewStatus.APPROVED.value)

        lease_contract = MagicMock(
            contract_id="contract-lease-window",
            status=ContractLifecycleStatus.ACTIVE,
            data_status="正常",
            group_relation_type=GroupRelationType.DOWNSTREAM,
            contract_group=lease_group,
            lease_detail=MagicMock(rent_amount=Decimal("9999.00")),
            ledger_entries=[
                MagicMock(year_month="2026-05", amount_due=Decimal("600.00")),
                MagicMock(year_month="2026-06", amount_due=Decimal("400.00")),
            ],
            service_fee_ledgers=[],
            agency_detail=None,
            lessee_party_id="customer-1",
            lessor_party=MagicMock(review_status=PartyReviewStatus.APPROVED.value),
            lessee_party=MagicMock(review_status=PartyReviewStatus.APPROVED.value),
        )

        direct_contract = MagicMock(
            contract_id="contract-agency-window",
            status=ContractLifecycleStatus.ACTIVE,
            data_status="正常",
            group_relation_type=GroupRelationType.DIRECT_LEASE,
            contract_group=agency_group,
            lease_detail=MagicMock(rent_amount=Decimal("9999.00")),
            ledger_entries=[],
            service_fee_ledgers=[
                MagicMock(
                    year_month="2026-05",
                    amount_due=Decimal("150.00"),
                    payment_status="paid",
                ),
                MagicMock(
                    year_month="2026-06",
                    amount_due=Decimal("50.00"),
                    payment_status="unpaid",
                ),
            ],
            agency_detail=None,
            lessee_party_id="customer-2",
            lessor_party=MagicMock(review_status=PartyReviewStatus.APPROVED.value),
            lessee_party=MagicMock(review_status=PartyReviewStatus.APPROVED.value),
        )

        with (
            patch(
                "src.crud.asset.asset_crud.get_multi_with_search_async",
                new_callable=AsyncMock,
                return_value=([], 0),
            ),
            patch("src.services.analytics.area_service.AreaService") as mock_area_cls,
            patch(
                "src.services.analytics.occupancy_service.OccupancyService"
            ) as mock_occupancy_cls,
            patch.object(
                analytics_service,
                "_list_active_contracts",
                AsyncMock(return_value=[lease_contract, direct_contract]),
            ),
        ):
            mock_area_service = MagicMock()
            mock_area_service.calculate_summary_with_aggregation = AsyncMock(
                return_value={"total_assets": 0}
            )
            mock_area_cls.return_value = mock_area_service

            mock_occupancy_service = MagicMock()
            mock_occupancy_service.calculate_with_aggregation = AsyncMock(
                return_value={"rate": 0}
            )
            mock_occupancy_cls.return_value = mock_occupancy_service

            result = await analytics_service.get_comprehensive_analytics(
                filters={"date_from": "2026-05-01", "date_to": "2026-05-31"},
                should_use_cache=False,
            )

        assert result["self_operated_rent_income"] == 600.0
        assert result["agency_service_income"] == 150.0
        assert result["total_income"] == 750.0

    @pytest.mark.asyncio
    async def test_calculate_analytics_should_include_operational_metrics(
        self, analytics_service
    ):
        with (
            patch(
                "src.crud.asset.asset_crud.get_multi_with_search_async",
                new_callable=AsyncMock,
                return_value=([], 0),
            ),
            patch("src.services.analytics.area_service.AreaService") as mock_area_cls,
            patch(
                "src.services.analytics.occupancy_service.OccupancyService"
            ) as mock_occupancy_cls,
            patch.object(
                analytics_service,
                "_list_active_contracts",
                AsyncMock(return_value=[]),
            ) as mock_list_contracts,
        ):
            mock_area_service = MagicMock()
            mock_area_service.calculate_summary_with_aggregation = AsyncMock(
                return_value={"total_assets": 0}
            )
            mock_area_cls.return_value = mock_area_service

            mock_occupancy_service = MagicMock()
            mock_occupancy_service.calculate_with_aggregation = AsyncMock(
                return_value={"rate": 0}
            )
            mock_occupancy_cls.return_value = mock_occupancy_service

            result = await analytics_service._calculate_analytics({})

        mock_list_contracts.assert_awaited_once_with({})
        assert "total_income" in result
        assert "self_operated_rent_income" in result
        assert "agency_service_income" in result
        assert "customer_entity_count" in result
        assert "customer_contract_count" in result
        assert "metrics_version" in result
