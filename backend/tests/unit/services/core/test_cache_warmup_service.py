"""Unit tests for startup cache warmup service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.cache_warmup_service import CacheWarmupService

pytestmark = pytest.mark.asyncio


async def test_warmup_low_churn_data_success() -> None:
    """Warmup should populate dictionary/org cache targets and return success summary."""
    service = CacheWarmupService()
    mock_db = MagicMock()

    with patch(
        "src.services.cache_warmup_service.system_dictionary_service.get_types_async",
        new=AsyncMock(return_value=["organization_type", "organization_status"]),
    ), patch(
        "src.services.cache_warmup_service.organization_service.get_statistics",
        new=AsyncMock(return_value={"total": 8}),
    ):
        result = await service.warmup_low_churn_data(mock_db)

    assert result["success_count"] == 2
    assert result["failure_count"] == 0
    assert result["items"]["system_dictionary.types"]["status"] == "success"
    assert result["items"]["organization.statistics"]["status"] == "success"


async def test_warmup_low_churn_data_partial_failure() -> None:
    """Warmup should continue when one target fails."""
    service = CacheWarmupService()
    mock_db = MagicMock()

    with patch(
        "src.services.cache_warmup_service.system_dictionary_service.get_types_async",
        new=AsyncMock(side_effect=RuntimeError("dict unavailable")),
    ), patch(
        "src.services.cache_warmup_service.organization_service.get_statistics",
        new=AsyncMock(return_value={"total": 5}),
    ):
        result = await service.warmup_low_churn_data(mock_db)

    assert result["success_count"] == 1
    assert result["failure_count"] == 1
    assert result["items"]["system_dictionary.types"]["status"] == "failed"
    assert "dict unavailable" in result["items"]["system_dictionary.types"]["error"]
    assert result["items"]["organization.statistics"]["status"] == "success"
