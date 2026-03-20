import json
from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from starlette.requests import Request

from src.api.v1.assets import assets as assets_api
from src.models.asset import Asset
from src.models.contract_group import (
    Contract,
    ContractDirection,
    ContractLifecycleStatus,
    GroupRelationType,
    LeaseContractDetail,
)
from src.models.ownership import Ownership

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
        asset_name="测试资产",
        address="测试地址",
        ownership_status="已确权",
        property_nature="商业",
        usage_status="在用",
    )


def _build_contract(
    *,
    contract_number: str,
    tenant_name: str,
    effective_from: date,
    effective_to: date,
    monthly_rent: Decimal,
    deposit: Decimal,
) -> Contract:
    contract = Contract(
        contract_group_id="group-001",
        contract_number=contract_number,
        contract_direction=ContractDirection.LESSOR,
        group_relation_type=GroupRelationType.DOWNSTREAM,
        lessor_party_id="party-lessor",
        lessee_party_id="party-lessee",
        sign_date=effective_from,
        effective_from=effective_from,
        effective_to=effective_to,
        status=ContractLifecycleStatus.ACTIVE,
    )
    contract.lease_detail = LeaseContractDetail(
        rent_amount=monthly_rent,
        monthly_rent_base=monthly_rent,
        total_deposit=deposit,
        tenant_name=tenant_name,
    )
    return contract


def _build_request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/assets",
            "headers": [],
            "query_string": b"",
        }
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
            request=_build_request(),
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
    assert not any(
        "Asset.active_contract accessed" in record.message for record in caplog.records
    )


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
    asset.contracts = [
        _build_contract(
            contract_number="RC-2026-001",
            tenant_name="测试租户",
            effective_from=date(2026, 1, 1),
            effective_to=date(2026, 12, 31),
            monthly_rent=Decimal("3500.00"),
            deposit=Decimal("7000.00"),
        )
    ]

    service_stub = _AssetServiceStub([asset], 1)
    monkeypatch.setattr(assets_api, "AsyncAssetService", lambda _: service_stub)

    response = await assets_api.get_assets(
        request=_build_request(),
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
