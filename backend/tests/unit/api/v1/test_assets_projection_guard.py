import json
from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from src.api.v1.assets import assets as assets_api
from src.core.enums import ContractStatus
from src.models.asset import Asset
from src.models.ownership import Ownership
from src.models.rent_contract import RentContract

pytestmark = [pytest.mark.unit, pytest.mark.api]


class _AssetServiceStub:
    def __init__(self, assets, total):
        self._assets = assets
        self._total = total
        self.last_kwargs = None

    async def get_assets(self, **kwargs):
        self.last_kwargs = kwargs
        return self._assets, self._total


def _build_asset() -> Asset:
    return Asset(
        ownership_id="ownership-1",
        property_name="测试资产",
        address="测试地址",
        ownership_status="已确权",
        property_nature="商业",
        usage_status="在用",
    )


@pytest.mark.asyncio
async def test_get_assets_without_relations_keeps_contract_projection_empty(
    monkeypatch, caplog
):
    asset = _build_asset()
    service_stub = _AssetServiceStub([asset], 1)
    monkeypatch.setattr(assets_api, "AsyncAssetService", lambda _: service_stub)

    with caplog.at_level("WARNING"):
        response = await assets_api.get_assets(
            page=1,
            page_size=20,
            search=None,
            ownership_status=None,
            property_nature=None,
            usage_status=None,
            ownership_id=None,
            management_entity=None,
            business_category=None,
            data_status=None,
            min_area=None,
            max_area=None,
            min_occupancy_rate=None,
            max_occupancy_rate=None,
            is_litigated=None,
            include_relations=False,
            sort_field="created_at",
            sort_by=None,
            sort_order="desc",
            db=MagicMock(),
            current_user=MagicMock(),
        )

    payload = json.loads(response.body)
    item = payload["data"]["items"][0]

    assert service_stub.last_kwargs is not None
    assert service_stub.last_kwargs["include_relations"] is False
    assert item["tenant_name"] is None
    assert item["lease_contract_number"] is None
    assert item["contract_start_date"] is None
    assert item["contract_end_date"] is None
    assert not any("Asset.active_contract accessed" in record.message for record in caplog.records)


@pytest.mark.asyncio
async def test_get_assets_with_relations_projects_active_contract(monkeypatch):
    asset = _build_asset()
    asset.ownership = Ownership(
        id="owner-001",
        name="测试权属方",
        code="OWN-001",
        is_active=True,
        created_at=datetime.now(UTC).replace(tzinfo=None),
        updated_at=datetime.now(UTC).replace(tzinfo=None),
    )
    asset.rent_contracts = [
        RentContract(
            contract_number="RC-2026-001",
            ownership_id="ownership-1",
            tenant_name="测试租户",
            sign_date=date(2026, 1, 1),
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            contract_status=ContractStatus.ACTIVE.value,
            monthly_rent_base=Decimal("3500.00"),
            total_deposit=Decimal("7000.00"),
        )
    ]

    service_stub = _AssetServiceStub([asset], 1)
    monkeypatch.setattr(assets_api, "AsyncAssetService", lambda _: service_stub)

    response = await assets_api.get_assets(
        page=1,
        page_size=20,
        search=None,
        ownership_status=None,
        property_nature=None,
        usage_status=None,
        ownership_id=None,
        management_entity=None,
        business_category=None,
        data_status=None,
        min_area=None,
        max_area=None,
        min_occupancy_rate=None,
        max_occupancy_rate=None,
        is_litigated=None,
        include_relations=True,
        sort_field="created_at",
        sort_by=None,
        sort_order="desc",
        db=MagicMock(),
        current_user=MagicMock(),
    )
    payload = json.loads(response.body)
    item = payload["data"]["items"][0]

    assert service_stub.last_kwargs is not None
    assert service_stub.last_kwargs["include_relations"] is True
    assert item["ownership_entity"] == "测试权属方"
    assert item["tenant_name"] == "测试租户"
    assert item["lease_contract_number"] == "RC-2026-001"
    assert item["monthly_rent"] == "3500.00"
    assert item["deposit"] == "7000.00"
