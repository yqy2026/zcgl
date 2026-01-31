#!/usr/bin/env python3
"""
错误恢复管理API
提供错误恢复策略管理、监控和统计功能
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Body, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ....core.exception_handler import (
    BaseBusinessError,
    InternalServerError,
    bad_request,
    internal_error,
    not_found,
)
from ....middleware.auth import require_permission
from ....middleware.error_recovery_middleware import api_error_recovery
from ....models.auth import User
from ....security.route_guards import debug_only, require_localhost
from ....services.error_recovery_service import (
    ErrorCategory,
    ErrorSeverity,
    error_recovery_engine,
)

router = APIRouter(prefix="/error-recovery", tags=["错误恢复"])


# Pydantic模型
class RecoveryStrategyUpdate(BaseModel):
    """恢复策略更新模型"""

    max_attempts: int | None = Field(None, ge=1, le=10, description="最大重试次数")
    base_delay: float | None = Field(None, ge=0.1, le=60.0, description="基础延迟时间")
    max_delay: float | None = Field(None, ge=1.0, le=300.0, description="最大延迟时间")
    backoff_multiplier: float | None = Field(
        None, ge=1.0, le=5.0, description="退避倍数"
    )
    auto_recovery: bool | None = Field(None, description="是否启用自动恢复")


# Error category constants (for documentation, actual enum is in error_recovery_service)
class ErrorCategoryConst:
    """错误类别常量"""

    NETWORK = "network"
    DATABASE = "database"
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    FILE_SYSTEM = "file_system"
    MEMORY = "memory"
    EXTERNAL_API = "external_api"
    PROCESSING = "processing"
    BUSINESS_LOGIC = "business_logic"
    SYSTEM = "system"


# Error severity constants (for documentation, actual enum is in error_recovery_service)
class ErrorSeverityConst:
    """错误严重程度常量"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorStatisticsResponse(BaseModel):
    """错误统计响应"""

    total_recoveries: int = Field(..., description="总恢复次数")
    successful_recoveries: int = Field(..., description="成功恢复次数")
    success_rate: float = Field(..., description="成功率(%)")
    average_attempts: float = Field(..., description="平均尝试次数")
    average_time: float = Field(..., description="平均恢复时间(秒)")
    by_category: dict[str, Any] = Field(..., description="按类别分组的统计")


class CircuitBreakerStatus(BaseModel):
    """熔断器状态"""

    category: str = Field(..., description="错误类别")
    state: str = Field(..., description="熔断器状态")
    failure_count: int = Field(..., description="失败次数")
    last_failure_time: datetime | None = Field(None, description="最后失败时间")
    next_retry_time: datetime | None = Field(None, description="下次重试时间")


class RecoveryConfigResponse(BaseModel):
    """恢复配置响应"""

    name: str = Field(..., description="策略名称")
    category: str = Field(..., description="错误类别")
    max_attempts: int = Field(..., description="最大重试次数")
    base_delay: float = Field(..., description="基础延迟时间")
    max_delay: float = Field(..., description="最大延迟时间")
    backoff_multiplier: float = Field(..., description="退避倍数")
    auto_recovery: bool = Field(..., description="是否启用自动恢复")
    fallback_enabled: bool = Field(..., description="是否启用fallback")
    requires_manual_intervention: bool = Field(..., description="是否需要人工干预")


# API路由


@router.get(
    "/statistics",
    summary="获取错误恢复统计信息",
    description="获取系统错误恢复的整体统计信息，包括成功率、平均尝试次数等",
    response_model=ErrorStatisticsResponse,
)
@api_error_recovery(ErrorCategory.DATABASE)
async def get_recovery_statistics(
    current_user: User = Depends(require_permission("system:error_recovery", "view")),
    category: str | None = Query(None, description="按错误类别筛选"),
    start_time: datetime | None = Query(None, description="开始时间"),
    end_time: datetime | None = Query(None, description="结束时间"),
) -> ErrorStatisticsResponse:
    """获取错误恢复统计信息"""

    try:
        statistics = error_recovery_engine.get_recovery_statistics()

        # 应用筛选条件
        if category:
            filtered_stats = {}
            if category in statistics.get("by_category", {}):
                filtered_stats[category] = statistics["by_category"][category]
            statistics["by_category"] = filtered_stats

        return ErrorStatisticsResponse(**statistics)

    except Exception as e:
        raise internal_error(f"获取统计信息失败: {str(e)}")


