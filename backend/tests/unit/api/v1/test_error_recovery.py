"""
Comprehensive Unit Tests for Error Recovery API Routes (src/api/v1/error_recovery.py)

This test module covers all endpoints in the error recovery router to achieve 70%+ coverage:

Endpoints Tested:
1. GET /api/v1/error-recovery/statistics - Get error recovery statistics
2. GET /api/v1/error-recovery/strategies - Get error recovery strategies
3. PUT /api/v1/error-recovery/strategies/{category} - Update error recovery strategy
4. GET /api/v1/error-recovery/circuit-breakers - Get circuit breaker status
5. POST /api/v1/error-recovery/circuit-breakers/{category}/reset - Reset circuit breaker
6. GET /api/v1/error-recovery/history - Get error recovery history
7. POST /api/v1/error-recovery/test - Test error recovery
8. DELETE /api/v1/error-recovery/history/clear - Clear error recovery history
9. GET /api/v1/error-recovery/health - Get error recovery system health

Testing Approach:
- Mock all dependencies (error_recovery_engine, services, auth)
- Test successful responses
- Test error handling scenarios
- Test request validation
- Test response schemas
- Test permission checks
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from src.core.exception_handler import BaseBusinessError

pytestmark = pytest.mark.api


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_current_user():
    """Create mock authenticated user"""
    user = MagicMock()
    user.id = "test-user-id"
    user.username = "testuser"
    user.is_active = True
    return user


@pytest.fixture
def mock_error_recovery_engine():
    """Create mock error recovery engine"""
    engine = MagicMock()

    # Mock strategies
    from src.services.error_recovery_service import ErrorCategory, RecoveryStrategy

    engine.strategies = {}
    for category in ErrorCategory:
        engine.strategies[category] = RecoveryStrategy(
            name=f"{category.value}_strategy",
            category=category,
            max_attempts=3,
            base_delay=1.0,
            max_delay=60.0,
            backoff_multiplier=2.0,
            auto_recovery=True,
            fallback_enabled=True,
            requires_manual_intervention=False,
        )

    # Mock circuit breakers
    engine.circuit_breakers = {}
    for category in ErrorCategory:
        engine.circuit_breakers[category.value] = {
            "state": "closed",
            "failure_count": 0,
            "opened_at": None,
            "timeout": 60,
        }

    # Mock recovery history
    engine.recovery_history = [
        {
            "error_id": "test_error_1",
            "category": "database",
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "attempts": 2,
        },
        {
            "error_id": "test_error_2",
            "category": "network",
            "success": False,
            "timestamp": datetime.now().isoformat(),
            "attempts": 3,
        },
    ]

    # Mock statistics
    engine.get_recovery_statistics.return_value = {
        "total_recoveries": 100,
        "successful_recoveries": 90,
        "success_rate": 90.0,
        "average_attempts": 2.5,
        "average_time": 1.2,
        "by_category": {
            "database": {
                "total": 50,
                "successful": 45,
                "success_rate": 90.0,
            },
            "network": {
                "total": 30,
                "successful": 27,
                "success_rate": 90.0,
            },
        },
    }

    # Mock recover_from_error
    from src.services.error_recovery_service import RecoveryResult

    engine.recover_from_error = AsyncMock(
        return_value=RecoveryResult(
            success=True,
            attempts_made=2,
            total_time=0.5,
            strategy_used="database_strategy",
            recovery_actions=["retry", "fallback"],
        )
    )

    return engine


# ============================================================================
# Test: GET /statistics - Get Error Recovery Statistics
# ============================================================================


class TestGetRecoveryStatistics:
    """Tests for GET /api/v1/error-recovery/statistics endpoint"""

    @patch("src.api.v1.system.error_recovery.error_recovery_engine")
    @pytest.mark.asyncio
    async def test_get_statistics_success(self, mock_engine, mock_current_user):
        """Test getting statistics successfully"""
        from src.api.v1.system.error_recovery import get_recovery_statistics

        mock_engine.get_recovery_statistics.return_value = {
            "total_recoveries": 100,
            "successful_recoveries": 90,
            "success_rate": 90.0,
            "average_attempts": 2.5,
            "average_time": 1.2,
            "by_category": {
                "database": {
                    "total": 50,
                    "successful": 45,
                    "success_rate": 90.0,
                }
            },
        }

        response = await get_recovery_statistics(
            category=None,
            start_time=None,
            end_time=None,
            current_user=mock_current_user,
        )

        assert response["success"] is True
        result = response["data"]
        assert result.total_recoveries == 100
        assert result.successful_recoveries == 90
        assert result.success_rate == 90.0
        assert result.average_attempts == 2.5
        assert result.average_time == 1.2
        assert len(result.by_category) == 1

    @patch("src.api.v1.system.error_recovery.error_recovery_engine")
    @pytest.mark.asyncio
    async def test_get_statistics_with_category_filter(
        self, mock_engine, mock_current_user
    ):
        """Test getting statistics with category filter"""
        from src.api.v1.system.error_recovery import get_recovery_statistics

        mock_engine.get_recovery_statistics.return_value = {
            "total_recoveries": 100,
            "successful_recoveries": 90,
            "success_rate": 90.0,
            "average_attempts": 2.5,
            "average_time": 1.2,
            "by_category": {
                "database": {"total": 50, "successful": 45, "success_rate": 90.0},
                "network": {"total": 30, "successful": 27, "success_rate": 90.0},
            },
        }

        response = await get_recovery_statistics(
            category="database",
            start_time=None,
            end_time=None,
            current_user=mock_current_user,
        )

        assert response["success"] is True
        result = response["data"]
        assert len(result.by_category) == 1
        assert "database" in result.by_category

    @patch("src.api.v1.system.error_recovery.error_recovery_engine")
    @pytest.mark.asyncio
    async def test_get_statistics_invalid_category_filter(
        self, mock_engine, mock_current_user
    ):
        """Test getting statistics with non-existent category filter"""
        from src.api.v1.system.error_recovery import get_recovery_statistics

        mock_engine.get_recovery_statistics.return_value = {
            "total_recoveries": 100,
            "successful_recoveries": 90,
            "success_rate": 90.0,
            "average_attempts": 2.5,
            "average_time": 1.2,
            "by_category": {
                "database": {"total": 50, "successful": 45, "success_rate": 90.0}
            },
        }

        response = await get_recovery_statistics(
            category="nonexistent",
            start_time=None,
            end_time=None,
            current_user=mock_current_user,
        )

        assert response["success"] is True
        result = response["data"]
        assert len(result.by_category) == 0

    @patch("src.api.v1.system.error_recovery.error_recovery_engine")
    @pytest.mark.asyncio
    async def test_get_statistics_engine_error(self, mock_engine, mock_current_user):
        """Test getting statistics when engine raises exception"""
        from src.api.v1.system.error_recovery import get_recovery_statistics

        mock_engine.get_recovery_statistics.side_effect = Exception("Engine error")

        with pytest.raises(BaseBusinessError) as exc_info:
            await get_recovery_statistics(
                category=None,
                start_time=None,
                end_time=None,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 500
        assert "获取统计信息失败" in exc_info.value.message


# ============================================================================
# Test: GET /strategies - Get Error Recovery Strategies
# ============================================================================


class TestGetRecoveryStrategies:
    """Tests for GET /api/v1/error-recovery/strategies endpoint"""

    @pytest.mark.asyncio
    async def test_get_strategies_success(
        self, mock_error_recovery_engine, mock_current_user
    ):
        """Test getting all strategies successfully"""
        from src.api.v1.system.error_recovery import get_recovery_strategies

        with patch(
            "src.api.v1.system.error_recovery.error_recovery_engine",
            mock_error_recovery_engine,
        ):
            response = await get_recovery_strategies(current_user=mock_current_user)

            assert response["success"] is True
            result = response["data"]
            assert len(result) > 0
            assert all(hasattr(strategy, "name") for strategy in result)
            assert all(hasattr(strategy, "category") for strategy in result)
            assert all(hasattr(strategy, "max_attempts") for strategy in result)
            assert all(hasattr(strategy, "auto_recovery") for strategy in result)

    @pytest.mark.asyncio
    async def test_get_strategies_content(
        self, mock_error_recovery_engine, mock_current_user
    ):
        """Test strategy response content"""
        from src.api.v1.system.error_recovery import get_recovery_strategies

        with patch(
            "src.api.v1.system.error_recovery.error_recovery_engine",
            mock_error_recovery_engine,
        ):
            response = await get_recovery_strategies(current_user=mock_current_user)

            assert response["success"] is True
            result = response["data"]
            first_strategy = result[0]
            assert first_strategy.category in [
                "network",
                "database",
                "validation",
                "authentication",
            ]
            assert first_strategy.max_attempts == 3
            assert first_strategy.base_delay == 1.0
            assert first_strategy.max_delay == 60.0
            assert first_strategy.backoff_multiplier == 2.0
            assert first_strategy.auto_recovery is True
            assert first_strategy.fallback_enabled is True
            assert first_strategy.requires_manual_intervention is False

    @pytest.mark.asyncio
    async def test_get_strategies_engine_error(self, mock_current_user):
        """Test getting strategies when engine raises exception"""
        from src.api.v1.system.error_recovery import get_recovery_strategies

        mock_engine = MagicMock()
        mock_engine.strategies.side_effect = Exception("Strategy error")

        with patch("src.api.v1.system.error_recovery.error_recovery_engine", mock_engine):
            with pytest.raises(BaseBusinessError) as exc_info:
                await get_recovery_strategies(current_user=mock_current_user)

            assert exc_info.value.status_code == 500
            assert "获取策略配置失败" in exc_info.value.message


# ============================================================================
# Test: PUT /strategies/{category} - Update Error Recovery Strategy
# ============================================================================


class TestUpdateRecoveryStrategy:
    """Tests for PUT /api/v1/error-recovery/strategies/{category} endpoint"""

    @pytest.mark.asyncio
    async def test_update_strategy_success(
        self, mock_error_recovery_engine, mock_current_user
    ):
        """Test updating strategy successfully"""
        from src.api.v1.system.error_recovery import (
            RecoveryStrategyUpdate,
            update_recovery_strategy,
        )

        with patch(
            "src.api.v1.system.error_recovery.error_recovery_engine",
            mock_error_recovery_engine,
        ):
            strategy_update = RecoveryStrategyUpdate(max_attempts=5, base_delay=2.0)

            response = await update_recovery_strategy(
                category="database",
                strategy_update=strategy_update,
                current_user=mock_current_user,
            )

            assert response["success"] is True
            result = response["data"]
            assert result["updated_strategy"]["max_attempts"] == 5
            assert result["updated_strategy"]["base_delay"] == 2.0

    @pytest.mark.asyncio
    async def test_update_strategy_multiple_fields(
        self, mock_error_recovery_engine, mock_current_user
    ):
        """Test updating multiple strategy fields"""
        from src.api.v1.system.error_recovery import (
            RecoveryStrategyUpdate,
            update_recovery_strategy,
        )

        with patch(
            "src.api.v1.system.error_recovery.error_recovery_engine",
            mock_error_recovery_engine,
        ):
            strategy_update = RecoveryStrategyUpdate(
                max_attempts=5,
                base_delay=2.0,
                max_delay=120.0,
                backoff_multiplier=3.0,
                auto_recovery=False,
            )

            response = await update_recovery_strategy(
                category="database",
                strategy_update=strategy_update,
                current_user=mock_current_user,
            )

            assert response["success"] is True
            result = response["data"]
            assert result["updated_strategy"]["max_attempts"] == 5
            assert result["updated_strategy"]["base_delay"] == 2.0
            assert result["updated_strategy"]["max_delay"] == 120.0
            assert result["updated_strategy"]["backoff_multiplier"] == 3.0
            assert result["updated_strategy"]["auto_recovery"] is False

    @pytest.mark.asyncio
    async def test_update_strategy_invalid_category(
        self, mock_error_recovery_engine, mock_current_user
    ):
        """Test updating strategy with invalid category"""
        from src.api.v1.system.error_recovery import (
            RecoveryStrategyUpdate,
            update_recovery_strategy,
        )

        with patch(
            "src.api.v1.system.error_recovery.error_recovery_engine",
            mock_error_recovery_engine,
        ):
            strategy_update = RecoveryStrategyUpdate(max_attempts=5)

            with pytest.raises(BaseBusinessError) as exc_info:
                await update_recovery_strategy(
                    category="invalid_category",
                    strategy_update=strategy_update,
                    current_user=mock_current_user,
                )

            assert exc_info.value.status_code == 400
            assert "无效的错误类别" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_update_strategy_partial_update(
        self, mock_error_recovery_engine, mock_current_user
    ):
        """Test updating strategy with partial fields"""
        from src.api.v1.system.error_recovery import (
            RecoveryStrategyUpdate,
            update_recovery_strategy,
        )

        with patch(
            "src.api.v1.system.error_recovery.error_recovery_engine",
            mock_error_recovery_engine,
        ):
            # Only update max_attempts, other fields should remain unchanged
            strategy_update = RecoveryStrategyUpdate(max_attempts=7)

            response = await update_recovery_strategy(
                category="database",
                strategy_update=strategy_update,
                current_user=mock_current_user,
            )

            assert response["success"] is True
            result = response["data"]
            assert result["updated_strategy"]["max_attempts"] == 7
            # Other fields should remain at default values
            assert result["updated_strategy"]["base_delay"] == 1.0

    @pytest.mark.asyncio
    async def test_update_strategy_not_found(
        self, mock_error_recovery_engine, mock_current_user
    ):
        """Test updating strategy when strategy doesn't exist"""
        from src.api.v1.system.error_recovery import (
            RecoveryStrategyUpdate,
            update_recovery_strategy,
        )

        # Remove the database strategy
        from src.services.error_recovery_service import ErrorCategory

        del mock_error_recovery_engine.strategies[ErrorCategory.DATABASE]

        with patch(
            "src.api.v1.system.error_recovery.error_recovery_engine",
            mock_error_recovery_engine,
        ):
            strategy_update = RecoveryStrategyUpdate(max_attempts=5)

            with pytest.raises(BaseBusinessError) as exc_info:
                await update_recovery_strategy(
                    category="database",
                    strategy_update=strategy_update,
                    current_user=mock_current_user,
                )

            assert exc_info.value.status_code == 404
            assert "未找到错误类别" in exc_info.value.message


