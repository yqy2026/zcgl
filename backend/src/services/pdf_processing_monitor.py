from typing import Any
"""
PDF处理性能监控和错误处理系统
提供全面的性能指标收集、错误分析和系统健康监控
"""

import asyncio
import logging
import threading
import time
import traceback
from collections import defaultdict, deque
from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum


import psutil

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """错误严重程度"""

    LOW = "low"  # 轻微错误，不影响核心功能
    MEDIUM = "medium"  # 中等错误，影响部分功能
    HIGH = "high"  # 严重错误，影响核心功能
    CRITICAL = "critical"  # 致命错误，系统不可用


class PerformanceLevel(Enum):
    """性能等级"""

    EXCELLENT = "excellent"  # 优秀 (< 5秒)
    GOOD = "good"  # 良好 (5-15秒)
    ACCEPTABLE = "acceptable"  # 可接受 (15-30秒)
    POOR = "poor"  # 较差 (30-60秒)
    VERY_POOR = "very_poor"  # 很差 (> 60秒)


@dataclass
class ErrorRecord:
    """错误记录"""

    timestamp: datetime
    error_type: str
    severity: ErrorSeverity
    message: str
    traceback: str
    session_id: str | None = None
    file_name: str | None = None
    processing_step: str | None = None
    context: dict[str, Any] = field(default_factory=dict)
    resolved: bool = False
    resolution_time: datetime | None = None


@dataclass
class PerformanceMetric:
    """性能指标"""

    timestamp: datetime
    operation_type: str
    duration: float
    success: bool
    file_size: int | None = None
    file_pages: int | None = None
    processing_method: str | None = None
    session_id: str | None = None
    memory_usage: float | None = None
    cpu_usage: float | None = None
    error_type: str | None = None


@dataclass
class SystemHealth:
    """系统健康状态"""

    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    active_sessions: int
    error_rate: float
    avg_processing_time: float
    success_rate: float
    status: str  # healthy, warning, critical