@router.get(
    "/strategies",
    summary="获取错误恢复策略配置",
    description="获取所有错误类别对应的恢复策略配置信息",
    response_model=list[RecoveryConfigResponse],
)
@api_error_recovery(ErrorCategory.DATABASE)
async def get_recovery_strategies(
    current_user: User = Depends(require_permission("system:error_recovery", "view")),
) -> list[RecoveryConfigResponse]:
    """获取错误恢复策略配置"""

    try:
        strategies = []

        for category in ErrorCategory:
            strategy = error_recovery_engine.strategies.get(category)
            if strategy:
                strategy_response = RecoveryConfigResponse(
                    name=strategy.name,
                    category=category.value,
                    max_attempts=strategy.max_attempts,
                    base_delay=strategy.base_delay,
                    max_delay=strategy.max_delay,
                    backoff_multiplier=strategy.backoff_multiplier,
                    auto_recovery=strategy.auto_recovery,
                    fallback_enabled=strategy.fallback_enabled,
                    requires_manual_intervention=strategy.requires_manual_intervention,
                )
                strategies.append(strategy_response)

        return strategies

    except Exception as e:
        raise internal_error(f"获取策略配置失败: {str(e)}")


@router.put(
    "/strategies/{category}",
    summary="更新错误恢复策略",
    description="更新指定错误类别的恢复策略配置",
)
@api_error_recovery(ErrorCategory.DATABASE)
async def update_recovery_strategy(
    category: str,
    strategy_update: RecoveryStrategyUpdate,
    current_user: User = Depends(require_permission("system:error_recovery", "edit")),
) -> dict[str, Any]:
    """更新错误恢复策略"""

    try:
        # 验证错误类别
        error_category = None
        for ec in ErrorCategory:
            if ec.value == category:
                error_category = ec
                break

        if not error_category:
            raise bad_request(f"无效的错误类别: {category}")

        # 获取现有策略
        existing_strategy = error_recovery_engine.strategies.get(error_category)
        if not existing_strategy:
            raise not_found(
                f"未找到错误类别 {category} 的策略", resource_type="recovery_strategy"
            )

        # 更新策略配置
        if strategy_update.max_attempts is not None:
            existing_strategy.max_attempts = strategy_update.max_attempts
        if strategy_update.base_delay is not None:
            existing_strategy.base_delay = strategy_update.base_delay
        if strategy_update.max_delay is not None:
            existing_strategy.max_delay = strategy_update.max_delay
        if strategy_update.backoff_multiplier is not None:
            existing_strategy.backoff_multiplier = strategy_update.backoff_multiplier
        if strategy_update.auto_recovery is not None:
            existing_strategy.auto_recovery = strategy_update.auto_recovery

        return {
            "success": True,
            "message": f"错误类别 {category} 的恢复策略已更新",
            "updated_strategy": {
                "name": existing_strategy.name,
                "category": category,
                "max_attempts": existing_strategy.max_attempts,
                "base_delay": existing_strategy.base_delay,
                "max_delay": existing_strategy.max_delay,
                "backoff_multiplier": existing_strategy.backoff_multiplier,
                "auto_recovery": existing_strategy.auto_recovery,
            },
        }

    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"更新策略失败: {str(e)}")


@router.get(
    "/circuit-breakers",
    summary="获取熔断器状态",
    description="获取所有错误类别的熔断器当前状态",
    response_model=list[CircuitBreakerStatus],
)
@api_error_recovery(ErrorCategory.DATABASE)
async def get_circuit_breaker_status(
    current_user: User = Depends(require_permission("system:error_recovery", "view")),
) -> list[CircuitBreakerStatus]:
    """获取熔断器状态"""

    try:
        circuit_breakers = []

        for category, breaker in error_recovery_engine.circuit_breakers.items():
            status = CircuitBreakerStatus(
                category=category,
                state=breaker["state"],
                failure_count=breaker.get("failure_count", 0),
                last_failure_time=datetime.fromtimestamp(breaker.get("opened_at", 0))
                if breaker.get("opened_at")
                else None,
                next_retry_time=datetime.fromtimestamp(
                    breaker.get("opened_at", 0) + breaker.get("timeout", 60)
                )
                if breaker.get("opened_at")
                else None,
            )
            circuit_breakers.append(status)

        return circuit_breakers

    except Exception as e:
        raise internal_error(f"获取熔断器状态失败: {str(e)}")


@router.post(
    "/circuit-breakers/{category}/reset",
    summary="重置熔断器",
    description="重置指定错误类别的熔断器状态",
)
@api_error_recovery(ErrorCategory.DATABASE)
async def reset_circuit_breaker(
    category: str,
    current_user: User = Depends(require_permission("system:error_recovery", "edit")),
) -> dict[str, Any]:
    """重置熔断器"""

    try:
        # 验证错误类别
        error_category = None
        for ec in ErrorCategory:
            if ec.value == category:
                error_category = ec
                break

        if not error_category:
            raise bad_request(f"无效的错误类别: {category}")

        # 重置熔断器
        if category in error_recovery_engine.circuit_breakers:
            error_recovery_engine.circuit_breakers[category]["state"] = "closed"
            error_recovery_engine.circuit_breakers[category]["failure_count"] = 0

            return {"success": True, "message": f"错误类别 {category} 的熔断器已重置"}
        else:
            return {
                "success": True,
                "message": f"错误类别 {category} 没有熔断器需要重置",
            }

    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"重置熔断器失败: {str(e)}")


