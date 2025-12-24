from typing import Any

"""
系统监控服务 - 提供全面的系统监控和性能分析功能

功能特�?
- 实时性能数据收集
- 历史数据存储和查�?
- 性能趋势分析
- 自动告警机制
- 监控报告生成

作�? Claude Code
创建时间: 2025-11-01
"""

import asyncio
import json
import logging
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path

try:
    from src.core.database import get_db

    from src.api.v1.system_monitoring import (
        ApplicationMetrics,
        PerformanceAlert,
        SystemMetrics,
        collect_application_metrics,
        collect_system_metrics,
    )
    from src.core.config import get_config
except ImportError:
    # 独立运行时的回退方案
    def get_config():
        return {}

    def get_db():
        return None

    # 从system_monitoring.py导入核心功能
    import os
    import sys

    sys.path.insert(0, os.path.dirname(__file__))

    try:
        # 定义基础数据结构

        import psutil
        from pydantic import BaseModel

        class SystemMetrics(BaseModel):
            cpu: float
            memory: dict[str, Any]
            disk: dict[str, Any]
            network: dict[str, Any]
            timestamp: datetime

        class ApplicationMetrics(BaseModel):
            uptime: float
            active_connections: int
            request_count: int
            error_count: int
            response_time_avg: float

        class PerformanceAlert(BaseModel):
            level: str
            message: str
            metric: str
            value: float
            threshold: float
            timestamp: datetime

        def collect_system_metrics():
            from datetime import datetime

            return SystemMetrics(
                cpu=psutil.cpu_percent(interval=1),
                memory={
                    "total": psutil.virtual_memory().total,
                    "available": psutil.virtual_memory().available,
                    "percent": psutil.virtual_memory().percent,
                },
                disk={
                    "total": psutil.disk_usage("/").total,
                    "free": psutil.disk_usage("/").free,
                    "percent": (
                        psutil.disk_usage("/").used / psutil.disk_usage("/").total
                    )
                    * 100,
                },
                network={
                    "bytes_sent": psutil.net_io_counters().bytes_sent,
                    "bytes_recv": psutil.net_io_counters().bytes_recv,
                },
                timestamp=datetime.now(),
            )

        def collect_application_metrics():
            return ApplicationMetrics(
                uptime=time.time(),
                active_connections=0,
                request_count=0,
                error_count=0,
                response_time_avg=0.0,
            )

    except Exception as e:
        print(f"监控模块初始化失�? {e}")
        SystemMetrics = None
        ApplicationMetrics = None
        PerformanceAlert = None
        collect_system_metrics = None
        collect_application_metrics = None

logger = logging.getLogger(__name__)


@dataclass
class MonitoringConfig:
    """监控配置"""

    collection_interval: int = 60  # 数据收集间隔(�?
    history_retention_hours: int = 168  # 历史数据保留时间(小时)
    alert_threshold_cpu: float = 80.0  # CPU告警阈�?
    alert_threshold_memory: float = 85.0  # 内存告警阈�?
    alert_threshold_disk: float = 90.0  # 磁盘告警阈�?
    alert_threshold_response_time: float = 1000.0  # 响应时间告警阈�?ms)
    alert_threshold_error_rate: float = 5.0  # 错误率告警阈�?%)
    enable_auto_collection: bool = True  # 是否启用自动收集
    enable_alerting: bool = True  # 是否启用告警


@dataclass
class TrendAnalysis:
    """趋势分析结果"""

    metric_name: str
    current_value: float
    avg_value_1h: float
    avg_value_24h: float
    trend_direction: str  # "up", "down", "stable"
    trend_percent: float
    prediction_1h: float | None
    status: str  # "normal", "warning", "critical"


