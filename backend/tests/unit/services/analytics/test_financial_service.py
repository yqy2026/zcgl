"""
Unit tests for FinancialService.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.analytics.financial_service import FinancialService


@pytest.fixture
def service(mock_db):
    return FinancialService(mock_db)


@patch("src.services.analytics.financial_service.asset_crud")
@patch("src.services.analytics.financial_service.to_float")
@pytest.mark.asyncio
async def test_calculate_summary_empty(mock_to_float, mock_asset_crud, service):
    mock_asset_crud.get_multi_with_search_async = AsyncMock(return_value=([], 0))
    mock_to_float.return_value = 0.0

    summary = await service.calculate_summary()

    assert summary["total_assets"] == 0
    assert summary["total_annual_income"] == 0.0
    assert summary["total_annual_expense"] == 0.0
    assert summary["net_annual_income"] == 0.0
    assert summary["income_per_sqm"] == 0.0
    assert summary["expense_per_sqm"] == 0.0
    mock_asset_crud.get_multi_with_search_async.assert_awaited_once_with(
        db=service.db,
        skip=0,
        limit=10000,
        filters=None,
        include_contract_projection=False,
    )


@patch("src.services.analytics.financial_service.asset_crud")
@patch("src.services.analytics.financial_service.to_float")
@pytest.mark.asyncio
async def test_calculate_summary_with_assets(mock_to_float, mock_asset_crud, service):
    asset_a = MagicMock()
    asset_a.rentable_area = 100.0
    asset_a.annual_income = 1000.0
    asset_a.annual_expense = 400.0
    asset_a.net_income = 600.0

    asset_b = MagicMock()
    asset_b.rentable_area = 50.0
    asset_b.annual_income = 2000.0
    asset_b.annual_expense = 600.0
    asset_b.net_income = 1400.0

    mock_asset_crud.get_multi_with_search_async = AsyncMock(
        return_value=([asset_a, asset_b], 2)
    )
    mock_to_float.side_effect = lambda x: x

    summary = await service.calculate_summary()

    assert summary["total_assets"] == 2
    assert summary["total_annual_income"] == 3000.0
    assert summary["total_annual_expense"] == 1000.0
    assert summary["net_annual_income"] == 2000.0
    assert summary["income_per_sqm"] == 20.0
    assert summary["expense_per_sqm"] == 6.67


@patch("src.services.analytics.financial_service.asset_crud")
@patch("src.services.analytics.financial_service.to_float")
@pytest.mark.asyncio
async def test_calculate_summary_zero_area(mock_to_float, mock_asset_crud, service):
    asset = MagicMock()
    asset.rentable_area = 0.0
    asset.annual_income = 1000.0
    asset.annual_expense = 500.0
    asset.net_income = 500.0

    mock_asset_crud.get_multi_with_search_async = AsyncMock(return_value=([asset], 1))
    mock_to_float.side_effect = lambda x: x

    summary = await service.calculate_summary()

    assert summary["income_per_sqm"] == 0.0
    assert summary["expense_per_sqm"] == 0.0