# ============================================================================
# Test: GET /circuit-breakers - Get Circuit Breaker Status
# ============================================================================


class TestGetCircuitBreakerStatus:
    """Tests for GET /api/v1/error-recovery/circuit-breakers endpoint"""

    @pytest.mark.asyncio
    async def test_get_circuit_breakers_success(
        self, mock_error_recovery_engine, mock_current_user
    ):
        """Test getting circuit breaker status successfully"""
        from src.api.v1.system.error_recovery import get_circuit_breaker_status

        with patch(
            "src.api.v1.system.error_recovery.error_recovery_engine",
            mock_error_recovery_engine,
        ):
            response = await get_circuit_breaker_status(current_user=mock_current_user)

            assert response["success"] is True
            result = response["data"]
            assert len(result) > 0
            assert all(hasattr(cb, "category") for cb in result)
            assert all(hasattr(cb, "state") for cb in result)
            assert all(hasattr(cb, "failure_count") for cb in result)

    @pytest.mark.asyncio
    async def test_get_circuit_breakers_closed_state(
        self, mock_error_recovery_engine, mock_current_user
    ):
        """Test circuit breaker in closed state"""
        from src.api.v1.system.error_recovery import get_circuit_breaker_status

        mock_error_recovery_engine.circuit_breakers["database"] = {
            "state": "closed",
            "failure_count": 0,
            "opened_at": None,
            "timeout": 60,
        }

        with patch(
            "src.api.v1.system.error_recovery.error_recovery_engine",
            mock_error_recovery_engine,
        ):
            response = await get_circuit_breaker_status(current_user=mock_current_user)

            assert response["success"] is True
            result = response["data"]
            database_cb = next(cb for cb in result if cb.category == "database")
            assert database_cb.state == "closed"
            assert database_cb.failure_count == 0
            assert database_cb.last_failure_time is None
            assert database_cb.next_retry_time is None

    @pytest.mark.asyncio
    async def test_get_circuit_breakers_open_state(
        self, mock_error_recovery_engine, mock_current_user
    ):
        """Test circuit breaker in open state"""
        from src.api.v1.system.error_recovery import get_circuit_breaker_status

        opened_time = datetime.now().timestamp()
        mock_error_recovery_engine.circuit_breakers["database"] = {
            "state": "open",
            "failure_count": 5,
            "opened_at": opened_time,
            "timeout": 60,
        }

        with patch(
            "src.api.v1.system.error_recovery.error_recovery_engine",
            mock_error_recovery_engine,
        ):
            response = await get_circuit_breaker_status(current_user=mock_current_user)

            assert response["success"] is True
            result = response["data"]
            database_cb = next(cb for cb in result if cb.category == "database")
            assert database_cb.state == "open"
            assert database_cb.failure_count == 5
            assert database_cb.last_failure_time is not None
            assert database_cb.next_retry_time is not None

    @pytest.mark.asyncio
    async def test_get_circuit_breakers_engine_error(self, mock_current_user):
        """Test getting circuit breakers when engine raises exception"""
        from src.api.v1.system.error_recovery import get_circuit_breaker_status

        mock_engine = MagicMock()
        # Accessing circuit_breakers.items() will raise the exception during iteration
        mock_engine.circuit_breakers.items.side_effect = Exception(
            "Circuit breaker error"
        )

        with patch("src.api.v1.system.error_recovery.error_recovery_engine", mock_engine):
            with pytest.raises(BaseBusinessError) as exc_info:
                await get_circuit_breaker_status(current_user=mock_current_user)

            assert exc_info.value.status_code == 500
            assert "获取熔断器状态失败" in exc_info.value.message


