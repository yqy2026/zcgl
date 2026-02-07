from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.services.ownership.service import OwnershipService

pytestmark = pytest.mark.asyncio


def _result_with_scalars(values):
    result = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = values
    result.scalars.return_value = scalars
    return result


def _result_with_all(values):
    result = MagicMock()
    result.all.return_value = values
    return result


@pytest.fixture
def service() -> OwnershipService:
    return OwnershipService()


class TestOwnershipDropdownOptions:
    async def test_batches_asset_and_project_counts(self, service: OwnershipService):
        ownership_1 = MagicMock()
        ownership_1.id = "own-1"
        ownership_1.name = "权属方1"
        ownership_1.code = "OW001"
        ownership_1.short_name = "A"
        ownership_1.is_active = True
        ownership_1.data_status = "正常"
        ownership_1.created_at = datetime.now(UTC)
        ownership_1.updated_at = datetime.now(UTC)

        ownership_2 = MagicMock()
        ownership_2.id = "own-2"
        ownership_2.name = "权属方2"
        ownership_2.code = "OW002"
        ownership_2.short_name = "B"
        ownership_2.is_active = True
        ownership_2.data_status = "正常"
        ownership_2.created_at = datetime.now(UTC)
        ownership_2.updated_at = datetime.now(UTC)

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(
            side_effect=[
                _result_with_scalars([ownership_1, ownership_2]),
                _result_with_all([("own-1", 3)]),
                _result_with_all([("own-1", 1), ("own-2", 2)]),
            ]
        )

        result = await service.get_ownership_dropdown_options(mock_db)

        assert len(result) == 2
        assert result[0]["asset_count"] == 3
        assert result[0]["project_count"] == 1
        assert result[1]["asset_count"] == 0
        assert result[1]["project_count"] == 2
        assert mock_db.execute.await_count == 3

    async def test_returns_early_when_no_ownerships(self, service: OwnershipService):
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(side_effect=[_result_with_scalars([])])

        result = await service.get_ownership_dropdown_options(mock_db)

        assert result == []
        assert mock_db.execute.await_count == 1