class PDFProcessingMonitor:
    """PDF处理监控器"""

    def __init__(self, max_records: int = 1000):
        self.max_records = max_records
        self.error_records: deque = deque(maxlen=max_records)
        self.performance_metrics: deque = deque(maxlen=max_records)
        self.active_operations: dict[str, datetime] = {}
        self.error_handlers: dict[str, Callable] = {}
        self.performance_thresholds = self._load_performance_thresholds()
        self.alert_thresholds = self._load_alert_thresholds()
        self._monitoring_active = False
        self._monitoring_thread: threading.Thread | None = None

    def _load_performance_thresholds(self) -> dict[str, Any][str, dict[str, float]]:
        """加载性能阈值"""
        return {
            "pdf_processing": {
                "excellent": 5.0,
                "good": 15.0,
                "acceptable": 30.0,
                "poor": 60.0,
            },
            "ocr_processing": {
                "excellent": 10.0,
                "good": 30.0,
                "acceptable": 60.0,
                "poor": 120.0,
            },
            "text_extraction": {
                "excellent": 3.0,
                "good": 10.0,
                "acceptable": 20.0,
                "poor": 40.0,
            },
            "field_extraction": {
                "excellent": 2.0,
                "good": 5.0,
                "acceptable": 15.0,
                "poor": 30.0,
            },
        }

    def _load_alert_thresholds(self) -> dict[str, Any][str, float]:
        """加载告警阈值"""
        return {
            "error_rate": 0.1,  # 10%错误率
            "avg_processing_time": 45.0,  # 45秒平均处理时间
            "cpu_usage": 80.0,  # 80% CPU使用率
            "memory_usage": 85.0,  # 85% 内存使用率
            "active_sessions": 10,  # 10个活跃会话
            "disk_usage": 90.0,  # 90% 磁盘使用率
        }

    def start_monitoring(self):
        """启动监控"""
        if self._monitoring_active:
            return

        self._monitoring_active = True
        self._monitoring_thread = threading.Thread(
            target=self._monitoring_loop, daemon=True
        )
        self._monitoring_thread.start()
        logger.info("PDF处理监控已启动")

    def stop_monitoring(self):
        """停止监控"""
        self._monitoring_active = False
        if self._monitoring_thread:
            self._monitoring_thread.join(timeout=5)
        logger.info("PDF处理监控已停止")

    def _monitoring_loop(self):
        """监控循环"""
        while self._monitoring_active:
            try:
                # 检查系统健康状态
                health = self._collect_system_health()

                # 检查告警条件
                self._check_alerts(health)

                # 清理过期记录
                self._cleanup_old_records()

                time.sleep(30)  # 30秒检查一次

            except Exception as e:
                logger.error(f"监控循环错误: {str(e)}")
                time.sleep(60)  # 出错后等待更长时间

    def _collect_system_health(self) -> SystemHealth:
        """收集系统健康状态"""
        try:
            # 系统资源使用情况
            cpu_usage = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            # 计算统计指标
            recent_metrics = [
                m
                for m in self.performance_metrics
                if m.timestamp > datetime.now() - timedelta(hours=1)
            ]

            active_sessions = len(self.active_operations)
            error_rate = self._calculate_error_rate(recent_metrics)
            avg_processing_time = self._calculate_avg_processing_time(recent_metrics)
            success_rate = self._calculate_success_rate(recent_metrics)

            # 确定系统状态
            status = self._determine_system_status(
                cpu_usage,
                memory.percent,
                disk.percent,
                error_rate,
                avg_processing_time,
                active_sessions,
            )

            return SystemHealth(
                timestamp=datetime.now(),
                cpu_usage=cpu_usage,
                memory_usage=memory.percent,
                disk_usage=disk.percent,
                active_sessions=active_sessions,
                error_rate=error_rate,
                avg_processing_time=avg_processing_time,
                success_rate=success_rate,
                status=status,
            )

        except Exception as e:
            logger.error(f"系统健康状态收集失败: {str(e)}")
            return SystemHealth(
                timestamp=datetime.now(),
                cpu_usage=0.0,
                memory_usage=0.0,
                disk_usage=0.0,
                active_sessions=0,
                error_rate=0.0,
                avg_processing_time=0.0,
                success_rate=0.0,
                status="error",
            )

    def _determine_system_status(
        self,
        cpu: float,
        memory: float,
        disk: float,
        error_rate: float,
        avg_time: float,
        sessions: int,
    ) -> str:
        """确定系统状态"""
        # 检查关键指标
        if cpu > 95 or memory > 95 or disk > 95 or error_rate > 0.5 or sessions > 20:
            return "critical"

        if (
            cpu > 80
            or memory > 85
            or disk > 90
            or error_rate > 0.2
            or avg_time > 120
            or sessions > 15
        ):
            return "warning"

        return "healthy"

    def _check_alerts(self, health: SystemHealth):
        """检查告警条件"""
        alerts = []

        if health.cpu_usage > self.alert_thresholds["cpu_usage"]:
            alerts.append(f"CPU使用率过高: {health.cpu_usage:.1f}%")

        if health.memory_usage > self.alert_thresholds["memory_usage"]:
            alerts.append(f"内存使用率过高: {health.memory_usage:.1f}%")

        if health.disk_usage > self.alert_thresholds["disk_usage"]:
            alerts.append(f"磁盘使用率过高: {health.disk_usage:.1f}%")

        if health.error_rate > self.alert_thresholds["error_rate"]:
            alerts.append(f"错误率过高: {health.error_rate:.1%}")

        if health.avg_processing_time > self.alert_thresholds["avg_processing_time"]:
            alerts.append(f"平均处理时间过长: {health.avg_processing_time:.1f}秒")

        if health.active_sessions > self.alert_thresholds["active_sessions"]:
            alerts.append(f"活跃会话数过多: {health.active_sessions}")

        # 发送告警
        for alert in alerts:
            self._send_alert(alert, health.status)

    def _send_alert(self, message: str, severity: str):
        """发送告警"""
        logger.warning(f"系统告警 [{severity}]: {message}")
        # 这里可以集成邮件、短信、Slack等告警方式

    def _cleanup_old_records(self):
        """清理过期记录"""
        cutoff_time = datetime.now() - timedelta(days=7)

        # 清理错误记录
        self.error_records = deque(
            (record for record in self.error_records if record.timestamp > cutoff_time),
            maxlen=self.max_records,
        )

        # 清理性能指标
        self.performance_metrics = deque(
            (
                metric
                for metric in self.performance_metrics
                if metric.timestamp > cutoff_time
            ),
            maxlen=self.max_records,
        )

    def record_operation_start(self, operation_id: str):
        """记录操作开始"""
        self.active_operations[operation_id] = datetime.now()

    def record_operation_end(
        self,
        operation_id: str,
        operation_type: str,
        success: bool,
        file_size: int | None = None,
        file_pages: int | None = None,
        processing_method: str | None = None,
        error_type: str | None = None,
    ):
        """记录操作结束"""
        start_time = self.active_operations.pop(operation_id, None)
        if start_time is None:
            return

        duration = (datetime.now() - start_time).total_seconds()

        # 获取系统资源使用情况
        memory_usage = psutil.virtual_memory().percent
        cpu_usage = psutil.cpu_percent()

        metric = PerformanceMetric(
            timestamp=datetime.now(),
            operation_type=operation_type,
            duration=duration,
            success=success,
            file_size=file_size,
            file_pages=file_pages,
            processing_method=processing_method,
            session_id=operation_id,
            memory_usage=memory_usage,
            cpu_usage=cpu_usage,
            error_type=error_type,
        )

        self.performance_metrics.append(metric)

        # 如果操作失败，记录错误
        if not success and error_type:
            self.record_error(
                error_type,
                "MEDIUM",
                f"操作失败: {operation_type}",
                session_id=operation_id,
                processing_step=operation_type,
            )

    def record_error(
        self,
        error_type: str,
        severity: ErrorSeverity,
        message: str,
        session_id: str | None = None,
        file_name: str | None = None,
        processing_step: str | None = None,
        context: dict[str, Any] | None = None,
    ):
        """记录错误"""
        error_record = ErrorRecord(
            timestamp=datetime.now(),
            error_type=error_type,
            severity=severity,
            message=message,
            traceback=traceback.format_exc(),
            session_id=session_id,
            file_name=file_name,
            processing_step=processing_step,
            context=context or {},
        )

        self.error_records.append(error_record)

        # 尝试自动处理错误
        self._handle_error(error_record)

    def _handle_error(self, error_record: ErrorRecord):
        """处理错误"""
        handler = self.error_handlers.get(error_record.error_type)
        if handler:
            try:
                # 异步调用错误处理器
                asyncio.create_task(self._async_error_handler(handler, error_record))
            except Exception as e:
                logger.error(f"错误处理器执行失败: {str(e)}")

    async def _async_error_handler(self, handler: Callable, error_record: ErrorRecord):
        """异步错误处理器"""
        try:
            result = await handler(error_record)
            if result:
                error_record.resolved = True
                error_record.resolution_time = datetime.now()
                logger.info(f"错误已自动处理: {error_record.error_type}")
        except Exception as e:
            logger.error(f"错误处理失败: {str(e)}")

    def register_error_handler(self, error_type: str, handler: Callable):
        """注册错误处理器"""
        self.error_handlers[error_type] = handler

    @asynccontextmanager
    async def monitor_operation(
        self,
        operation_type: str,
        session_id: str | None = None,
        file_size: int | None = None,
        file_pages: int | None = None,
        processing_method: str | None = None,
    ):
        """操作监控上下文管理器"""
        operation_id = session_id or f"{operation_type}_{int(time.time())}"

        # 记录操作开始
        self.record_operation_start(operation_id)

        try:
            yield operation_id
            success = True
            error_type = None
        except Exception as e:
            success = False
            error_type = type(e).__name__

            # 记录错误
            severity = self._determine_error_severity(e, operation_type)
            self.record_error(
                error_type=error_type,
                severity=severity,
                message=str(e),
                session_id=session_id,
                processing_step=operation_type,
            )

            raise
        finally:
            # 记录操作结束
            self.record_operation_end(
                operation_id=operation_id,
                operation_type=operation_type,
                success=success,
                file_size=file_size,
                file_pages=file_pages,
                processing_method=processing_method,
                error_type=error_type,
            )

    def _determine_error_severity(
        self, error: Exception, operation_type: str
    ) -> ErrorSeverity:
        """确定错误严重程度"""
        error_message = str(error).lower()

        # 系统级错误
        if any(
            keyword in error_message
            for keyword in ["memory", "disk", "system", "crash"]
        ):
            return ErrorSeverity.CRITICAL

        # 网络相关错误
        if any(
            keyword in error_message for keyword in ["timeout", "connection", "network"]
        ):
            return ErrorSeverity.MEDIUM

        # 文件相关错误
        if any(
            keyword in error_message
            for keyword in ["file not found", "permission", "corrupt"]
        ):
            return ErrorSeverity.HIGH

        # 默认为中等错误
        return ErrorSeverity.MEDIUM

    def get_performance_stats(self, hours: int = 24) -> dict[str, Any]:
        """获取性能统计"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_metrics = [
            m for m in self.performance_metrics if m.timestamp > cutoff_time
        ]

        if not recent_metrics:
            return {
                "total_operations": 0,
                "success_rate": 0.0,
                "avg_processing_time": 0.0,
                "performance_level": "no_data",
            }

        # 基础统计
        total_operations = len(recent_metrics)
        successful_operations = sum(1 for m in recent_metrics if m.success)
        success_rate = (
            successful_operations / total_operations if total_operations > 0 else 0
        )

        # 时间统计
        durations = [m.duration for m in recent_metrics]
        avg_processing_time = sum(durations) / len(durations) if durations else 0
        min_time = min(durations) if durations else 0
        max_time = max(durations) if durations else 0

        # 性能等级
        performance_level = self._determine_performance_level(avg_processing_time)

        # 按操作类型分组统计
        stats_by_type = defaultdict(list)
        for metric in recent_metrics:
            stats_by_type[metric.operation_type].append(metric)

        type_stats = {}
        for op_type, metrics in stats_by_type.items():
            type_durations = [m.duration for m in metrics]
            type_success_rate = (
                sum(1 for m in metrics if m.success) / len(metrics) if metrics else 0
            )

            type_stats[op_type] = {
                "count": len(metrics),
                "success_rate": type_success_rate,
                "avg_duration": sum(type_durations) / len(type_durations)
                if type_durations
                else 0,
                "min_duration": min(type_durations) if type_durations else 0,
                "max_duration": max(type_durations) if type_durations else 0,
            }

        return {
            "total_operations": total_operations,
            "success_rate": success_rate,
            "avg_processing_time": avg_processing_time,
            "min_processing_time": min_time,
            "max_processing_time": max_time,
            "performance_level": performance_level.value,
            "stats_by_type": type_stats,
            "period_hours": hours,
        }

    def _determine_performance_level(self, avg_time: float) -> PerformanceLevel:
        """确定性能等级"""
        if avg_time < 5:
            return PerformanceLevel.EXCELLENT
        elif avg_time < 15:
            return PerformanceLevel.GOOD
        elif avg_time < 30:
            return PerformanceLevel.ACCEPTABLE
        elif avg_time < 60:
            return PerformanceLevel.POOR
        else:
            return PerformanceLevel.VERY_POOR

    def get_error_stats(self, hours: int = 24) -> dict[str, Any]:
        """获取错误统计"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_errors = [e for e in self.error_records if e.timestamp > cutoff_time]

        if not recent_errors:
            return {
                "total_errors": 0,
                "error_rate": 0.0,
                "errors_by_type": {},
                "errors_by_severity": {},
                "resolved_errors": 0,
            }

        # 错误统计
        total_errors = len(recent_errors)
        resolved_errors = sum(1 for e in recent_errors if e.resolved)

        # 按类型分组
        errors_by_type = defaultdict(int)
        errors_by_severity = defaultdict(int)

        for error in recent_errors:
            errors_by_type[error.error_type] += 1
            errors_by_severity[error.severity.value] += 1

        # 错误率计算
        total_operations = len(
            [m for m in self.performance_metrics if m.timestamp > cutoff_time]
        )
        error_rate = total_errors / total_operations if total_operations > 0 else 0

        return {
            "total_errors": total_errors,
            "resolved_errors": resolved_errors,
            "error_rate": error_rate,
            "errors_by_type": dict(errors_by_type),
            "errors_by_severity": dict(errors_by_severity),
            "period_hours": hours,
        }

    def get_system_health(self) -> SystemHealth:
        """获取系统健康状态"""
        return self._collect_system_health()

    def _calculate_error_rate(self, metrics: list[PerformanceMetric]) -> float:
        """计算错误率"""
        if not metrics:
            return 0.0
        failed_operations = sum(1 for m in metrics if not m.success)
        return failed_operations / len(metrics)

    def _calculate_avg_processing_time(self, metrics: list[PerformanceMetric]) -> float:
        """计算平均处理时间"""
        if not metrics:
            return 0.0
        durations = [m.duration for m in metrics]
        return sum(durations) / len(durations)

    def _calculate_success_rate(self, metrics: list[PerformanceMetric]) -> float:
        """计算成功率"""
        if not metrics:
            return 0.0
        successful_operations = sum(1 for m in metrics if m.success)
        return successful_operations / len(metrics)

    def get_recommendations(self) -> list[str]:
        """获取优化建议"""
        recommendations = []

        # 性能分析
        perf_stats = self.get_performance_stats(1)  # 最近1小时
        error_stats = self.get_error_stats(1)

        # 性能建议
        if perf_stats["avg_processing_time"] > 30:
            recommendations.append("平均处理时间较长，建议优化处理算法或增加硬件资源")

        if perf_stats["success_rate"] < 0.9:
            recommendations.append("成功率偏低，建议检查错误日志并改进错误处理")

        # 错误分析建议
        if error_stats["error_rate"] > 0.1:
            recommendations.append("错误率较高，建议分析常见错误原因并改进系统稳定性")

        # 常见错误类型建议
        errors_by_type = error_stats.get("errors_by_type", {})
        if "MemoryError" in errors_by_type or "memory" in str(errors_by_type).lower():
            recommendations.append("检测到内存相关错误，建议优化内存使用或增加内存")

        if "timeout" in str(errors_by_type).lower():
            recommendations.append("检测到超时错误，建议优化处理性能或调整超时设置")

        # 系统资源建议
        health = self.get_system_health()
        if health.cpu_usage > 80:
            recommendations.append("CPU使用率较高，建议优化算法或增加CPU资源")

        if health.memory_usage > 85:
            recommendations.append("内存使用率较高，建议优化内存管理或增加内存")

        return recommendations


# 创建全局监控实例
pdf_processing_monitor = PDFProcessingMonitor()