# ============================================================================
# Test: POST /circuit-breakers/{category}/reset - Reset Circuit Breaker
# ============================================================================


class TestResetCircuitBreaker:
    """Tests for POST /api/v1/error-recovery/circuit-breakers/{category}/reset endpoint"""

    @pytest.mark.asyncio
    async def test_reset_circuit_breaker_success(
        self, mock_error_recovery_engine, mock_current_user
    ):
        """Test resetting circuit breaker successfully"""
        from src.api.v1.system.error_recovery import reset_circuit_breaker

        # Set circuit breaker to open state
        mock_error_recovery_engine.circuit_breakers["database"] = {
            "state": "open",
            "failure_count": 5,
            "opened_at": datetime.now().timestamp(),
            "timeout": 60,
        }

        with patch(
            "src.api.v1.system.error_recovery.error_recovery_engine",
            mock_error_recovery_engine,
        ):
            response = await reset_circuit_breaker(
                category="database", current_user=mock_current_user
            )

            assert response["success"] is True
            result = response["data"]
            assert "已重置" in result["message"]
            assert (
                mock_error_recovery_engine.circuit_breakers["database"]["state"]
                == "closed"
            )
            assert (
                mock_error_recovery_engine.circuit_breakers["database"]["failure_count"]
                == 0
            )

    @pytest.mark.asyncio
    async def test_reset_circuit_breaker_invalid_category(
        self, mock_error_recovery_engine, mock_current_user
    ):
        """Test resetting circuit breaker with invalid category"""
        from src.api.v1.system.error_recovery import reset_circuit_breaker

        with patch(
            "src.api.v1.system.error_recovery.error_recovery_engine",
            mock_error_recovery_engine,
        ):
            with pytest.raises(BaseBusinessError) as exc_info:
                await reset_circuit_breaker(
                    category="invalid_category", current_user=mock_current_user
                )

            assert exc_info.value.status_code == 400
            assert "无效的错误类别" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_reset_circuit_breaker_nonexistent(
        self, mock_error_recovery_engine, mock_current_user
    ):
        """Test resetting circuit breaker that doesn't exist"""
        from src.api.v1.system.error_recovery import reset_circuit_breaker

        # Remove database circuit breaker
        del mock_error_recovery_engine.circuit_breakers["database"]

        with patch(
            "src.api.v1.system.error_recovery.error_recovery_engine",
            mock_error_recovery_engine,
        ):
            response = await reset_circuit_breaker(
                category="database", current_user=mock_current_user
            )

            assert response["success"] is True
            result = response["data"]
            assert "没有熔断器需要重置" in result["message"]

    @pytest.mark.asyncio
    async def test_reset_circuit_breaker_generic_exception(
        self, mock_error_recovery_engine, mock_current_user
    ):
        """Test resetting circuit breaker when a generic exception occurs"""
        from src.api.v1.system.error_recovery import reset_circuit_breaker

        # Make circuit_breakers[__setitem__] raise an exception
        mock_cb = MagicMock()
        mock_cb.__setitem__ = MagicMock(side_effect=Exception("Circuit breaker error"))
        mock_error_recovery_engine.circuit_breakers = {"database": mock_cb}

        with patch(
            "src.api.v1.system.error_recovery.error_recovery_engine",
            mock_error_recovery_engine,
        ):
            with pytest.raises(BaseBusinessError) as exc_info:
                await reset_circuit_breaker(
                    category="database", current_user=mock_current_user
                )

            assert exc_info.value.status_code == 500
            assert "重置熔断器失败" in exc_info.value.message


