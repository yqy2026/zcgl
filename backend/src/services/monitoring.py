from typing import Any
"""
系统监控服务
提供系统性能监控、日志记录和健康检查功能
"""

import asyncio
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta


import psutil
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@dataclass
class SystemMetrics:
    """系统指标数据类"""

    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used: int
    memory_available: int
    disk_usage_percent: float
    active_connections: int
    database_size: int
    response_time: float


@dataclass
class APIMetrics:
    """API指标数据类"""

    timestamp: datetime
    endpoint: str
    method: str
    status_code: int
    response_time: float
    user_id: str | None = None


class SystemMonitor:
    """系统监控器"""

    def __init__(self, max_history_size: int = 1000):
        self.max_history_size = max_history_size
        self.system_metrics_history = deque(maxlen=max_history_size)
        self.api_metrics_history = deque(maxlen=max_history_size)
        self.error_counts = defaultdict(int)
        self.response_times = deque(maxlen=100)  # 最近100次响应时间
        self.start_time = datetime.now()
        self._is_monitoring = False

    async def start_monitoring(self, interval: int = 30):
        """开始系统监控"""
        if self._is_monitoring:
            return

        self._is_monitoring = True
        logger.info(f"Starting system monitoring with interval: {interval}s")

        while self._is_monitoring:
            try:
                metrics = await self._collect_system_metrics()
                self.system_metrics_history.append(metrics)
                await asyncio.sleep(interval)
            except Exception as e:
                logger.error(f"Error in system monitoring: {e}")
                await asyncio.sleep(interval)

    def stop_monitoring(self):
        """停止系统监控"""
        self._is_monitoring = False
        logger.info("System monitoring stopped")

    async def _collect_system_metrics(self) -> SystemMetrics:
        """收集系统指标"""
        start_time = time.time()

        # CPU和内存信息
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()

        # 磁盘使用情况
        disk = psutil.disk_usage("/")
        disk_usage_percent = disk.used / disk.total * 100

        # 网络连接数
        try:
            active_connections = len(psutil.net_connections())
        except (psutil.AccessDenied, OSError):
            active_connections = 0

        # 数据库信息
        database_size = await self._get_database_size()

        response_time = time.time() - start_time

        return SystemMetrics(
            timestamp=datetime.now(),
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_used=memory.used,
            memory_available=memory.available,
            disk_usage_percent=disk_usage_percent,
            active_connections=active_connections,
            database_size=database_size,
            response_time=response_time,
        )

    async def _get_database_size(self) -> int:
        """获取数据库大小"""
        try:
            # 这里应该从数据库连接池获取连接
            # 实际计算数据库文件大小
            return 50 * 1024 * 1024  # 50MB
        except Exception:
            return 0

    def record_api_call(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        response_time: float,
        user_id: str | None = None,
    ):
        """记录API调用"""
        metrics = APIMetrics(
            timestamp=datetime.now(),
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            response_time=response_time,
            user_id=user_id,
        )

        self.api_metrics_history.append(metrics)
        self.response_times.append(response_time)

        # 记录错误
        if status_code >= 400:
            self.error_counts[f"{method} {endpoint}"] += 1

    def get_system_status(self) -> dict[str, Any]:
        """获取系统状态摘要"""
        if not self.system_metrics_history:
            return {
                "status": "no_data",
                "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
            }

        latest = self.system_metrics_history[-1]

        # 计算平均响应时间
        avg_response_time = (
            sum(self.response_times) / len(self.response_times)
            if self.response_times
            else 0
        )

        # 计算错误率
        total_calls = len(self.api_metrics_history)
        error_calls = sum(1 for m in self.api_metrics_history if m.status_code >= 400)
        error_rate = (error_calls / total_calls * 100) if total_calls > 0 else 0

        return {
            "status": "healthy"
            if latest.cpu_percent < 80 and latest.memory_percent < 80
            else "warning",
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
            "current_metrics": {
                "cpu_percent": latest.cpu_percent,
                "memory_percent": latest.memory_percent,
                "memory_used_mb": latest.memory_used // (1024 * 1024),
                "memory_available_mb": latest.memory_available // (1024 * 1024),
                "disk_usage_percent": latest.disk_usage_percent,
                "active_connections": latest.active_connections,
                "database_size_mb": latest.database_size // (1024 * 1024),
                "response_time_ms": latest.response_time * 1000,
            },
            "performance": {
                "avg_response_time_ms": avg_response_time * 1000,
                "error_rate_percent": error_rate,
                "total_api_calls": total_calls,
                "total_errors": error_calls,
            },
            "timestamp": latest.timestamp.isoformat(),
        }

    def get_performance_summary(self, hours: int = 1) -> dict[str, Any]:
        """获取性能摘要"""
        cutoff_time = datetime.now() - timedelta(hours=hours)

        # 筛选指定时间范围内的指标
        recent_system = [
            m for m in self.system_metrics_history if m.timestamp >= cutoff_time
        ]
        recent_api = [m for m in self.api_metrics_history if m.timestamp >= cutoff_time]

        if not recent_system:
            return {"message": f"No data available for the last {hours} hours"}

        # 系统指标统计
        cpu_values = [m.cpu_percent for m in recent_system]
        memory_values = [m.memory_percent for m in recent_system]

        # API性能统计
        response_times = [m.response_time for m in recent_api]
        status_codes = [m.status_code for m in recent_api]

        return {
            "time_range_hours": hours,
            "system_stats": {
                "cpu": {
                    "avg": sum(cpu_values) / len(cpu_values),
                    "max": max(cpu_values),
                    "min": min(cpu_values),
                },
                "memory": {
                    "avg": sum(memory_values) / len(memory_values),
                    "max": max(memory_values),
                    "min": min(memory_values),
                },
            },
            "api_stats": {
                "total_calls": len(recent_api),
                "avg_response_time_ms": (
                    sum(response_times) / len(response_times) * 1000
                )
                if response_times
                else 0,
                "max_response_time_ms": (max(response_times) * 1000)
                if response_times
                else 0,
                "error_rate_percent": (
                    sum(1 for s in status_codes if s >= 400) / len(status_codes) * 100
                )
                if status_codes
                else 0,
            },
            "top_errors": dict(
                sorted(self.error_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            ),
        }

    def get_database_stats(self, db: Session) -> dict[str, Any]:
        """获取数据库统计信息"""
        try:
            # 获取表统计信息
            tables_query = text("""
                SELECT name, sql FROM sqlite_master
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """)
            tables = db.execute(tables_query).fetchall()

            table_stats = []
            total_records = 0

            for table_name, _ in tables:
                try:
                    count_query = text(f"SELECT COUNT(*) FROM {table_name}")
                    count = db.execute(count_query).scalar()
                    total_records += count

                    table_stats.append({"name": table_name, "record_count": count})
                except Exception as e:
                    logger.warning(f"Could not get stats for table {table_name}: {e}")

            return {
                "total_tables": len(tables),
                "total_records": total_records,
                "tables": table_stats,
            }

        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {"error": str(e)}

    def get_health_check(self, db: Session) -> dict[str, Any]:
        """健康检查"""
        health_status = {
            "overall": "healthy",
            "timestamp": datetime.now().isoformat(),
            "checks": {},
        }

        # 检查数据库连接
        try:
            db.execute(text("SELECT 1"))
            health_status["checks"]["database"] = {
                "status": "healthy",
                "message": "Database connection OK",
            }
        except Exception as e:
            health_status["checks"]["database"] = {
                "status": "unhealthy",
                "message": f"Database connection failed: {e}",
            }
            health_status["overall"] = "unhealthy"

        # 检查系统资源
        if self.system_metrics_history:
            latest = self.system_metrics_history[-1]

            # CPU检查
            if latest.cpu_percent > 90:
                health_status["checks"]["cpu"] = {
                    "status": "critical",
                    "message": f"High CPU usage: {latest.cpu_percent:.1f}%",
                }
                health_status["overall"] = "critical"
            elif latest.cpu_percent > 80:
                health_status["checks"]["cpu"] = {
                    "status": "warning",
                    "message": f"Elevated CPU usage: {latest.cpu_percent:.1f}%",
                }
                if health_status["overall"] == "healthy":
                    health_status["overall"] = "warning"
            else:
                health_status["checks"]["cpu"] = {
                    "status": "healthy",
                    "message": f"CPU usage normal: {latest.cpu_percent:.1f}%",
                }

            # 内存检查
            if latest.memory_percent > 90:
                health_status["checks"]["memory"] = {
                    "status": "critical",
                    "message": f"High memory usage: {latest.memory_percent:.1f}%",
                }
                health_status["overall"] = "critical"
            elif latest.memory_percent > 80:
                health_status["checks"]["memory"] = {
                    "status": "warning",
                    "message": f"Elevated memory usage: {latest.memory_percent:.1f}%",
                }
                if health_status["overall"] == "healthy":
                    health_status["overall"] = "warning"
            else:
                health_status["checks"]["memory"] = {
                    "status": "healthy",
                    "message": f"Memory usage normal: {latest.memory_percent:.1f}%",
                }

        # 检查错误率
        if self.api_metrics_history:
            recent_calls = list(self.api_metrics_history)[-100:]  # 最近100次调用
            error_rate = (
                sum(1 for m in recent_calls if m.status_code >= 400)
                / len(recent_calls)
                * 100
            )

            if error_rate > 20:
                health_status["checks"]["api_errors"] = {
                    "status": "critical",
                    "message": f"High error rate: {error_rate:.1f}%",
                }
                health_status["overall"] = "critical"
            elif error_rate > 10:
                health_status["checks"]["api_errors"] = {
                    "status": "warning",
                    "message": f"Elevated error rate: {error_rate:.1f}%",
                }
                if health_status["overall"] == "healthy":
                    health_status["overall"] = "warning"
            else:
                health_status["checks"]["api_errors"] = {
                    "status": "healthy",
                    "message": f"Error rate normal: {error_rate:.1f}%",
                }

        return health_status


# 全局监控器实例
system_monitor = SystemMonitor()