@router.get(
    "/history",
    summary="获取错误恢复历史",
    description="获取错误恢复的历史记录，支持分页和筛选",
)
@api_error_recovery(ErrorCategory.DATABASE)
async def get_recovery_history(
    current_user: User = Depends(require_permission("system:error_recovery", "view")),
    category: str | None = Query(None, description="按错误类别筛选"),
    success: bool | None = Query(None, description="按是否成功筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=1000, description="每页记录数"),
) -> dict[str, Any]:
    """获取错误恢复历史"""

    try:
        # 获取历史记录
        history = error_recovery_engine.recovery_history

        # 应用筛选条件
        if category:
            history = [h for h in history if h.get("category") == category]

        if success is not None:
            history = [h for h in history if h.get("success") == success]

        # 分页
        total = len(history)
        offset = (page - 1) * page_size
        history_page = history[offset : offset + page_size]

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "records": history_page,
        }

    except Exception as e:
        raise internal_error(f"获取历史记录失败: {str(e)}")


@router.post(
    "/test",
    summary="测试错误恢复",
    description="手动触发错误恢复测试，验证恢复策略的有效性",
    dependencies=[Depends(require_localhost)],
)
@api_error_recovery(ErrorCategory.DATABASE)
@debug_only
async def test_error_recovery(
    category: str = Body(..., description="错误类别"),
    simulate_error: bool = Body(True, description="是否模拟错误"),
    current_user: User = Depends(require_permission("system:error_recovery", "test")),
) -> dict[str, Any]:
    """测试错误恢复"""

    try:
        # 验证错误类别
        error_category = None
        for ec in ErrorCategory:
            if ec.value == category:
                error_category = ec
                break

        if not error_category:
            raise bad_request(f"无效的错误类别: {category}")

        # 执行测试
        async def test_function() -> dict[str, str]:
            if simulate_error:
                raise InternalServerError(message=f"模拟 {category} 错误")
            return {"test": "success"}

        from ....services.error_recovery_service import ErrorContext

        error_context = ErrorContext(
            error_id="test_" + str(int(datetime.now().timestamp())),
            error_type="TestException",
            error_message=f"模拟 {category} 错误",
            stack_trace="Test stack trace",
            severity=ErrorSeverity.MEDIUM,
            category=error_category,
            timestamp=datetime.now(),
            operation="test_recovery",
        )

        recovery_result = await error_recovery_engine.recover_from_error(
            error_context, test_function
        )

        return {
            "success": True,
            "message": "错误恢复测试完成",
            "test_result": {
                "recovery_success": recovery_result.success,
                "attempts_made": recovery_result.attempts_made,
                "total_time": recovery_result.total_time,
                "strategy_used": recovery_result.strategy_used,
                "recovery_actions": recovery_result.recovery_actions,
            },
        }

    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"测试失败: {str(e)}")


@router.delete(
    "/history/clear",
    summary="清理错误恢复历史",
    description="清理指定时间之前的错误恢复历史记录",
)
@api_error_recovery(ErrorCategory.DATABASE)
async def clear_recovery_history(
    current_user: User = Depends(require_permission("system:error_recovery", "edit")),
    before_time: datetime | None = Query(None, description="清理此时间之前的记录"),
) -> dict[str, Any]:
    """清理错误恢复历史"""

    try:
        if before_time:
            # 清理指定时间之前的记录
            before_timestamp = before_time.timestamp()
            original_count = len(error_recovery_engine.recovery_history)

            error_recovery_engine.recovery_history = [
                h
                for h in error_recovery_engine.recovery_history
                if datetime.fromisoformat(h["timestamp"]).timestamp() > before_timestamp
            ]

            cleared_count = original_count - len(error_recovery_engine.recovery_history)
        else:
            # 清理所有历史记录
            cleared_count = len(error_recovery_engine.recovery_history)
            error_recovery_engine.recovery_history = []

        return {"success": True, "message": f"已清理 {cleared_count} 条历史记录"}

    except Exception as e:
        raise internal_error(f"清理历史记录失败: {str(e)}")


@router.get(
    "/health",
    summary="获取错误恢复系统健康状态",
    description="检查错误恢复系统的整体健康状态",
)
def get_error_recovery_health() -> JSONResponse:
    """获取错误恢复系统健康状态"""

    try:
        statistics = error_recovery_engine.get_recovery_statistics()
        success_rate = statistics.get("success_rate", 0)

        # 健康状态判断
        if success_rate >= 90:
            health_status = "healthy"
            status_code = 200
        elif success_rate >= 70:
            health_status = "degraded"
            status_code = 200
        else:
            health_status = "unhealthy"
            status_code = 503

        content = {
            "status": health_status,
            "success_rate": success_rate,
            "total_recoveries": statistics.get("total_recoveries", 0),
            "active_circuit_breakers": len(
                [
                    cb
                    for cb in error_recovery_engine.circuit_breakers.values()
                    if cb.get("state") == "open"
                ]
            ),
            "timestamp": datetime.now().isoformat(),
        }
        return JSONResponse(content=content, status_code=status_code)

    except Exception as e:
        content = {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }
        return JSONResponse(content=content, status_code=500)