# ============================================================================
# Test: GET /history - Get Error Recovery History
# ============================================================================


class TestGetRecoveryHistory:
    """Tests for GET /api/v1/error-recovery/history endpoint"""

    @pytest.mark.asyncio
    async def test_get_history_success(
        self, mock_error_recovery_engine, mock_current_user
    ):
        """Test getting history successfully"""
        from src.api.v1.system.error_recovery import get_recovery_history

        with patch(
            "src.api.v1.system.error_recovery.error_recovery_engine",
            mock_error_recovery_engine,
        ):
            response = await get_recovery_history(
                category=None,
                success=None,
                limit=50,
                offset=0,
                current_user=mock_current_user,
            )

            assert response["success"] is True
            result = response["data"]
            assert "total" in result
            assert "offset" in result
            assert "limit" in result
            assert "records" in result
            assert result["total"] == 2
            assert len(result["records"]) == 2

    @pytest.mark.asyncio
    async def test_get_history_with_category_filter(
        self, mock_error_recovery_engine, mock_current_user
    ):
        """Test getting history with category filter"""
        from src.api.v1.system.error_recovery import get_recovery_history

        with patch(
            "src.api.v1.system.error_recovery.error_recovery_engine",
            mock_error_recovery_engine,
        ):
            response = await get_recovery_history(
                category="database",
                success=None,
                limit=50,
                offset=0,
                current_user=mock_current_user,
            )

            assert response["success"] is True
            result = response["data"]
            assert result["total"] == 1
            assert len(result["records"]) == 1
            assert result["records"][0]["category"] == "database"

    @pytest.mark.asyncio
    async def test_get_history_with_success_filter(
        self, mock_error_recovery_engine, mock_current_user
    ):
        """Test getting history with success filter"""
        from src.api.v1.system.error_recovery import get_recovery_history

        with patch(
            "src.api.v1.system.error_recovery.error_recovery_engine",
            mock_error_recovery_engine,
        ):
            response = await get_recovery_history(
                category=None,
                success=True,
                limit=50,
                offset=0,
                current_user=mock_current_user,
            )

            assert response["success"] is True
            result = response["data"]
            assert result["total"] == 1
            assert result["records"][0]["success"] is True

    @pytest.mark.asyncio
    async def test_get_history_with_pagination(
        self, mock_error_recovery_engine, mock_current_user
    ):
        """Test getting history with pagination"""
        from src.api.v1.system.error_recovery import get_recovery_history

        # Add more history records
        for i in range(10):
            mock_error_recovery_engine.recovery_history.append(
                {
                    "error_id": f"test_error_{i}",
                    "category": "database" if i % 2 == 0 else "network",
                    "success": i % 2 == 0,
                    "timestamp": datetime.now().isoformat(),
                    "attempts": i + 1,
                }
            )

        with patch(
            "src.api.v1.system.error_recovery.error_recovery_engine",
            mock_error_recovery_engine,
        ):
            response = await get_recovery_history(
                category=None,
                success=None,
                limit=5,
                offset=0,
                current_user=mock_current_user,
            )

            assert response["success"] is True
            result = response["data"]
            assert result["total"] == 12
            assert len(result["records"]) == 5
            assert result["limit"] == 5
            assert result["offset"] == 0

    @pytest.mark.asyncio
    async def test_get_history_with_offset(
        self, mock_error_recovery_engine, mock_current_user
    ):
        """Test getting history with offset"""
        from src.api.v1.system.error_recovery import get_recovery_history

        with patch(
            "src.api.v1.system.error_recovery.error_recovery_engine",
            mock_error_recovery_engine,
        ):
            response = await get_recovery_history(
                category=None,
                success=None,
                limit=50,
                offset=1,
                current_user=mock_current_user,
            )

            assert response["success"] is True
            result = response["data"]
            assert result["total"] == 2
            assert len(result["records"]) == 1
            assert result["offset"] == 1

    @pytest.mark.asyncio
    async def test_get_history_empty(
        self, mock_error_recovery_engine, mock_current_user
    ):
        """Test getting history when empty"""
        from src.api.v1.system.error_recovery import get_recovery_history

        mock_error_recovery_engine.recovery_history = []

        with patch(
            "src.api.v1.system.error_recovery.error_recovery_engine",
            mock_error_recovery_engine,
        ):
            response = await get_recovery_history(
                category=None,
                success=None,
                limit=50,
                offset=0,
                current_user=mock_current_user,
            )

            assert response["success"] is True
            result = response["data"]
            assert result["total"] == 0
            assert len(result["records"]) == 0


