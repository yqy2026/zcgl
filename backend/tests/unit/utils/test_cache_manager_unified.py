import pytest

from src.core.cache_manager import cache_manager as core_cache_manager
from src.utils.cache_manager import cache_manager as async_cache_manager


@pytest.mark.asyncio
async def test_utils_cache_manager_delegates_to_core_backend():
    # Set via async wrapper
    await async_cache_manager.set("statistics", "test_key", "value", expire=60)

    # Read via core cache manager
    assert core_cache_manager.get("test_key", namespace="statistics") == "value"


@pytest.mark.asyncio
async def test_utils_cache_manager_clear_pattern_affects_core_cache():
    await async_cache_manager.set("statistics", "k1", "v1", expire=60)
    await async_cache_manager.set("statistics", "k2", "v2", expire=60)

    cleared = await async_cache_manager.clear_pattern("statistics:*")
    assert cleared >= 0

    assert core_cache_manager.get("k1", namespace="statistics") is None
    assert core_cache_manager.get("k2", namespace="statistics") is None
