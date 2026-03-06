from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.exception_handler import ResourceNotFoundError
from src.models.contract_group import GroupRelationType
from src.services.asset.asset_service import AssetService

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.in_transaction.return_value = True
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db


@pytest.fixture
def service(mock_db):
    return AssetService(mock_db)


def _build_contract(
    *,
    contract_id: str,
    group_relation_type: GroupRelationType,
    monthly_rent_base: str | None = None,
    lessee_party_id: str | None = None,
    lessee_party_name: str | None = None,
    tenant_name: str | None = None,
):
    lease_detail = None
    if monthly_rent_base is not None or tenant_name is not None:
        lease_detail = SimpleNamespace(
            monthly_rent_base=(
                Decimal(monthly_rent_base) if monthly_rent_base is not None else None
            ),
            tenant_name=tenant_name,
        )

    return SimpleNamespace(
        contract_id=contract_id,
        group_relation_type=group_relation_type,
        lease_detail=lease_detail,
        agency_detail=None,
        lessee_party_id=lessee_party_id,
        lessee_party=(
            SimpleNamespace(name=lessee_party_name)
            if lessee_party_name is not None
            else None
        ),
    )


class TestGetAssetLeaseSummary:
    async def test_active_contracts_by_group_relation_type(self, service):
        from src.services.asset import asset_service as asset_service_module

        asset = SimpleNamespace(
            id="asset-1",
            data_status="正常",
            rentable_area=Decimal("100"),
        )
        contracts = [
            _build_contract(
                contract_id="c1",
                group_relation_type=GroupRelationType.UPSTREAM,
                monthly_rent_base="1200",
            ),
            _build_contract(
                contract_id="c2",
                group_relation_type=GroupRelationType.DOWNSTREAM,
                monthly_rent_base="2300",
                lessee_party_id="party-1",
                lessee_party_name="租户A",
            ),
            _build_contract(
                contract_id="c3",
                group_relation_type=GroupRelationType.ENTRUSTED,
            ),
            _build_contract(
                contract_id="c4",
                group_relation_type=GroupRelationType.DIRECT_LEASE,
                monthly_rent_base="3400",
                lessee_party_id="party-2",
                lessee_party_name="租户B",
            ),
        ]

        with (
            patch.object(service, "get_asset", new=AsyncMock(return_value=asset)),
        ):
            asset_service_module.contract_crud = SimpleNamespace(  # type: ignore[attr-defined]
                get_active_by_asset_id=AsyncMock(return_value=contracts)
            )
            result = await service.get_asset_lease_summary(
                asset_id="asset-1",
                current_user_id="user-1",
            )

        assert result.total_contracts == 4
        assert result.total_rented_area == 0.0
        assert result.rentable_area == 100.0
        assert result.occupancy_rate == 0.0
        assert [item.group_relation_type for item in result.by_type] == [
            "上游",
            "下游",
            "委托",
            "直租",
        ]
        assert [item.contract_count for item in result.by_type] == [1, 1, 1, 1]
        assert [item.monthly_amount for item in result.by_type] == [
            1200.0,
            2300.0,
            0.0,
            3400.0,
        ]

    async def test_customer_summary_only_outbound_and_dedup(self, service):
        from src.services.asset import asset_service as asset_service_module

        asset = SimpleNamespace(
            id="asset-1",
            data_status="正常",
            rentable_area=Decimal("50"),
        )
        contracts = [
            _build_contract(
                contract_id="up-1",
                group_relation_type=GroupRelationType.UPSTREAM,
                monthly_rent_base="1000",
                lessee_party_id="internal-1",
                lessee_party_name="内部主体",
            ),
            _build_contract(
                contract_id="down-1",
                group_relation_type=GroupRelationType.DOWNSTREAM,
                monthly_rent_base="2000",
                lessee_party_id="party-1",
                lessee_party_name="租户A",
            ),
            _build_contract(
                contract_id="down-2",
                group_relation_type=GroupRelationType.DOWNSTREAM,
                monthly_rent_base="2200",
                lessee_party_id="party-1",
                lessee_party_name="租户A",
            ),
            _build_contract(
                contract_id="direct-1",
                group_relation_type=GroupRelationType.DIRECT_LEASE,
                monthly_rent_base="3200",
                lessee_party_id=None,
                lessee_party_name=None,
                tenant_name="直租租户",
            ),
            _build_contract(
                contract_id="entrusted-1",
                group_relation_type=GroupRelationType.ENTRUSTED,
            ),
        ]

        with (
            patch.object(service, "get_asset", new=AsyncMock(return_value=asset)),
        ):
            asset_service_module.contract_crud = SimpleNamespace(  # type: ignore[attr-defined]
                get_active_by_asset_id=AsyncMock(return_value=contracts)
            )
            result = await service.get_asset_lease_summary(asset_id="asset-1")

        assert [(item.party_name, item.group_relation_type, item.contract_count) for item in result.customer_summary] == [
            ("租户A", "下游", 2),
            ("直租租户", "直租", 1),
        ]

    async def test_no_active_contracts_and_zero_rentable_area(self, service):
        from src.services.asset import asset_service as asset_service_module

        asset = SimpleNamespace(
            id="asset-1",
            data_status="正常",
            rentable_area=Decimal("0"),
        )

        with (
            patch.object(service, "get_asset", new=AsyncMock(return_value=asset)),
        ):
            asset_service_module.contract_crud = SimpleNamespace(  # type: ignore[attr-defined]
                get_active_by_asset_id=AsyncMock(return_value=[])
            )
            result = await service.get_asset_lease_summary(asset_id="asset-1")

        assert result.total_contracts == 0
        assert result.rentable_area == 0.0
        assert result.occupancy_rate == 0.0
        assert result.customer_summary == []
        assert [item.contract_count for item in result.by_type] == [0, 0, 0, 0]

    async def test_partial_period_aligns_to_provided_month(self, service):
        from src.services.asset import asset_service as asset_service_module

        asset = SimpleNamespace(
            id="asset-1",
            data_status="正常",
            rentable_area=Decimal("80"),
        )

        with (
            patch.object(service, "get_asset", new=AsyncMock(return_value=asset)),
        ):
            asset_service_module.contract_crud = SimpleNamespace(  # type: ignore[attr-defined]
                get_active_by_asset_id=AsyncMock(return_value=[])
            )
            start_only_result = await service.get_asset_lease_summary(
                asset_id="asset-1",
                period_start=date(2026, 4, 1),
            )
            end_only_result = await service.get_asset_lease_summary(
                asset_id="asset-1",
                period_end=date(2026, 5, 31),
            )

        assert start_only_result.period_start == date(2026, 4, 1)
        assert start_only_result.period_end == date(2026, 4, 30)
        assert end_only_result.period_start == date(2026, 5, 1)
        assert end_only_result.period_end == date(2026, 5, 31)

    async def test_asset_not_found(self, service):
        with patch.object(
            service,
            "get_asset",
            new=AsyncMock(side_effect=ResourceNotFoundError("Asset", "missing")),
        ):
            with pytest.raises(ResourceNotFoundError):
                await service.get_asset_lease_summary(asset_id="missing")
