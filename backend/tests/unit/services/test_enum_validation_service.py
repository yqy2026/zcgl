"""
测试 AsyncEnumValidationService (枚举值动态验证服务)
"""

from __future__ import annotations

import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.services.enum_validation_service import AsyncEnumValidationService

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def enum_service(mock_db):
    return AsyncEnumValidationService(mock_db)


def _result_with_first(value):
    result = MagicMock()
    scalars = MagicMock()
    scalars.first.return_value = value
    result.scalars.return_value = scalars
    return result


def _result_with_all(values):
    result = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = values
    result.scalars.return_value = scalars
    return result


class TestAsyncEnumValidationService:
    async def test_get_valid_values_from_cache(self, enum_service):
        enum_service._cache['ownership_status'] = ['active', 'inactive']
        enum_service._cache_timestamps['ownership_status'] = time.time()

        result = await enum_service.get_valid_values('ownership_status')

        assert result == ['active', 'inactive']
        enum_service.db.execute.assert_not_called()

    async def test_get_valid_values_from_database(self, mock_db, enum_service):
        enum_type = SimpleNamespace(id='enum-1')
        mock_db.execute.side_effect = [
            _result_with_first(enum_type),
            _result_with_all(['value1', 'value2']),
        ]

        result = await enum_service.get_valid_values('ownership_status')

        assert result == ['value1', 'value2']
        assert enum_service._cache['ownership_status'] == ['value1', 'value2']

    async def test_get_valid_values_enum_type_missing(self, mock_db, enum_service):
        mock_db.execute.return_value = _result_with_first(None)

        result = await enum_service.get_valid_values('missing')

        assert result == []

    async def test_validate_value_allows_empty(self, enum_service):
        is_valid, error = await enum_service.validate_value(
            'ownership_status', '', allow_empty=True
        )

        assert is_valid is True
        assert error is None

    async def test_validate_value_invalid_value(self, enum_service):
        enum_service.get_valid_values = AsyncMock(return_value=['allowed'])

        is_valid, error = await enum_service.validate_value(
            'ownership_status', 'invalid', allow_empty=False
        )

        assert is_valid is False
        assert error is not None

    async def test_validate_asset_data_collects_errors(self, enum_service):
        enum_service.validate_value = AsyncMock(
            side_effect=[(False, 'bad'), (True, None), (True, None), (True, None), (True, None), (True, None), (True, None)]
        )

        is_valid, errors = await enum_service.validate_asset_data(
            {
                'ownership_status': 'invalid',
                'usage_status': 'ok',
                'property_nature': 'ok',
                'business_model': 'ok',
                'operation_status': 'ok',
                'tenant_type': 'ok',
                'data_status': 'ok',
            }
        )

        assert is_valid is False
        assert errors == ['ownership_status: bad']
