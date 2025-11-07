from typing import Any

"""
并发处理优化服务
提供智能的并发处理控制和资源管理
"""

import asyncio
import gc
import logging
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum

logger = logging.getLogger(__name__)

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.warning("psutil未安装，资源监控功能将被禁用")


class TaskPriority(Enum):
    """任务优先�?""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class ProcessingTask:
    """处理任务数据结构"""

    task_id: str
    func: Callable
    args: tuple
    kwargs: dict
    priority: TaskPriority
    created_at: datetime
    estimated_duration: float = 0.0
    resource_requirements: dict[str, Any] = None

    def __post_init__(self):
        if self.resource_requirements is None:
            self.resource_requirements = {}


class ResourceMonitor:
    """系统资源监控�?""

    def __init__(self):
        self.start_time = datetime.now(UTC)
        self.monitoring_active = True
        self.thresholds = {
            "cpu_percent": 80.0,  # CPU使用率阈�?
            "memory_percent": 85.0,  # 内存使用率阈�?
            "disk_io_percent": 90.0,  # 磁盘I/O阈�?
            "active_processes": 10,  # 最大活跃进程数
        }

    def get_system_metrics(self) -> dict[str, float]:
        """获取系统指标"""
        if not PSUTIL_AVAILABLE:
            return {
                "cpu_percent": 25.0,  # 模拟�?
                "memory_percent": 40.0,  # 模拟�?
                "disk_io_percent": 10.0,  # 模拟�?
                "active_processes": 5,  # 模拟�?
                "uptime_seconds": (datetime.now(UTC) - self.start_time).total_seconds(),
            }

        try:
            # CPU使用率（�?秒内的平均值）
            cpu_percent = psutil.cpu_percent(interval=1)

            # 内存使用�?
            memory = psutil.virtual_memory()
            memory_percent = memory.percent

            # 磁盘使用率（取所有磁盘的平均值）
            disk_io = 0.0
            try:
                disk_usage = psutil.disk_usage("/")
                disk_io = (disk_usage.used / disk_usage.total) * 100
            except (OSError, PermissionError):
                pass

            # 活跃进程�?
            process_count = len(psutil.pids())

            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "disk_io_percent": disk_io,
                "active_processes": process_count,
                "uptime_seconds": (datetime.now(UTC) - self.start_time).total_seconds(),
            }

        except Exception as e:
            logger.error(f"获取系统指标失败: {e}")
            return {
                "cpu_percent": 0.0,
                "memory_percent": 0.0,
                "disk_io_percent": 0.0,
                "active_processes": 0,
                "uptime_seconds": 0.0,
            }

    def can_accept_new_task(self, task_requirements: dict[str, Any]) -> bool:
        """检查是否可以接受新任务"""
        metrics = self.get_system_metrics()

        # CPU检�?
        if metrics["cpu_percent"] > self.thresholds["cpu_percent"]:
            logger.warning(f"CPU使用率过�?({metrics['cpu_percent']:.1f}%)，拒绝新任务")
            return False

        # 内存检�?
        if metrics["memory_percent"] > self.thresholds["memory_percent"]:
            logger.warning(
                f"内存使用率过�?({metrics['memory_percent']:.1f}%)，拒绝新任务"
            )
            return False

        # 进程数检�?
        if metrics["active_processes"] > self.thresholds["active_processes"]:
            logger.warning(
                f"活跃进程数过�?({metrics['active_processes']})，拒绝新任务"
            )
            return False

        return True

    def get_optimal_concurrency(self) -> int:
        """获取最优并发数"""
        metrics = self.get_system_metrics()

        # 基础并发数（基于CPU核心数）
        if PSUTIL_AVAILABLE:
            cpu_cores = psutil.cpu_count()
            base_concurrency = max(2, cpu_cores - 1)
        else:
            base_concurrency = 4  # 默认�?

        # 根据系统负载调整
        load_factor = 1.0

        # CPU负载调整
        if metrics["cpu_percent"] > 70:
            load_factor *= 0.7
        elif metrics["cpu_percent"] > 50:
            load_factor *= 0.85

        # 内存负载调整
        if metrics["memory_percent"] > 80:
            load_factor *= 0.6
        elif metrics["memory_percent"] > 60:
            load_factor *= 0.8

        optimal_concurrency = max(1, int(base_concurrency * load_factor))

        logger.debug(
            f"系统负载评估 - CPU: {metrics['cpu_percent']:.1f}%, "
            f"内存: {metrics['memory_percent']:.1f}%, "
            f"最优并发数: {optimal_concurrency}"
        )

        return optimal_concurrency


class TaskQueue:
    """优先级任务队�?""

    def __init__(self):
        self._queue = []
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)

    def put(self, task: ProcessingTask):
        """添加任务到队�?""
        with self._condition:
            self._queue.append(task)
            # 按优先级排序（高优先级在前）
            self._queue.sort(key=lambda t: t.priority.value, reverse=True)
            self._condition.notify()

    def get(self, timeout: float | None = None) -> ProcessingTask | None:
        """从队列获取任�?""
        with self._condition:
            if not self._queue:
                self._condition.wait(timeout)

            if self._queue:
                return self._queue.pop(0)
            return None

    def size(self) -> int:
        """获取队列大小"""
        with self._lock:
            return len(self._queue)

    def empty(self) -> bool:
        """检查队列是否为�?""
        with self._lock:
            return len(self._queue) == 0