# ============================================================================
# Test: POST /test - Test Error Recovery
# ============================================================================


class TestErrorRecoveryTest:
    """Tests for POST /api/v1/error-recovery/test endpoint"""

    @pytest.mark.asyncio
    async def test_error_recovery_success(
        self, mock_error_recovery_engine, mock_current_user
    ):
        """Test successful error recovery"""
        from src.api.v1.system.error_recovery import test_error_recovery

        with patch(
            "src.api.v1.system.error_recovery.error_recovery_engine",
            mock_error_recovery_engine,
        ):
            response = await test_error_recovery(
                category="database", simulate_error=True, current_user=mock_current_user
            )

            assert response["success"] is True
            result = response["data"]
            assert "test_result" in result
            assert result["test_result"]["recovery_success"] is True
            assert result["test_result"]["attempts_made"] == 2
            assert result["test_result"]["total_time"] == 0.5

    @pytest.mark.asyncio
    async def test_error_recovery_without_simulation(
        self, mock_error_recovery_engine, mock_current_user
    ):
        """Test error recovery without simulating error"""
        from src.api.v1.system.error_recovery import test_error_recovery

        with patch(
            "src.api.v1.system.error_recovery.error_recovery_engine",
            mock_error_recovery_engine,
        ):
            response = await test_error_recovery(
                category="database",
                simulate_error=False,
                current_user=mock_current_user,
            )

            assert response["success"] is True
            result = response["data"]
            assert "test_result" in result
            assert result["test_result"]["recovery_success"] is True

    @pytest.mark.asyncio
    async def test_error_recovery_invalid_category(
        self, mock_error_recovery_engine, mock_current_user
    ):
        """Test error recovery with invalid category"""
        from src.api.v1.system.error_recovery import test_error_recovery

        with patch(
            "src.api.v1.system.error_recovery.error_recovery_engine",
            mock_error_recovery_engine,
        ):
            with pytest.raises(BaseBusinessError) as exc_info:
                await test_error_recovery(
                    category="invalid_category",
                    simulate_error=True,
                    current_user=mock_current_user,
                )

            assert exc_info.value.status_code == 400
            assert "无效的错误类别" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_error_recovery_failed_recovery(
        self, mock_error_recovery_engine, mock_current_user
    ):
        """Test error recovery when recovery fails"""
        from src.api.v1.system.error_recovery import test_error_recovery

        from src.services.error_recovery_service import RecoveryResult

        # Mock failed recovery
        mock_error_recovery_engine.recover_from_error = AsyncMock(
            return_value=RecoveryResult(
                success=False,
                attempts_made=3,
                total_time=1.5,
                strategy_used="database_strategy",
                recovery_actions=["retry", "retry", "retry"],
            )
        )

        with patch(
            "src.api.v1.system.error_recovery.error_recovery_engine",
            mock_error_recovery_engine,
        ):
            response = await test_error_recovery(
                category="database", simulate_error=True, current_user=mock_current_user
            )

            assert response["success"] is True
            result = response["data"]
            assert result["test_result"]["recovery_success"] is False
            assert result["test_result"]["attempts_made"] == 3

    @pytest.mark.asyncio
    async def test_error_recovery_with_simulate_error_true(
        self, mock_error_recovery_engine, mock_current_user
    ):
        """Test error recovery with simulate_error=True to cover the exception raising path"""
        from src.api.v1.system.error_recovery import test_error_recovery

        with patch(
            "src.api.v1.system.error_recovery.error_recovery_engine",
            mock_error_recovery_engine,
        ):
            # This should trigger the simulate_error=True branch
            response = await test_error_recovery(
                category="database", simulate_error=True, current_user=mock_current_user
            )

            assert response["success"] is True
            result = response["data"]
            assert "test_result" in result

    @pytest.mark.asyncio
    async def test_error_recovery_generic_exception(self, mock_current_user):
        """Test error recovery when a generic exception occurs"""
        from src.api.v1.system.error_recovery import test_error_recovery

        mock_engine = MagicMock()
        mock_engine.recover_from_error = AsyncMock(
            side_effect=Exception("Recovery error")
        )

        with patch("src.api.v1.system.error_recovery.error_recovery_engine", mock_engine):
            with pytest.raises(BaseBusinessError) as exc_info:
                await test_error_recovery(
                    category="database",
                    simulate_error=True,
                    current_user=mock_current_user,
                )

            assert exc_info.value.status_code == 500
            assert "测试失败" in exc_info.value.message


