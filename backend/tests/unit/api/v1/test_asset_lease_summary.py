from datetime import date, timedelta
from unittest.mock import AsyncMock

from dateutil.relativedelta import relativedelta
from starlette import status

from src.core.exception_handler import ResourceNotFoundError


class TestGetAssetLeaseSummary:
    def test_get_asset_lease_summary_returns_default_period(
        self,
        client,
        auth_headers,
        monkeypatch,
    ):
        from src.api.v1.assets import assets as asset_module

        today = date.today()
        default_start = today.replace(day=1)
        default_end = (default_start + relativedelta(months=1)) - timedelta(days=1)

        async def mock_get_asset_lease_summary(
            self,
            asset_id: str,
            *,
            period_start: date | None = None,
            period_end: date | None = None,
            current_user_id: str | None = None,
        ):
            assert asset_id == "asset-1"
            assert current_user_id is not None
            return {
                "asset_id": asset_id,
                "period_start": default_start,
                "period_end": default_end,
                "total_contracts": 0,
                "total_rented_area": 0.0,
                "rentable_area": 100.0,
                "occupancy_rate": 0.0,
                "by_type": [
                    {
                        "group_relation_type": "上游",
                        "label": "上游承租",
                        "contract_count": 0,
                        "total_area": 0.0,
                        "monthly_amount": 0.0,
                    },
                    {
                        "group_relation_type": "下游",
                        "label": "下游转租",
                        "contract_count": 0,
                        "total_area": 0.0,
                        "monthly_amount": 0.0,
                    },
                    {
                        "group_relation_type": "委托",
                        "label": "委托协议",
                        "contract_count": 0,
                        "total_area": 0.0,
                        "monthly_amount": 0.0,
                    },
                    {
                        "group_relation_type": "直租",
                        "label": "直租合同",
                        "contract_count": 0,
                        "total_area": 0.0,
                        "monthly_amount": 0.0,
                    },
                ],
                "customer_summary": [],
            }

        monkeypatch.setattr(
            asset_module.AsyncAssetService,
            "get_asset_lease_summary",
            mock_get_asset_lease_summary,
            raising=False,
        )

        response = client.get(
            "/api/v1/assets/asset-1/lease-summary",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert payload["success"] is True
        assert payload["data"]["asset_id"] == "asset-1"
        assert payload["data"]["period_start"] == default_start.isoformat()
        assert payload["data"]["period_end"] == default_end.isoformat()

    def test_get_asset_lease_summary_not_found(
        self,
        client,
        auth_headers,
        monkeypatch,
    ):
        from src.api.v1.assets import assets as asset_module

        monkeypatch.setattr(
            asset_module.AsyncAssetService,
            "get_asset_lease_summary",
            AsyncMock(side_effect=ResourceNotFoundError("Asset", "missing")),
            raising=False,
        )

        response = client.get(
            "/api/v1/assets/missing/lease-summary",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_asset_lease_summary_aligns_partial_period_to_same_month(
        self,
        client,
        auth_headers,
        monkeypatch,
    ):
        from src.api.v1.assets import assets as asset_module

        async def mock_get_asset_lease_summary(
            self,
            asset_id: str,
            *,
            period_start: date | None = None,
            period_end: date | None = None,
            current_user_id: str | None = None,
        ):
            assert asset_id == "asset-1"
            return {
                "asset_id": asset_id,
                "period_start": date(2026, 4, 1),
                "period_end": date(2026, 4, 30),
                "total_contracts": 0,
                "total_rented_area": 0.0,
                "rentable_area": 100.0,
                "occupancy_rate": 0.0,
                "by_type": [],
                "customer_summary": [],
            }

        monkeypatch.setattr(
            asset_module.AsyncAssetService,
            "get_asset_lease_summary",
            mock_get_asset_lease_summary,
            raising=False,
        )

        response = client.get(
            "/api/v1/assets/asset-1/lease-summary?period_start=2026-04-01",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert payload["data"]["period_start"] == "2026-04-01"
        assert payload["data"]["period_end"] == "2026-04-30"

    def test_get_asset_lease_summary_aligns_period_end_only_to_same_month(
        self,
        client,
        auth_headers,
        monkeypatch,
    ):
        from src.api.v1.assets import assets as asset_module

        async def mock_get_asset_lease_summary(
            self,
            asset_id: str,
            *,
            period_start: date | None = None,
            period_end: date | None = None,
            current_user_id: str | None = None,
        ):
            assert asset_id == "asset-1"
            return {
                "asset_id": asset_id,
                "period_start": date(2026, 5, 1),
                "period_end": date(2026, 5, 31),
                "total_contracts": 0,
                "total_rented_area": 0.0,
                "rentable_area": 100.0,
                "occupancy_rate": 0.0,
                "by_type": [],
                "customer_summary": [],
            }

        monkeypatch.setattr(
            asset_module.AsyncAssetService,
            "get_asset_lease_summary",
            mock_get_asset_lease_summary,
            raising=False,
        )

        response = client.get(
            "/api/v1/assets/asset-1/lease-summary?period_end=2026-05-31",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert payload["data"]["period_start"] == "2026-05-01"
        assert payload["data"]["period_end"] == "2026-05-31"