class ConcurrentProcessingOptimizer:
    """并发处理优化�?""

    def __init__(
        self,
        max_workers: int = 4,
        enable_monitoring: bool = True,
        resource_aware: bool = True,
    ):
        """
        初始化并发处理优化器

        Args:
            max_workers: 最大工作线程数
            enable_monitoring: 是否启用资源监控
            resource_aware: 是否启用资源感知调度
        """
        self.max_workers = max_workers
        self.enable_monitoring = enable_monitoring
        self.resource_aware = resource_aware

        # 任务队列
        self.task_queue = TaskQueue()

        # 资源监控
        self.resource_monitor = ResourceMonitor() if enable_monitoring else None

        # 执行器管�?
        self.executor = None
        self.active_workers = 0
        self.worker_lock = threading.Lock()

        # 统计信息
        self.stats = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "average_processing_time": 0.0,
            "peak_concurrent_tasks": 0,
            "current_concurrent_tasks": 0,
            "resource_rejections": 0,
        }

        # 控制标志
        self.shutdown_flag = False

        logger.info(
            f"并发处理优化器初始化 - 最大工作线�? {max_workers}, "
            f"资源监控: {enable_monitoring}, 资源感知: {resource_aware}"
        )

    def start(self):
        """启动并发处理�?""
        if self.executor is not None:
            logger.warning("并发处理器已经启�?)
            return

        # 获取最优工作线程数
        if self.resource_aware and self.resource_monitor:
            optimal_workers = self.resource_monitor.get_optimal_concurrency()
            actual_workers = min(self.max_workers, optimal_workers)
        else:
            actual_workers = self.max_workers

        self.executor = ThreadPoolExecutor(
            max_workers=actual_workers, thread_name_prefix="PDFProcessor"
        )

        # 启动工作线程
        for i in range(actual_workers):
            worker_thread = threading.Thread(
                target=self._worker_loop, name=f"PDFWorker-{i}", daemon=True
            )
            worker_thread.start()

        logger.info(f"并发处理器已启动，工作线程数: {actual_workers}")

    def stop(self, wait_for_completion: bool = True, timeout: float = 30.0):
        """停止并发处理�?""
        if self.executor is None:
            logger.warning("并发处理器未启动")
            return

        logger.info("正在停止并发处理�?..")
        self.shutdown_flag = True

        # 等待任务完成
        if wait_for_completion:
            start_time = time.time()
            while not self.task_queue.empty() and self.active_workers > 0:
                if time.time() - start_time > timeout:
                    logger.warning("等待任务完成超时，强制停�?)
                    break
                time.sleep(0.1)

        # 关闭执行�?
        self.executor.shutdown(wait=wait_for_completion)
        self.executor = None
        self.shutdown_flag = False

        logger.info("并发处理器已停止")

    def submit_task(
        self,
        task_id: str,
        func: Callable,
        args: tuple = (),
        kwargs: dict[str, Any] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        estimated_duration: float = 0.0,
        resource_requirements: dict[str, Any] = None,
    ) -> str:
        """
        提交处理任务

        Args:
            task_id: 任务唯一标识
            func: 要执行的函数
            args: 函数参数
            kwargs: 函数关键字参�?
            priority: 任务优先�?
            estimated_duration: 预估执行时间（秒�?
            resource_requirements: 资源需�?

        Returns:
            任务ID
        """
        if kwargs is None:
            kwargs = {}

        if resource_requirements is None:
            resource_requirements = {}

        # 资源感知检�?
        if self.resource_aware and self.resource_monitor:
            if not self.resource_monitor.can_accept_new_task(resource_requirements):
                self.stats["resource_rejections"] += 1
                raise ResourceError("系统资源不足，无法接受新任务")

        # 创建任务
        task = ProcessingTask(
            task_id=task_id,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            created_at=datetime.now(UTC),
            estimated_duration=estimated_duration,
            resource_requirements=resource_requirements,
        )

        # 添加到队�?
        self.task_queue.put(task)
        self.stats["total_tasks"] += 1

        logger.debug(
            f"任务已提�? {task_id}, 优先�? {priority.name}, "
            f"队列大小: {self.task_queue.size()}"
        )

        return task_id

    async def submit_task_async(
        self,
        task_id: str,
        func: Callable,
        args: tuple = (),
        kwargs: dict[str, Any] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        estimated_duration: float = 0.0,
        resource_requirements: dict[str, Any] = None,
    ) -> str:
        """异步提交任务"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.submit_task,
            task_id,
            func,
            args,
            kwargs,
            priority,
            estimated_duration,
            resource_requirements,
        )

    def _worker_loop(self):
        """工作线程循环"""
        while not self.shutdown_flag:
            try:
                # 从队列获取任�?
                task = self.task_queue.get(timeout=1.0)
                if task is None:
                    continue

                # 更新活跃工作线程�?
                with self.worker_lock:
                    self.active_workers += 1
                    current_concurrent = self.active_workers
                    self.stats["current_concurrent_tasks"] = current_concurrent
                    self.stats["peak_concurrent_tasks"] = max(
                        self.stats["peak_concurrent_tasks"], current_concurrent
                    )

                try:
                    # 执行任务
                    start_time = time.time()

                    # 添加任务元数据到kwargs
                    task.kwargs["_task_id"] = task.task_id
                    task.kwargs["_worker_thread"] = threading.current_thread().name

                    # 提交到线程池执行
                    future = self.executor.submit(task.func, *task.args, **task.kwargs)
                    future.result()  # 等待任务完成

                    # 更新统计信息
                    processing_time = time.time() - start_time
                    self._update_task_stats(processing_time, True)

                    logger.debug(
                        f"任务完成: {task.task_id}, 耗时: {processing_time:.3f}�?
                    )

                except Exception as e:
                    # 任务执行失败
                    processing_time = time.time() - start_time
                    self._update_task_stats(processing_time, False)
                    logger.error(f"任务执行失败: {task.task_id}, 错误: {e}")

                finally:
                    # 更新活跃工作线程�?
                    with self.worker_lock:
                        self.active_workers -= 1

            except Exception as e:
                logger.error(f"工作线程异常: {e}")

    def _update_task_stats(self, processing_time: float, success: bool):
        """更新任务统计信息"""
        if success:
            self.stats["completed_tasks"] += 1
        else:
            self.stats["failed_tasks"] += 1

        # 更新平均处理时间
        completed = self.stats["completed_tasks"]
        if completed > 0:
            current_avg = self.stats["average_processing_time"]
            new_avg = (current_avg * (completed - 1) + processing_time) / completed
            self.stats["average_processing_time"] = new_avg

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息"""
        stats = self.stats.copy()

        # 添加实时系统指标
        if self.resource_monitor:
            stats["system_metrics"] = self.resource_monitor.get_system_metrics()
            stats["optimal_concurrency"] = (
                self.resource_monitor.get_optimal_concurrency()
            )

        # 计算成功�?
        total = self.stats["total_tasks"]
        if total > 0:
            stats["success_rate"] = self.stats["completed_tasks"] / total
        else:
            stats["success_rate"] = 0.0

        # 计算队列状�?
        stats["queue_size"] = self.task_queue.size()
        stats["active_workers"] = self.active_workers
        stats["max_workers"] = self.max_workers

        return stats

    def get_health_status(self) -> dict[str, Any]:
        """获取健康状�?""
        stats = self.get_statistics()

        # 健康评分
        health_score = 100.0

        # 成功率检�?
        if stats["success_rate"] < 0.9:
            health_score -= 20

        # 资源拒绝检�?
        if stats.get("resource_rejections", 0) > 0:
            health_score -= 15

        # 队列积压检�?
        if stats["queue_size"] > 10:
            health_score -= 10

        # 系统资源检�?
        system_metrics = stats.get("system_metrics", {})
        if system_metrics:
            if system_metrics.get("cpu_percent", 0) > 90:
                health_score -= 15
            if system_metrics.get("memory_percent", 0) > 90:
                health_score -= 15

        # 确定健康等级
        if health_score >= 90:
            status = "excellent"
        elif health_score >= 75:
            status = "good"
        elif health_score >= 60:
            status = "fair"
        else:
            status = "poor"

        return {
            "status": status,
            "health_score": max(0, health_score),
            "uptime_seconds": stats.get("uptime_seconds", 0),
            "issues": self._identify_health_issues(stats),
        }

    def _identify_health_issues(self, stats: dict[str, Any]) -> list[str]:
        """识别健康问题"""
        issues = []

        if stats["success_rate"] < 0.8:
            issues.append(f"任务成功率过�?({stats['success_rate']:.1%})")

        if stats.get("resource_rejections", 0) > 5:
            issues.append("资源拒绝次数过多")

        if stats["queue_size"] > 20:
            issues.append("任务队列积压严重")

        system_metrics = stats.get("system_metrics", {})
        if system_metrics:
            if system_metrics.get("cpu_percent", 0) > 85:
                issues.append("CPU使用率过�?)
            if system_metrics.get("memory_percent", 0) > 85:
                issues.append("内存使用率过�?)

        return issues

    def force_garbage_collection(self):
        """强制垃圾回收"""
        try:
            collected = gc.collect()
            logger.info(f"强制垃圾回收完成，回收对象数: {collected}")
        except Exception as e:
            logger.error(f"垃圾回收失败: {e}")


class ResourceError(Exception):
    """资源不足异常"""

    pass


# 创建全局并发处理器实�?
concurrent_optimizer = ConcurrentProcessingOptimizer(
    max_workers=4, enable_monitoring=True, resource_aware=True
)