# ============================================================================
# Test: DELETE /history/clear - Clear Error Recovery History
# ============================================================================


class TestClearRecoveryHistory:
    """Tests for DELETE /api/v1/error-recovery/history/clear endpoint"""

    @pytest.mark.asyncio
    async def test_clear_all_history(
        self, mock_error_recovery_engine, mock_current_user
    ):
        """Test clearing all history"""
        from src.api.v1.system.error_recovery import clear_recovery_history

        initial_count = len(mock_error_recovery_engine.recovery_history)

        with patch(
            "src.api.v1.system.error_recovery.error_recovery_engine",
            mock_error_recovery_engine,
        ):
            response = await clear_recovery_history(
                before_time=None, current_user=mock_current_user
            )

            assert response["success"] is True
            result = response["data"]
            assert f"{initial_count} 条历史记录" in result["message"]
            assert len(mock_error_recovery_engine.recovery_history) == 0

    @pytest.mark.asyncio
    async def test_clear_history_with_time_filter(
        self, mock_error_recovery_engine, mock_current_user
    ):
        """Test clearing history with time filter"""
        from src.api.v1.system.error_recovery import clear_recovery_history

        # Add old and new records - make sure the difference in timestamps is clear
        old_time = datetime(2024, 1, 1, 12, 0, 0)
        # Use a time that's between old and new to clear only the old record
        middle_time = datetime(2024, 1, 1, 18, 0, 0)
        new_time = datetime(2024, 1, 2, 12, 0, 0)

        mock_error_recovery_engine.recovery_history = [
            {
                "error_id": "old_error",
                "category": "database",
                "success": True,
                "timestamp": old_time.isoformat(),
                "attempts": 1,
            },
            {
                "error_id": "new_error",
                "category": "network",
                "success": False,
                "timestamp": new_time.isoformat(),
                "attempts": 2,
            },
        ]

        with patch(
            "src.api.v1.system.error_recovery.error_recovery_engine",
            mock_error_recovery_engine,
        ):
            # Clear records before middle_time (this should clear old_error only)
            response = await clear_recovery_history(
                before_time=middle_time, current_user=mock_current_user
            )

            assert response["success"] is True
            result = response["data"]
            # Should clear 1 record (the old one)
            assert "1 条历史记录" in result["message"]
            assert len(mock_error_recovery_engine.recovery_history) == 1
            assert (
                mock_error_recovery_engine.recovery_history[0]["error_id"]
                == "new_error"
            )

    @pytest.mark.asyncio
    async def test_clear_empty_history(
        self, mock_error_recovery_engine, mock_current_user
    ):
        """Test clearing empty history"""
        from src.api.v1.system.error_recovery import clear_recovery_history

        mock_error_recovery_engine.recovery_history = []

        with patch(
            "src.api.v1.system.error_recovery.error_recovery_engine",
            mock_error_recovery_engine,
        ):
            response = await clear_recovery_history(
                before_time=None, current_user=mock_current_user
            )

            assert response["success"] is True
            result = response["data"]
            assert "0 条历史记录" in result["message"]


