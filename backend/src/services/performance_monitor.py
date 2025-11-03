from typing import Any
"""
PDF导入性能监控和优化服务
提供实时性能监控、指标收集和优化建议
"""

import logging
import statistics
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta


import psutil

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """性能指标数据类"""

    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    disk_io: dict[str, float]
    network_io: dict[str, float]
    processing_time: float
    success_rate: float
    error_rate: float
    concurrent_requests: int
    queue_length: int
    response_time: float
    throughput: float


@dataclass
class ProcessingTimeMetrics:
    """处理时间指标"""

    pdf_processing: float
    text_extraction: float
    field_extraction: float
    validation: float
    matching: float
    total_processing: float
    file_size: int
    processing_method: str
    success: bool


class PerformanceMonitor:
    """性能监控器"""

    def __init__(self):
        self.metrics_history: deque = deque(maxlen=1000)  # 保留最近1000个指标
        self.processing_times: deque = deque(maxlen=500)  # 保留最近500次处理时间
        self.alert_thresholds = self._load_alert_thresholds()
        self.performance_cache = {}
        self.optimization_suggestions = []
        self.baseline_metrics = None
        self.anomaly_detector = AnomalyDetector()

    def _load_alert_thresholds(self) -> dict[str, Any][str, float]:
        """加载告警阈值"""
        return {
            "cpu_usage": 80.0,  # CPU使用率超过80%
            "memory_usage": 85.0,  # 内存使用率超过85%
            "response_time": 30.0,  # 响应时间超过30秒
            "error_rate": 0.05,  # 错误率超过5%
            "queue_length": 100,  # 队列长度超过100
            "concurrent_requests": 50,  # 并发请求超过50
        }

    async def collect_system_metrics(self) -> dict[str, Any][str, float]:
        """收集系统性能指标"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)

            # 内存使用情况
            memory = psutil.virtual_memory()
            memory_percent = memory.percent

            # 磁盘IO
            disk_io = psutil.disk_io_counters()
            disk_read_mb = disk_io.read_bytes / (1024 * 1024)
            disk_write_mb = disk_io.write_bytes / (1024 * 1024)

            # 网络IO
            network_io = psutil.net_io_counters()
            network_sent_mb = network_io.bytes_sent / (1024 * 1024)
            network_recv_mb = network_io.bytes_recv / (1024 * 1024)

            return {
                "cpu_usage": cpu_percent,
                "memory_usage": memory_percent,
                "disk_read_mb": disk_read_mb,
                "disk_write_mb": disk_write_mb,
                "network_sent_mb": network_sent_mb,
                "network_recv_mb": network_recv_mb,
            }

        except Exception as e:
            logger.error(f"收集系统指标失败: {e}")
            return {}

    async def record_processing_metrics(
        self,
        session_id: str,
        processing_steps: dict[str, float],
        file_size: int,
        processing_method: str,
        success: bool,
        total_time: float,
    ):
        """记录处理性能指标"""
        try:
            metrics = ProcessingTimeMetrics(
                timestamp=datetime.now(),
                pdf_processing=processing_steps.get("pdf_processing", 0),
                text_extraction=processing_steps.get("text_extraction", 0),
                field_extraction=processing_steps.get("field_extraction", 0),
                validation=processing_steps.get("validation", 0),
                matching=processing_steps.get("matching", 0),
                total_processing=total_time,
                file_size=file_size,
                processing_method=processing_method,
                success=success,
            )

            self.processing_times.append(asdict(metrics))

            # 检测性能异常
            anomalies = await self.anomaly_detector.detect_anomalies(metrics)
            if anomalies:
                await self._handle_performance_anomalies(session_id, anomalies)

            logger.info(f"记录处理指标: {session_id}, 总时间: {total_time:.2f}s")

        except Exception as e:
            logger.error(f"记录处理指标失败: {e}")

    async def get_real_time_performance(self) -> dict[str, Any]:
        """获取实时性能数据"""
        try:
            # 收集系统指标
            system_metrics = await self.collect_system_metrics()

            # 计算处理统计
            recent_processing = list(self.processing_times)[-50:]  # 最近50次处理

            if not recent_processing:
                return {
                    "timestamp": datetime.now().isoformat(),
                    "system_metrics": system_metrics,
                    "processing_stats": {},
                    "alerts": [],
                    "recommendations": [],
                }

            # 计算统计指标
            successful_processes = [
                p for p in recent_processing if p.get("success", True)
            ]
            failed_processes = [
                p for p in recent_processing if not p.get("success", True)
            ]

            success_rate = (
                len(successful_processes) / len(recent_processing)
                if recent_processing
                else 0
            )
            error_rate = (
                len(failed_processes) / len(recent_processing)
                if recent_processing
                else 0
            )

            avg_processing_time = statistics.mean(
                [p["total_processing"] for p in recent_processing]
            )
            avg_throughput = (
                len(recent_processing) / 60 if recent_processing else 0
            )  # 每分钟处理数

            # 性能评分
            performance_score = self._calculate_performance_score(
                system_metrics, success_rate, avg_processing_time
            )

            # 检查告警
            alerts = await self._check_performance_alerts(
                system_metrics, success_rate, avg_processing_time
            )

            # 生成优化建议
            recommendations = await self._generate_optimization_recommendations(
                system_metrics, recent_processing
            )

            return {
                "timestamp": datetime.now().isoformat(),
                "system_metrics": system_metrics,
                "processing_stats": {
                    "success_rate": success_rate,
                    "error_rate": error_rate,
                    "avg_processing_time": avg_processing_time,
                    "throughput_per_minute": avg_throughput,
                    "total_processed": len(recent_processing),
                    "recent_failures": len(failed_processes[-10:]),  # 最近10次失败
                },
                "performance_score": performance_score,
                "alerts": alerts,
                "recommendations": recommendations,
            }

        except Exception as e:
            logger.error(f"获取实时性能失败: {e}")
            return {"timestamp": datetime.now().isoformat(), "error": str(e)}

    def _calculate_performance_score(
        self,
        system_metrics: dict[str, float],
        success_rate: float,
        avg_processing_time: float,
    ) -> float:
        """计算性能评分"""
        score = 100.0

        # CPU使用率评分 (权重20%)
        cpu_score = max(0, 100 - system_metrics.get("cpu_usage", 0))
        score = score * 0.8 + cpu_score * 0.2

        # 内存使用率评分 (权重20%)
        memory_score = max(0, 100 - system_metrics.get("memory_usage", 0))
        score = score * 0.8 + memory_score * 0.2

        # 成功率评分 (权重30%)
        score = score * 0.7 + (success_rate * 100) * 0.3

        # 处理时间评分 (权重30%) - 越快越好
        time_score = max(
            0, 100 - min(avg_processing_time / 60 * 100, 100)
        )  # 60秒为基准
        score = score * 0.7 + time_score * 0.3

        return min(score, 100.0)

    async def _check_performance_alerts(
        self,
        system_metrics: dict[str, float],
        success_rate: float,
        avg_processing_time: float,
    ) -> list[dict[str, Any]]:
        """检查性能告警"""
        alerts = []

        # 系统资源告警
        if system_metrics.get("cpu_usage", 0) > self.alert_thresholds["cpu_usage"]:
            alerts.append(
                {
                    "type": "system",
                    "level": "warning",
                    "message": f"CPU使用率过高: {system_metrics['cpu_usage']:.1f}%",
                    "threshold": self.alert_thresholds["cpu_usage"],
                    "current_value": system_metrics["cpu_usage"],
                }
            )

        if (
            system_metrics.get("memory_usage", 0)
            > self.alert_thresholds["memory_usage"]
        ):
            alerts.append(
                {
                    "type": "system",
                    "level": "warning",
                    "message": f"内存使用率过高: {system_metrics['memory_usage']:.1f}%",
                    "threshold": self.alert_thresholds["memory_usage"],
                    "current_value": system_metrics["memory_usage"],
                }
            )

        # 处理性能告警
        if avg_processing_time > self.alert_thresholds["response_time"]:
            alerts.append(
                {
                    "type": "performance",
                    "level": "critical",
                    "message": f"平均处理时间过长: {avg_processing_time:.1f}秒",
                    "threshold": self.alert_thresholds["response_time"],
                    "current_value": avg_processing_time,
                }
            )

        # 错误率告警
        if (1 - success_rate) > self.alert_thresholds["error_rate"]:
            alerts.append(
                {
                    "type": "quality",
                    "level": "critical",
                    "message": f"错误率过高: {(1 - success_rate) * 100:.1f}%",
                    "threshold": self.alert_thresholds["error_rate"],
                    "current_value": (1 - success_rate) * 100,
                }
            )

        return alerts

    async def _generate_optimization_recommendations(
        self, system_metrics: dict[str, float], recent_processing: list[dict]
    ) -> list[str]:
        """生成优化建议"""
        recommendations = []

        # 系统资源优化建议
        if system_metrics.get("cpu_usage", 0) > 70:
            recommendations.append("建议增加CPU资源或启用负载均衡")

        if system_metrics.get("memory_usage", 0) > 80:
            recommendations.append("建议增加内存资源或优化内存使用")

        # 处理方法分析
        method_performance = defaultdict(list)
        for process in recent_processing:
            method = process.get("processing_method", "unknown")
            method_performance[method].append(process.get("total_processing", 0))

        # 找出最佳处理方法
        best_method = None
        best_avg_time = float("inf")

        for method, times in method_performance.items():
            if times:
                avg_time = statistics.mean(times)
                if avg_time < best_avg_time:
                    best_avg_time = avg_time
                    best_method = method

        if best_method:
            recommendations.append(
                f"建议优先使用 {best_method} 处理方法，平均时间: {best_avg_time:.1f}秒"
            )

        # 文件大小对性能影响分析
        size_performance = [
            (p.get("file_size", 0), p.get("total_processing", 0))
            for p in recent_processing
            if p.get("file_size")
        ]
        if size_performance:
            # 简单的线性回归检测趋势
            avg_size = statistics.mean([s for s, _ in size_performance])
            avg_time = statistics.mean([t for _, t in size_performance])

            # 如果处理时间增长过快，建议优化
            size_time_ratio = avg_time / max(avg_size / 1000, 1)  # 每MB的处理时间
            if size_time_ratio > 30:  # 每MB超过30秒
                recommendations.append("建议优化大文件处理算法或实施分块处理")

        return recommendations

    async def _handle_performance_anomalies(
        self, session_id: str, anomalies: list[dict]
    ):
        """处理性能异常"""
        try:
            for anomaly in anomalies:
                logger.warning(
                    f"检测到性能异常: {anomaly['type']} - {anomaly['description']}"
                )

                # 根据异常类型采取不同措施
                if anomaly["type"] == "processing_time_spike":
                    await self._trigger_resource_optimization()
                elif anomaly["type"] == "success_rate_drop":
                    await self._trigger_quality_check()
                elif anomaly["type"] == "resource_exhaustion":
                    await self._trigger_emergency_scaling()

        except Exception as e:
            logger.error(f"处理性能异常失败: {e}")

    async def _trigger_resource_optimization(self):
        """触发资源优化"""
        logger.info("触发资源优化: 清理缓存、重启服务等")
        # 这里可以添加具体的优化逻辑

    async def _trigger_quality_check(self):
        """触发质量检查"""
        logger.info("触发质量检查: 检查数据质量和算法准确率")
        # 这里可以添加质量检查逻辑

    async def _trigger_emergency_scaling(self):
        """触发紧急扩容"""
        logger.warning("触发紧急扩容: 系统负载过高")
        # 这里可以添加扩容逻辑

    async def get_performance_report(self, hours: int = 24) -> dict[str, Any]:
        """获取性能报告"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            recent_data = [
                m for m in self.metrics_history if m["timestamp"] > cutoff_time
            ]

            if not recent_data:
                return {
                    "report_period_hours": hours,
                    "total_requests": 0,
                    "avg_performance_score": 0,
                    "peak_cpu": 0,
                    "peak_memory": 0,
                    "recommendations": ["无足够数据生成报告"],
                }

            # 计算报告指标
            total_requests = len(recent_data)
            avg_performance = statistics.mean(
                [m["performance_score"] for m in recent_data]
            )
            peak_cpu = max([m["cpu_usage"] for m in recent_data])
            peak_memory = max([m["memory_usage"] for m in recent_data])

            # 趋势分析
            if len(recent_data) >= 10:
                performance_trend = self._analyze_trend(
                    [m["performance_score"] for m in recent_data[-10:]]
                )
            else:
                performance_trend = "stable"

            return {
                "report_period_hours": hours,
                "generated_at": datetime.now().isoformat(),
                "total_requests": total_requests,
                "avg_performance_score": avg_performance,
                "performance_trend": performance_trend,
                "peak_system_usage": {
                    "cpu_percent": peak_cpu,
                    "memory_percent": peak_memory,
                },
                "optimization_opportunities": await self._identify_optimization_opportunities(
                    recent_data
                ),
            }

        except Exception as e:
            logger.error(f"生成性能报告失败: {e}")
            return {"error": str(e)}

    def _analyze_trend(self, values: list[float]) -> str:
        """分析趋势"""
        if len(values) < 3:
            return "insufficient_data"

        # 简单线性趋势分析
        first_half = values[: len(values) // 2]
        second_half = values[len(values) // 2 :]

        first_avg = statistics.mean(first_half)
        second_avg = statistics.mean(second_half)

        if second_avg > first_avg * 1.1:
            return "improving"
        elif second_avg < first_avg * 0.9:
            return "degrading"
        else:
            return "stable"

    async def _identify_optimization_opportunities(self, data: list[dict]) -> list[str]:
        """识别优化机会"""
        opportunities = []

        # 分析CPU使用模式
        cpu_values = [d["cpu_usage"] for d in data if "cpu_usage" in d]
        if cpu_values and statistics.mean(cpu_values) > 70:
            opportunities.append("CPU使用率持续偏高，建议优化算法或增加资源")

        # 分析内存使用模式
        memory_values = [d["memory_usage"] for d in data if "memory_usage" in d]
        if memory_values and statistics.mean(memory_values) > 75:
            opportunities.append("内存使用率偏高，建议检查内存泄漏或优化数据结构")

        # 分析响应时间模式
        response_times = [d["response_time"] for d in data if "response_time" in d]
        if response_times and statistics.mean(response_times) > 20:
            opportunities.append("响应时间较长，建议优化处理流程或启用异步处理")

        return opportunities


class AnomalyDetector:
    """异常检测器"""

    def __init__(self):
        self.baseline_cache = {}
        self.anomaly_threshold = 2.0  # 2个标准差

    async def detect_anomalies(
        self, metrics: ProcessingTimeMetrics
    ) -> list[dict[str, Any]]:
        """检测性能异常"""
        anomalies = []

        # 处理时间异常检测
        processing_time_anomaly = await self._detect_processing_time_anomaly(metrics)
        if processing_time_anomaly:
            anomalies.append(processing_time_anomaly)

        # 成功率异常检测
        if hasattr(self, "_recent_success_rate"):
            success_rate_anomaly = await self._detect_success_rate_anomaly(metrics)
            if success_rate_anomaly:
                anomalies.append(success_rate_anomaly)

        return anomalies

    async def _detect_processing_time_anomaly(
        self, metrics: ProcessingTimeMetrics
    ) -> dict[str, Any] | None:
        """检测处理时间异常"""
        # 这里可以实现更复杂的异常检测算法
        # 简单示例：如果处理时间超过平均值的3倍，则认为是异常
        if not hasattr(self, "_processing_history"):
            self._processing_history = []

        self._processing_history.append(metrics.total_processing)
        if len(self._processing_history) < 10:
            return None

        mean_time = statistics.mean(self._processing_history[-10:])
        std_time = statistics.stdev(self._processing_history[-10:])

        if metrics.total_processing > mean_time + (3 * std_time):
            return {
                "type": "processing_time_spike",
                "description": f"处理时间异常: {metrics.total_processing:.2f}s (平均: {mean_time:.2f}s)",
                "severity": "high",
                "current_value": metrics.total_processing,
                "baseline_value": mean_time,
                "recommendation": "检查处理瓶颈或考虑优化算法",
            }

        return None

    async def _detect_success_rate_anomaly(
        self, metrics: ProcessingTimeMetrics
    ) -> dict[str, Any] | None:
        """检测成功率异常"""
        # 这里可以实现成功率异常检测逻辑
        return None


# 全局性能监控实例
performance_monitor = PerformanceMonitor()
