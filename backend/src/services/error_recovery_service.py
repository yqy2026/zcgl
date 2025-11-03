#!/usr/bin/env python3
from typing import Any

"""
错误恢复服务
提供企业级的多层错误检测、自动重试和智能恢复策略
"""

import asyncio
import hashlib
import logging
import time
import traceback
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """错误严重程度"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """错误类别"""

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


@dataclass
class ErrorContext:
    """错误上下文"""

    error_id: str
    error_type: str
    error_message: str
    stack_trace: str
    severity: ErrorSeverity
    category: ErrorCategory
    timestamp: datetime
    user_id: str | None = None
    request_id: str | None = None
    session_id: str | None = None
    component: str | None = None
    operation: str | None = None
    additional_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class RecoveryStrategy:
    """恢复策略配置"""

    name: str
    category: ErrorCategory
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    retry_conditions: list[str] = field(default_factory=list)
    fallback_enabled: bool = True
    auto_recovery: bool = True
    requires_manual_intervention: bool = False


@dataclass
class RecoveryResult:
    """恢复结果"""

    success: bool
    attempts_made: int
    total_time: float
    strategy_used: str
    final_error: Exception | None = None
    recovery_actions: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)


class ErrorRecoveryEngine:
    """错误恢复引擎"""

    def __init__(self):
        self.strategies: dict[ErrorCategory, RecoveryStrategy] = {}
        self.recovery_history: list[dict[str, Any]] = []
        self.circuit_breakers: dict[str, dict[str, Any]] = {}
        self.metrics_collector = MetricsCollector()
        self._initialize_default_strategies()

    def _initialize_default_strategies(self):
        """初始化默认恢复策略"""

        # 网络错误恢复策略
        self.strategies[ErrorCategory.NETWORK] = RecoveryStrategy(
            name="网络错误恢复",
            category=ErrorCategory.NETWORK,
            max_attempts=3,
            base_delay=1.0,
            max_delay=30.0,
            backoff_multiplier=2.0,
            retry_conditions=["timeout", "connection_error", "dns_error", "http_error"],
            auto_recovery=True,
        )

        # 数据库错误恢复策略
        self.strategies[ErrorCategory.DATABASE] = RecoveryStrategy(
            name="数据库错误恢复",
            category=ErrorCategory.DATABASE,
            max_attempts=2,
            base_delay=0.5,
            max_delay=10.0,
            backoff_multiplier=1.5,
            retry_conditions=["connection_lost", "deadlock", "timeout"],
            fallback_enabled=True,
            auto_recovery=True,
        )

        # 验证错误恢复策略
        self.strategies[ErrorCategory.VALIDATION] = RecoveryStrategy(
            name="验证错误恢复",
            category=ErrorCategory.VALIDATION,
            max_attempts=1,
            base_delay=0.1,
            max_delay=1.0,
            backoff_multiplier=1.0,
            auto_recovery=True,
            fallback_enabled=False,
        )

        # 认证错误恢复策略
        self.strategies[ErrorCategory.AUTHENTICATION] = RecoveryStrategy(
            name="认证错误恢复",
            category=ErrorCategory.AUTHENTICATION,
            max_attempts=2,
            base_delay=0.5,
            max_delay=5.0,
            backoff_multiplier=1.5,
            retry_conditions=["token_expired", "invalid_token"],
            auto_recovery=True,
        )

        # 文件系统错误恢复策略
        self.strategies[ErrorCategory.FILE_SYSTEM] = RecoveryStrategy(
            name="文件系统错误恢复",
            category=ErrorCategory.FILE_SYSTEM,
            max_attempts=2,
            base_delay=0.5,
            max_delay=10.0,
            backoff_multiplier=2.0,
            retry_conditions=["file_not_found", "permission_denied", "disk_full"],
            fallback_enabled=True,
            auto_recovery=True,
        )

        # 外部API错误恢复策略
        self.strategies[ErrorCategory.EXTERNAL_API] = RecoveryStrategy(
            name="外部API错误恢复",
            category=ErrorCategory.EXTERNAL_API,
            max_attempts=3,
            base_delay=2.0,
            max_delay=60.0,
            backoff_multiplier=2.5,
            retry_conditions=["rate_limit", "service_unavailable", "timeout"],
            fallback_enabled=True,
            auto_recovery=True,
        )

    async def recover_from_error(
        self, error_context: ErrorContext, recovery_func: Callable, *args, **kwargs
    ) -> RecoveryResult:
        """从错误中恢复"""

        strategy = self.strategies.get(error_context.category)
        if not strategy:
            logger.warning(f"未找到错误类别的恢复策略: {error_context.category}")
            return RecoveryResult(
                success=False,
                attempts_made=0,
                total_time=0.0,
                strategy_used="none",
                final_error=Exception("未找到恢复策略"),
            )

        # 检查熔断器
        if self._is_circuit_breaker_open(error_context.category.value):
            logger.warning(f"熔断器开启，跳过恢复: {error_context.category}")
            return RecoveryResult(
                success=False,
                attempts_made=0,
                total_time=0.0,
                strategy_used=strategy.name,
                final_error=Exception("熔断器开启"),
            )

        return await self._execute_recovery_strategy(
            strategy, error_context, recovery_func, *args, **kwargs
        )

    async def _execute_recovery_strategy(
        self,
        strategy: RecoveryStrategy,
        error_context: ErrorContext,
        recovery_func: Callable,
        *args,
        **kwargs,
    ) -> RecoveryResult:
        """执行恢复策略"""

        start_time = time.time()
        recovery_actions = []
        last_exception = None

        logger.info(
            f"开始执行恢复策略: {strategy.name}, 最大尝试次数: {strategy.max_attempts}"
        )

        for attempt in range(strategy.max_attempts):
            try:
                # 计算延迟时间
                delay = self._calculate_delay(strategy, attempt)
                if attempt > 0 and delay > 0:
                    logger.info(f"第 {attempt + 1} 次尝试，延迟 {delay:.2f} 秒")
                    await asyncio.sleep(delay)

                # 执行恢复函数
                result = await self._attempt_recovery(
                    recovery_func, error_context, *args, **kwargs
                )

                if result.get("success", False):
                    total_time = time.time() - start_time
                    recovery_actions.append(f"第 {attempt + 1} 次尝试成功")

                    # 记录成功恢复
                    self._record_recovery_success(
                        error_context, strategy, attempt + 1, total_time
                    )

                    return RecoveryResult(
                        success=True,
                        attempts_made=attempt + 1,
                        total_time=total_time,
                        strategy_used=strategy.name,
                        recovery_actions=recovery_actions,
                        metrics=result.get("metrics", {}),
                    )

                last_exception = result.get("error")
                recovery_actions.append(
                    f"第 {attempt + 1} 次尝试失败: {str(last_exception)}"
                )

            except Exception as e:
                last_exception = e
                recovery_actions.append(f"第 {attempt + 1} 次尝试异常: {str(e)}")
                logger.error(f"恢复尝试 {attempt + 1} 失败: {e}")

        # 所有尝试都失败了
        total_time = time.time() - start_time
        recovery_actions.append("所有恢复尝试失败")

        # 记录失败恢复
        self._record_recovery_failure(error_context, strategy, last_exception)

        # 检查是否需要开启熔断器
        if self._should_open_circuit_breaker(error_context.category.value):
            self._open_circuit_breaker(error_context.category.value)

        return RecoveryResult(
            success=False,
            attempts_made=strategy.max_attempts,
            total_time=total_time,
            strategy_used=strategy.name,
            final_error=last_exception,
            recovery_actions=recovery_actions,
        )

    async def _attempt_recovery(
        self, recovery_func: Callable, error_context: ErrorContext, *args, **kwargs
    ) -> dict[str, Any]:
        """执行单次恢复尝试"""

        try:
            # 根据错误类型执行不同的恢复逻辑
            if error_context.category == ErrorCategory.VALIDATION:
                return await self._recover_validation_error(
                    recovery_func, error_context, *args, **kwargs
                )
            elif error_context.category == ErrorCategory.AUTHENTICATION:
                return await self._recover_authentication_error(
                    recovery_func, error_context, *args, **kwargs
                )
            elif error_context.category == ErrorCategory.DATABASE:
                return await self._recover_database_error(
                    recovery_func, error_context, *args, **kwargs
                )
            elif error_context.category == ErrorCategory.FILE_SYSTEM:
                return await self._recover_file_system_error(
                    recovery_func, error_context, *args, **kwargs
                )
            else:
                # 默认重试策略
                result = await recovery_func(*args, **kwargs)
                return {"success": True, "result": result}

        except Exception as e:
            return {"success": False, "error": e}

    async def _recover_validation_error(
        self, recovery_func: Callable, error_context: ErrorContext, *args, **kwargs
    ) -> dict[str, Any]:
        """验证错误恢复"""

        logger.info("执行验证错误恢复")

        # 尝试数据自动纠正
        if "data" in kwargs:
            corrected_data = await self._auto_correct_data(kwargs["data"])
            kwargs["data"] = corrected_data

            try:
                result = await recovery_func(*args, **kwargs)
                return {
                    "success": True,
                    "result": result,
                    "metrics": {
                        "auto_corrected": True,
                        "fields_corrected": len(corrected_data),
                    },
                }
            except Exception as e:
                return {"success": False, "error": e}

        return {"success": False, "error": Exception("数据纠正失败")}

    async def _recover_authentication_error(
        self, recovery_func: Callable, error_context: ErrorContext, *args, **kwargs
    ) -> dict[str, Any]:
        """认证错误恢复"""

        logger.info("执行认证错误恢复")

        # 尝试刷新token
        if "token_expired" in error_context.error_message.lower():
            try:
                # 这里应该调用token刷新服务
                refreshed_token = await self._refresh_authentication_token()
                if refreshed_token:
                    # 更新请求头
                    if "headers" in kwargs:
                        kwargs["headers"]["Authorization"] = f"Bearer {refreshed_token}"

                    result = await recovery_func(*args, **kwargs)
                    return {
                        "success": True,
                        "result": result,
                        "metrics": {"token_refreshed": True},
                    }
            except Exception as e:
                logger.error(f"Token刷新失败: {e}")

        return {"success": False, "error": Exception("认证恢复失败")}

    async def _recover_database_error(
        self, recovery_func: Callable, error_context: ErrorContext, *args, **kwargs
    ) -> dict[str, Any]:
        """数据库错误恢复"""

        logger.info("执行数据库错误恢复")

        # 尝试重新连接数据库
        try:
            # 这里应该调用数据库重连服务
            await self._reconnect_database()

            result = await recovery_func(*args, **kwargs)
            return {
                "success": True,
                "result": result,
                "metrics": {"database_reconnected": True},
            }
        except Exception:
            # 尝试使用备用数据库
            try:
                backup_connection = await self._connect_backup_database()
                if backup_connection:
                    kwargs["connection"] = backup_connection

                    result = await recovery_func(*args, **kwargs)
                    return {
                        "success": True,
                        "result": result,
                        "metrics": {"backup_database_used": True},
                    }
            except Exception as backup_e:
                logger.error(f"备用数据库连接失败: {backup_e}")

        return {"success": False, "error": Exception("数据库恢复失败")}

    async def _recover_file_system_error(
        self, recovery_func: Callable, error_context: ErrorContext, *args, **kwargs
    ) -> dict[str, Any]:
        """文件系统错误恢复"""

        logger.info("执行文件系统错误恢复")

        # 检查文件路径并尝试替代路径
        if "file_path" in kwargs:
            original_path = kwargs["file_path"]
            alternative_paths = [
                original_path,
                f"/tmp/{Path(original_path).name}",
                f"./backup/{Path(original_path).name}",
                f"../cache/{Path(original_path).name}",
            ]

            for alt_path in alternative_paths:
                try:
                    if Path(alt_path).exists():
                        kwargs["file_path"] = alt_path

                        result = await recovery_func(*args, **kwargs)
                        return {
                            "success": True,
                            "result": result,
                            "metrics": {"alternative_path_used": alt_path},
                        }
                except Exception:
                    continue

        return {"success": False, "error": Exception("文件系统恢复失败")}

    def _calculate_delay(self, strategy: RecoveryStrategy, attempt: int) -> float:
        """计算重试延迟"""
        if attempt == 0:
            return 0

        delay = strategy.base_delay * (strategy.backoff_multiplier**attempt)
        return min(delay, strategy.max_delay)

    def _is_circuit_breaker_open(self, category: str) -> bool:
        """检查熔断器是否开启"""
        breaker = self.circuit_breakers.get(category)
        if not breaker:
            return False

        if breaker["state"] == "open":
            # 检查是否可以进入半开状态
            if time.time() - breaker["opened_at"] > breaker["timeout"]:
                breaker["state"] = "half_open"
                return False
            return True

        return False

    def _should_open_circuit_breaker(self, category: str) -> bool:
        """判断是否应该开启熔断器"""
        recent_failures = [
            r
            for r in self.recovery_history[-10:]  # 最近10次记录
            if r["category"] == category and not r["success"]
        ]

        # 如果最近5次失败，开启熔断器
        return len(recent_failures) >= 5

    def _open_circuit_breaker(self, category: str):
        """开启熔断器"""
        if category not in self.circuit_breakers:
            self.circuit_breakers[category] = {}

        self.circuit_breakers[category].update(
            {
                "state": "open",
                "opened_at": time.time(),
                "timeout": 60,  # 60秒后尝试半开
            }
        )

        logger.warning(f"熔断器开启: {category}")

    def _record_recovery_success(
        self,
        error_context: ErrorContext,
        strategy: RecoveryStrategy,
        attempts: int,
        total_time: float,
    ):
        """记录成功恢复"""
        record = {
            "error_id": error_context.error_id,
            "category": error_context.category.value,
            "success": True,
            "strategy": strategy.name,
            "attempts": attempts,
            "total_time": total_time,
            "timestamp": datetime.now().isoformat(),
        }

        self.recovery_history.append(record)
        self.metrics_collector.record_recovery_success(
            error_context.category.value, attempts, total_time
        )

    def _record_recovery_failure(
        self, error_context: ErrorContext, strategy: RecoveryStrategy, error: Exception
    ):
        """记录失败恢复"""
        record = {
            "error_id": error_context.error_id,
            "category": error_context.category.value,
            "success": False,
            "strategy": strategy.name,
            "error_message": str(error),
            "timestamp": datetime.now().isoformat(),
        }

        self.recovery_history.append(record)
        self.metrics_collector.record_recovery_failure(error_context.category.value)

    # 辅助方法（这些方法需要根据实际项目实现）
    async def _auto_correct_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """自动纠正数据"""
        # 这里实现数据自动纠正逻辑
        return data

    async def _refresh_authentication_token(self) -> str | None:
        """刷新认证token"""
        # 这里实现token刷新逻辑
        return "refreshed_token"

    async def _reconnect_database(self):
        """重新连接数据库"""
        # 这里实现数据库重连逻辑
        pass

    async def _connect_backup_database(self):
        """连接备用数据库"""
        # 这里实现备用数据库连接逻辑
        return "backup_connection"

    def get_recovery_statistics(self) -> dict[str, Any]:
        """获取恢复统计信息"""
        if not self.recovery_history:
            return {
                "total_recoveries": 0,
                "success_rate": 0.0,
                "average_attempts": 0.0,
                "average_time": 0.0,
            }

        total = len(self.recovery_history)
        successful = sum(1 for r in self.recovery_history if r["success"])
        total_attempts = sum(r.get("attempts", 1) for r in self.recovery_history)
        total_time = sum(r.get("total_time", 0) for r in self.recovery_history)

        return {
            "total_recoveries": total,
            "successful_recoveries": successful,
            "success_rate": (successful / total) * 100,
            "average_attempts": total_attempts / total,
            "average_time": total_time / total,
            "by_category": self._get_category_statistics(),
        }

    def _get_category_statistics(self) -> dict[str, dict[str, Any]]:
        """获取按类别分组的统计信息"""
        stats = {}

        for category in ErrorCategory:
            category_history = [
                r for r in self.recovery_history if r["category"] == category.value
            ]

            if category_history:
                total = len(category_history)
                successful = sum(1 for r in category_history if r["success"])
                stats[category.value] = {
                    "total": total,
                    "successful": successful,
                    "success_rate": (successful / total) * 100,
                    "average_attempts": sum(
                        r.get("attempts", 1) for r in category_history
                    )
                    / total,
                }

        return stats


class MetricsCollector:
    """指标收集器"""

    def __init__(self):
        self.metrics = {
            "success_count": {},
            "failure_count": {},
            "total_attempts": {},
            "total_time": {},
        }

    def record_recovery_success(self, category: str, attempts: int, total_time: float):
        """记录恢复成功"""
        self.metrics["success_count"][category] = (
            self.metrics["success_count"].get(category, 0) + 1
        )
        self.metrics["total_attempts"][category] = (
            self.metrics["total_attempts"].get(category, 0) + attempts
        )
        self.metrics["total_time"][category] = (
            self.metrics["total_time"].get(category, 0) + total_time
        )

    def record_recovery_failure(self, category: str):
        """记录恢复失败"""
        self.metrics["failure_count"][category] = (
            self.metrics["failure_count"].get(category, 0) + 1
        )

    def get_metrics(self) -> dict[str, Any]:
        """获取指标"""
        return self.metrics.copy()


# 全局错误恢复引擎实例
error_recovery_engine = ErrorRecoveryEngine()


# 装饰器函数
def with_error_recovery(
    error_category: ErrorCategory, fallback_func: Callable | None = None
):
    """错误恢复装饰器"""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # 创建错误上下文
                error_context = ErrorContext(
                    error_id=hashlib.md5(f"{e}{time.time()}".encode()).hexdigest(),
                    error_type=type(e).__name__,
                    error_message=str(e),
                    stack_trace=traceback.format_exc(),
                    severity=ErrorSeverity.MEDIUM,
                    category=error_category,
                    timestamp=datetime.now(),
                    component=func.__name__,
                    operation="function_call",
                )

                # 尝试恢复
                recovery_result = await error_recovery_engine.recover_from_error(
                    error_context, func, *args, **kwargs
                )

                if recovery_result.success:
                    return recovery_result.metrics.get("result")
                elif fallback_func:
                    # 执行fallback函数
                    return await fallback_func(*args, **kwargs)
                else:
                    # 重新抛出异常
                    raise e

        return wrapper

    return decorator