# ============================================================================
# Test: GET /health - Get Error Recovery System Health
# ============================================================================


class TestGetErrorRecoveryHealth:
    """Tests for GET /api/v1/error-recovery/health endpoint"""

    @patch("src.api.v1.system.error_recovery.error_recovery_engine")
    @pytest.mark.asyncio
    async def test_health_healthy(self, mock_engine):
        """Test health endpoint when system is healthy (90%+ success rate)"""
        from fastapi.responses import JSONResponse
        from src.api.v1.system.error_recovery import get_error_recovery_health

        mock_engine.get_recovery_statistics.return_value = {
            "total_recoveries": 100,
            "successful_recoveries": 90,
            "success_rate": 90.0,
            "average_attempts": 2.5,
            "average_time": 1.2,
            "by_category": {},
        }
        mock_engine.circuit_breakers = {
            "database": {"state": "closed"},
            "network": {"state": "closed"},
        }

        response = get_error_recovery_health()

        assert isinstance(response, JSONResponse)
        assert response.status_code == 200
        import json

        content = json.loads(response.body.decode())
        assert content["status"] == "healthy"

    @patch("src.api.v1.system.error_recovery.error_recovery_engine")
    @pytest.mark.asyncio
    async def test_health_degraded(self, mock_engine):
        """Test health endpoint when system is degraded (70-90% success rate)"""
        from fastapi.responses import JSONResponse
        from src.api.v1.system.error_recovery import get_error_recovery_health

        mock_engine.get_recovery_statistics.return_value = {
            "total_recoveries": 100,
            "successful_recoveries": 75,
            "success_rate": 75.0,
            "average_attempts": 2.5,
            "average_time": 1.2,
            "by_category": {},
        }
        mock_engine.circuit_breakers = {
            "database": {"state": "closed"},
            "network": {"state": "open"},
        }

        response = get_error_recovery_health()

        assert isinstance(response, JSONResponse)
        assert response.status_code == 200
        import json

        content = json.loads(response.body.decode())
        assert content["status"] == "degraded"

    @patch("src.api.v1.system.error_recovery.error_recovery_engine")
    @pytest.mark.asyncio
    async def test_health_unhealthy(self, mock_engine):
        """Test health endpoint when system is unhealthy (<70% success rate)"""
        from fastapi.responses import JSONResponse
        from src.api.v1.system.error_recovery import get_error_recovery_health

        mock_engine.get_recovery_statistics.return_value = {
            "total_recoveries": 100,
            "successful_recoveries": 50,
            "success_rate": 50.0,
            "average_attempts": 2.5,
            "average_time": 1.2,
            "by_category": {},
        }
        mock_engine.circuit_breakers = {
            "database": {"state": "open"},
            "network": {"state": "open"},
        }

        response = get_error_recovery_health()

        assert isinstance(response, JSONResponse)
        assert response.status_code == 503
        import json

        content = json.loads(response.body.decode())
        assert content["status"] == "unhealthy"

    @patch("src.api.v1.system.error_recovery.error_recovery_engine")
    @pytest.mark.asyncio
    async def test_health_error(self, mock_engine):
        """Test health endpoint when engine raises exception"""
        from fastapi.responses import JSONResponse
        from src.api.v1.system.error_recovery import get_error_recovery_health

        mock_engine.get_recovery_statistics.side_effect = Exception(
            "Health check error"
        )

        response = get_error_recovery_health()

        assert isinstance(response, JSONResponse)
        assert response.status_code == 500
        import json

        content = json.loads(response.body.decode())
        assert content["status"] == "error"

    @patch("src.api.v1.system.error_recovery.error_recovery_engine")
    @pytest.mark.asyncio
    async def test_health_active_circuit_breakers(self, mock_engine):
        """Test health endpoint counts active circuit breakers"""
        from fastapi.responses import JSONResponse
        from src.api.v1.system.error_recovery import get_error_recovery_health

        mock_engine.get_recovery_statistics.return_value = {
            "total_recoveries": 100,
            "successful_recoveries": 90,
            "success_rate": 90.0,
            "average_attempts": 2.5,
            "average_time": 1.2,
            "by_category": {},
        }
        # Multiple open circuit breakers
        mock_engine.circuit_breakers = {
            "database": {"state": "open"},
            "network": {"state": "open"},
            "validation": {"state": "closed"},
        }

        response = get_error_recovery_health()

        assert isinstance(response, JSONResponse)
        import json

        content = json.loads(response.body.decode())
        assert content["active_circuit_breakers"] == 2