class MonitoringService:
    """系统监控服务"""

    def __init__(self, config: MonitoringConfig | None = None):
        self.config = config or MonitoringConfig()
        self._system_metrics_history: list[SystemMetrics] = []
        self._application_metrics_history: list[ApplicationMetrics] = []
        self._alerts_history: list[PerformanceAlert] = []
        self._is_running = False
        self._collection_task: asyncio.Task | None = None

        # 确保数据目录存在
        self.data_dir = Path("data/monitoring")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        logger.info("监控服务初始化完�?)

    async def start_monitoring(self):
        """启动监控服务"""
        if self._is_running:
            logger.warning("监控服务已在运行")
            return

        self._is_running = True
        self._collection_task = asyncio.create_task(self._collection_loop())
        logger.info("监控服务已启�?)

    async def stop_monitoring(self):
        """停止监控服务"""
        if not self._is_running:
            return

        self._is_running = False
        if self._collection_task:
            self._collection_task.cancel()
            try:
                await self._collection_task
            except asyncio.CancelledError:
                pass

        # 保存数据到文�?
        await self._save_data_to_file()
        logger.info("监控服务已停�?)

    async def _collection_loop(self):
        """数据收集循环"""
        while self._is_running:
            try:
                # 收集系统指标
                system_metrics = collect_system_metrics()
                self._system_metrics_history.append(system_metrics)

                # 收集应用指标
                app_metrics = collect_application_metrics()
                self._application_metrics_history.append(app_metrics)

                # 检查告�?
                if self.config.enable_alerting:
                    from src.api.v1.system_monitoring import check_performance_alerts

                    new_alerts = check_performance_alerts(system_metrics, app_metrics)
                    self._alerts_history.extend(new_alerts)

                # 清理历史数据
                await self._cleanup_old_data()

                logger.debug(
                    f"收集指标完成: CPU={system_metrics.cpu_percent:.1f}%, "
                    f"内存={system_metrics.memory_percent:.1f}%"
                )

            except Exception as e:
                logger.error(f"收集监控指标失败: {e}")

            # 等待下一次收�?
            try:
                await asyncio.sleep(self.config.collection_interval)
            except asyncio.CancelledError:
                break

    async def _cleanup_old_data(self):
        """清理过期数据"""
        cutoff_time = datetime.now() - timedelta(
            hours=self.config.history_retention_hours
        )

        # 清理系统指标历史
        self._system_metrics_history = [
            m for m in self._system_metrics_history if m.timestamp > cutoff_time
        ]

        # 清理应用指标历史
        self._application_metrics_history = [
            m for m in self._application_metrics_history if m.timestamp > cutoff_time
        ]

        # 清理告警历史 (保留更长时间)
        alert_cutoff_time = datetime.now() - timedelta(hours=24)
        self._alerts_history = [
            a for a in self._alerts_history if a.timestamp > alert_cutoff_time
        ]

    def get_current_metrics(self) -> tuple[SystemMetrics, ApplicationMetrics]:
        """获取当前指标"""
        if not self._system_metrics_history:
            raise ValueError("暂无系统指标数据")

        if not self._application_metrics_history:
            raise ValueError("暂无应用指标数据")

        return (self._system_metrics_history[-1], self._application_metrics_history[-1])

    def get_metrics_history(
        self, hours: int = 24, metric_type: str = "all"
    ) -> dict[str, list[Any]]:
        """获取历史指标数据"""
        cutoff_time = datetime.now() - timedelta(hours=hours)

        result = {}

        if metric_type in ("all", "system"):
            result["system"] = [
                m for m in self._system_metrics_history if m.timestamp > cutoff_time
            ]

        if metric_type in ("all", "application"):
            result["application"] = [
                m
                for m in self._application_metrics_history
                if m.timestamp > cutoff_time
            ]

        return result

    def analyze_trends(self, metric_name: str, hours: int = 24) -> TrendAnalysis:
        """分析指标趋势"""
        if metric_name.startswith("system_"):
            metrics = self._system_metrics_history
            field_name = metric_name.replace("system_", "")
        elif metric_name.startswith("app_"):
            metrics = self._application_metrics_history
            field_name = metric_name.replace("app_", "")
        else:
            raise ValueError(f"未知的指标类�? {metric_name}")

        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_metrics = [m for m in metrics if m.timestamp > cutoff_time]

        if not recent_metrics:
            raise ValueError(f"指标 {metric_name} 暂无历史数据")

        # 获取当前�?
        current_metrics = recent_metrics[-1]
        current_value = getattr(current_metrics, field_name, 0)

        # 计算1小时平均�?
        one_hour_ago = datetime.now() - timedelta(hours=1)
        metrics_1h = [m for m in recent_metrics if m.timestamp > one_hour_ago]
        avg_value_1h = sum(getattr(m, field_name, 0) for m in metrics_1h) / len(
            metrics_1h
        )

        # 计算24小时平均�?
        avg_value_24h = sum(getattr(m, field_name, 0) for m in recent_metrics) / len(
            recent_metrics
        )

        # 计算趋势
        if len(recent_metrics) >= 2:
            recent_values = [getattr(m, field_name, 0) for m in recent_metrics[-10:]]
            trend_percent = (
                (recent_values[-1] - recent_values[0]) / recent_values[0]
            ) * 100

            if trend_percent > 5:
                trend_direction = "up"
            elif trend_percent < -5:
                trend_direction = "down"
            else:
                trend_direction = "stable"
        else:
            trend_direction = "stable"
            trend_percent = 0

        # 简单的线性预�?(基于最近的趋势)
        if len(recent_metrics) >= 3:
            recent_values = [getattr(m, field_name, 0) for m in recent_metrics[-3:]]
            prediction_1h = recent_values[-1] + (recent_values[-1] - recent_values[0])
        else:
            prediction_1h = None

        # 确定状�?
        threshold_key = f"alert_threshold_{field_name}"
        threshold = getattr(self.config, threshold_key, None)

        if threshold:
            if current_value > threshold * 1.1:
                status = "critical"
            elif current_value > threshold:
                status = "warning"
            else:
                status = "normal"
        else:
            status = "normal"

        return TrendAnalysis(
            metric_name=metric_name,
            current_value=current_value,
            avg_value_1h=avg_value_1h,
            avg_value_24h=avg_value_24h,
            trend_direction=trend_direction,
            trend_percent=trend_percent,
            prediction_1h=prediction_1h,
            status=status,
        )

    def get_performance_summary(self, hours: int = 24) -> dict[str, Any]:
        """获取性能摘要"""
        cutoff_time = datetime.now() - timedelta(hours=hours)

        # 系统指标摘要
        system_metrics = [
            m for m in self._system_metrics_history if m.timestamp > cutoff_time
        ]
        system_summary = {}

        if system_metrics:
            system_summary = {
                "cpu": {
                    "avg": sum(m.cpu_percent for m in system_metrics)
                    / len(system_metrics),
                    "max": max(m.cpu_percent for m in system_metrics),
                    "min": min(m.cpu_percent for m in system_metrics),
                },
                "memory": {
                    "avg": sum(m.memory_percent for m in system_metrics)
                    / len(system_metrics),
                    "max": max(m.memory_percent for m in system_metrics),
                    "min": min(m.memory_percent for m in system_metrics),
                },
                "disk": {
                    "avg": sum(m.disk_usage_percent for m in system_metrics)
                    / len(system_metrics),
                    "max": max(m.disk_usage_percent for m in system_metrics),
                    "min": min(m.disk_usage_percent for m in system_metrics),
                },
            }

        # 应用指标摘要
        app_metrics = [
            m for m in self._application_metrics_history if m.timestamp > cutoff_time
        ]
        app_summary = {}

        if app_metrics:
            app_summary = {
                "response_time": {
                    "avg": sum(m.average_response_time for m in app_metrics)
                    / len(app_metrics),
                    "max": max(m.average_response_time for m in app_metrics),
                    "min": min(m.average_response_time for m in app_metrics),
                },
                "error_rate": {
                    "avg": sum(m.error_rate for m in app_metrics) / len(app_metrics),
                    "max": max(m.error_rate for m in app_metrics),
                    "min": min(m.error_rate for m in app_metrics),
                },
                "cache_hit_rate": {
                    "avg": sum(m.cache_hit_rate for m in app_metrics)
                    / len(app_metrics),
                    "max": max(m.cache_hit_rate for m in app_metrics),
                    "min": min(m.cache_hit_rate for m in app_metrics),
                },
            }

        # 告警摘要
        recent_alerts = [a for a in self._alerts_history if a.timestamp > cutoff_time]
        alert_summary = {
            "total": len(recent_alerts),
            "critical": len([a for a in recent_alerts if a.level == "critical"]),
            "warning": len([a for a in recent_alerts if a.level == "warning"]),
            "info": len([a for a in recent_alerts if a.level == "info"]),
            "resolved": len([a for a in recent_alerts if a.resolved]),
        }

        return {
            "time_range_hours": hours,
            "data_points": {
                "system": len(system_metrics),
                "application": len(app_metrics),
            },
            "system_metrics": system_summary,
            "application_metrics": app_summary,
            "alerts": alert_summary,
            "generated_at": datetime.now().isoformat(),
        }

    async def _save_data_to_file(self):
        """保存数据到文�?""
        try:
            # 保存系统指标
            system_file = self.data_dir / "system_metrics.json"
            system_data = [asdict(m) for m in self._system_metrics_history]
            with open(system_file, "w", encoding="utf-8") as f:
                json.dump(system_data, f, ensure_ascii=False, indent=2, default=str)

            # 保存应用指标
            app_file = self.data_dir / "application_metrics.json"
            app_data = [asdict(m) for m in self._application_metrics_history]
            with open(app_file, "w", encoding="utf-8") as f:
                json.dump(app_data, f, ensure_ascii=False, indent=2, default=str)

            # 保存告警历史
            alert_file = self.data_dir / "alerts.json"
            alert_data = [asdict(a) for a in self._alerts_history]
            with open(alert_file, "w", encoding="utf-8") as f:
                json.dump(alert_data, f, ensure_ascii=False, indent=2, default=str)

            logger.info(f"监控数据已保存到 {self.data_dir}")

        except Exception as e:
            logger.error(f"保存监控数据失败: {e}")

    async def load_data_from_file(self):
        """从文件加载数�?""
        try:
            # 加载系统指标
            system_file = self.data_dir / "system_metrics.json"
            if system_file.exists():
                with open(system_file, encoding="utf-8") as f:
                    system_data = json.load(f)
                self._system_metrics_history = [
                    SystemMetrics(**item) for item in system_data
                ]

            # 加载应用指标
            app_file = self.data_dir / "application_metrics.json"
            if app_file.exists():
                with open(app_file, encoding="utf-8") as f:
                    app_data = json.load(f)
                self._application_metrics_history = [
                    ApplicationMetrics(**item) for item in app_data
                ]

            # 加载告警历史
            alert_file = self.data_dir / "alerts.json"
            if alert_file.exists():
                with open(alert_file, encoding="utf-8") as f:
                    alert_data = json.load(f)
                self._alerts_history = [PerformanceAlert(**item) for item in alert_data]

            logger.info(f"�?{self.data_dir} 加载监控数据完成")

        except Exception as e:
            logger.error(f"加载监控数据失败: {e}")

    def get_service_status(self) -> dict[str, Any]:
        """获取服务状�?""
        return {
            "is_running": self._is_running,
            "collection_interval": self.config.collection_interval,
            "data_points": {
                "system_metrics": len(self._system_metrics_history),
                "application_metrics": len(self._application_metrics_history),
                "alerts": len(self._alerts_history),
            },
            "config": asdict(self.config),
            "data_directory": str(self.data_dir),
            "last_collection": (
                self._system_metrics_history[-1].timestamp.isoformat()
                if self._system_metrics_history
                else None
            ),
        }


# 全局监控服务实例
_monitoring_service: MonitoringService | None = None


def get_monitoring_service() -> MonitoringService:
    """获取全局监控服务实例"""
    global _monitoring_service
    if _monitoring_service is None:
        config = MonitoringConfig()
        _monitoring_service = MonitoringService(config)
    return _monitoring_service


async def initialize_monitoring():
    """初始化监控服�?""
    service = get_monitoring_service()
    await service.load_data_from_file()

    if service.config.enable_auto_collection:
        await service.start_monitoring()
        logger.info("监控服务自动启动")
    else:
        logger.info("监控服务初始化完成，自动收集已禁�?)


async def shutdown_monitoring():
    """关闭监控服务"""
    global _monitoring_service
    if _monitoring_service:
        await _monitoring_service.stop_monitoring()
        logger.info("监控服务已关�?)