# ============================================================================
# Test: Edge Cases and Validation
# ============================================================================


class TestErrorRecoveryEdgeCases:
    """Tests for edge cases and validation"""

    @pytest.mark.asyncio
    async def test_all_error_categories_valid(self, mock_current_user):
        """Test that all error categories are valid"""
        from src.api.v1.system.error_recovery import (
            RecoveryStrategyUpdate,
            update_recovery_strategy,
        )

        from src.services.error_recovery_service import ErrorCategory

        mock_engine = MagicMock()

        # Create mock strategies for all categories
        from src.services.error_recovery_service import RecoveryStrategy

        mock_engine.strategies = {}
        for category in ErrorCategory:
            mock_engine.strategies[category] = RecoveryStrategy(
                name=f"{category.value}_strategy",
                category=category,
                max_attempts=3,
                base_delay=1.0,
                max_delay=60.0,
                backoff_multiplier=2.0,
                auto_recovery=True,
                fallback_enabled=True,
                requires_manual_intervention=False,
            )

        with patch("src.api.v1.system.error_recovery.error_recovery_engine", mock_engine):
            for category in ErrorCategory:
                strategy_update = RecoveryStrategyUpdate(max_attempts=5)
                response = await update_recovery_strategy(
                    category=category.value,
                    strategy_update=strategy_update,
                    current_user=mock_current_user,
                )
                assert response["success"] is True

    @pytest.mark.asyncio
    async def test_strategy_validation_bounds(
        self, mock_error_recovery_engine, mock_current_user
    ):
        """Test strategy update with boundary values"""
        from src.api.v1.system.error_recovery import (
            RecoveryStrategyUpdate,
            update_recovery_strategy,
        )

        with patch(
            "src.api.v1.system.error_recovery.error_recovery_engine",
            mock_error_recovery_engine,
        ):
            # Test minimum and maximum allowed values
            strategy_update = RecoveryStrategyUpdate(
                max_attempts=10,  # Maximum allowed
                base_delay=0.1,  # Minimum allowed
                max_delay=300.0,  # Maximum allowed
                backoff_multiplier=5.0,  # Maximum allowed
            )

            response = await update_recovery_strategy(
                category="database",
                strategy_update=strategy_update,
                current_user=mock_current_user,
            )

            assert response["success"] is True

    @pytest.mark.asyncio
    async def test_pagination_edge_cases(
        self, mock_error_recovery_engine, mock_current_user
    ):
        """Test pagination edge cases"""
        from src.api.v1.system.error_recovery import get_recovery_history

        # Empty history
        mock_error_recovery_engine.recovery_history = []

        with patch(
            "src.api.v1.system.error_recovery.error_recovery_engine",
            mock_error_recovery_engine,
        ):
            response = await get_recovery_history(
                category=None,
                success=None,
                limit=1000,
                offset=0,
                current_user=mock_current_user,
            )

            assert response["success"] is True
            result = response["data"]
            assert result["total"] == 0
            assert result["offset"] == 0
            assert result["limit"] == 1000
            assert len(result["records"]) == 0

    @pytest.mark.asyncio
    async def test_time_filter_edge_cases(
        self, mock_error_recovery_engine, mock_current_user
    ):
        """Test time filter edge cases"""
        from src.api.v1.system.error_recovery import clear_recovery_history

        # History with specific timestamps
        mock_error_recovery_engine.recovery_history = [
            {
                "error_id": "error_1",
                "category": "database",
                "success": True,
                "timestamp": "2024-01-01T12:00:00",
                "attempts": 1,
            },
            {
                "error_id": "error_2",
                "category": "network",
                "success": True,
                "timestamp": "2024-01-02T12:00:00",
                "attempts": 2,
            },
        ]

        with patch(
            "src.api.v1.system.error_recovery.error_recovery_engine",
            mock_error_recovery_engine,
        ):
            # Clear before a time that's between the two records
            before_time = datetime(2024, 1, 1, 18, 0, 0)
            response = await clear_recovery_history(
                before_time=before_time, current_user=mock_current_user
            )

            assert response["success"] is True
            result = response["data"]
            assert "1 条历史记录" in result["message"]
            assert len(mock_error_recovery_engine.recovery_history) == 1
