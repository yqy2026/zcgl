from typing import Any
"""
并行PDF处理器
提供多任务并行处理和智能缓存优化
"""

import asyncio
import hashlib
import json
import logging
import os
import pickle
import queue
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps


logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """任务优先级"""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


class CacheStrategy(Enum):
    """缓存策略"""

    MEMORY_ONLY = "memory_only"
    DISK_PERSISTENT = "disk_persistent"
    DISTRIBUTED = "distributed"


@dataclass
class ProcessingTask:
    """处理任务"""

    task_id: str
    file_path: str
    priority: TaskPriority
    processing_options: dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    status: str = "pending"  # pending, processing, completed, failed, cancelled
    result: dict[str, Any] | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CacheEntry:
    """缓存条目"""

    key: str
    value: Any
    created_at: datetime
    expires_at: datetime
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.now)
    size_bytes: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class ParallelPDFProcessor:
    """并行PDF处理器"""

    def __init__(self, max_workers: int = 4, max_cache_size: int = 1000):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.task_queue = asyncio.Queue()
        self.active_tasks: dict[str, asyncio.Task] = {}
        self.completed_tasks: list[ProcessingTask] = []

        # 缓存系统
        self.memory_cache: dict[str, CacheEntry] = {}
        self.max_cache_size = max_cache_size
        self.cache_hits = 0
        self.cache_misses = 0

        # 线程安全
        self._cache_lock = threading.RLock()
        self._queue_lock = threading.Lock()

        # 统计信息
        self.stats = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "avg_processing_time": 0.0,
            "cache_hit_rate": 0.0,
            "parallel_efficiency": 0.0,
        }

    def _generate_cache_key(
        self, file_path: str, processing_options: dict[str, Any]
    ) -> str:
        """生成缓存键"""
        # 使用文件路径和关键处理选项生成唯一键
        file_stat = os.stat(file_path)
        file_hash = f"{file_path}_{file_stat.st_size}_{file_stat.st_mtime}"

        # 添加关键处理选项到键中
        key_options = {
            "prefer_ocr": processing_options.get("prefer_ocr", False),
            "enable_chinese_optimization": processing_options.get(
                "enable_chinese_optimization", True
            ),
            "confidence_threshold": processing_options.get("confidence_threshold", 0.7),
            "enable_multi_engine_fusion": processing_options.get(
                "enable_multi_engine_fusion", True
            ),
        }

        options_str = json.dumps(key_options, sort_keys=True)
        combined = f"{file_hash}_{options_str}"

        # 生成哈希
        return hashlib.md5(combined.encode()).hexdigest()

    def _get_from_cache(self, cache_key: str) -> Any | None:
        """从缓存获取数据"""
        with self._cache_lock:
            entry = self.memory_cache.get(cache_key)

            if entry is None:
                self.cache_misses += 1
                return None

            # 检查是否过期
            if datetime.now() > entry.expires_at:
                del self.memory_cache[cache_key]
                self.cache_misses += 1
                return None

            # 更新访问统计
            entry.access_count += 1
            entry.last_accessed = datetime.now()
            self.cache_hits += 1

            return entry.value

    def _set_cache(
        self,
        cache_key: str,
        value: Any,
        ttl_minutes: int = 60,
        metadata: dict[str, Any] | None = None,
    ):
        """设置缓存数据"""
        with self._cache_lock:
            expires_at = datetime.now() + timedelta(minutes=ttl_minutes)

            # 计算值的大小（近似）
            try:
                size_bytes = len(pickle.dumps(value))
            except (Exception, pickle.PickleError, TypeError):
                # 序列化失败时使用字符串长度
                size_bytes = len(str(value).encode())

            entry = CacheEntry(
                key=cache_key,
                value=value,
                created_at=datetime.now(),
                expires_at=expires_at,
                size_bytes=size_bytes,
                metadata=metadata or {},
            )

            # 检查缓存大小限制
            self._evict_if_needed()

            self.memory_cache[cache_key] = entry

    def _evict_if_needed(self):
        """如果需要，驱逐最旧的缓存条目"""
        if len(self.memory_cache) <= self.max_cache_size:
            return

        # 按最后访问时间排序，删除最旧的条目
        sorted_items = sorted(
            self.memory_cache.items(), key=lambda item: item[1].last_accessed
        )

        # 删除最旧的条目直到缓存大小合适
        while len(self.memory_cache) > self.max_cache_size * 0.8:
            oldest_key = sorted_items[0][0]
            del self.memory_cache[oldest_key]
            sorted_items = sorted_items[1:]

    def _calculate_task_score(self, task: ProcessingTask) -> float:
        """计算任务优先级分数"""
        priority_score = task.priority.value * 10

        # 时间因素：越新的任务分数越高
        age_hours = (datetime.now() - task.created_at).total_seconds() / 3600
        time_score = max(0, 10 - age_hours)

        # 文件大小因素：小文件优先
        try:
            file_size_mb = os.path.getsize(task.file_path) / (1024 * 1024)
            size_score = max(0, 5 - file_size_mb)
        except (Exception, OSError, FileNotFoundError):
            # 文件操作失败时使用默认分数
            size_score = 2.5

        return priority_score + time_score + size_score

    async def submit_task(
        self,
        file_path: str,
        processing_options: dict[str, Any],
        priority: TaskPriority = TaskPriority.NORMAL,
    ) -> str:
        """提交处理任务"""
        task_id = f"task_{int(time.time() * 1000)}_{os.path.basename(file_path)}"

        task = ProcessingTask(
            task_id=task_id,
            file_path=file_path,
            priority=priority,
            processing_options=processing_options,
        )

        # 检查缓存
        cache_key = self._generate_cache_key(file_path, processing_options)
        cached_result = self._get_from_cache(cache_key)

        if cached_result:
            task.status = "completed"
            task.result = cached_result
            task.completed_at = datetime.now()
            task.metadata["cache_hit"] = True
            self.completed_tasks.append(task)
            logger.info(f"缓存命中: {file_path}")
            return task_id

        # 添加到队列
        await self.task_queue.put(task)
        self.stats["total_tasks"] += 1

        logger.info(f"任务提交: {task_id}, 文件: {file_path}, 优先级: {priority.name}")
        return task_id

    async def process_task(self, task: ProcessingTask) -> ProcessingTask:
        """处理单个任务"""
        task.status = "processing"
        task.started_at = datetime.now()

        try:
            # 这里调用实际的PDF处理逻辑
            from .enhanced_pdf_processor import enhanced_pdf_processor

            # 执行PDF处理
            result = await enhanced_pdf_processor.process_with_enhanced_config(
                file_path=task.file_path,
                custom_config=None,  # 使用任务中的处理选项
            )

            if result.get("success"):
                task.status = "completed"
                task.result = result
                task.completed_at = datetime.now()

                # 缓存结果
                cache_key = self._generate_cache_key(
                    task.file_path, task.processing_options
                )
                self._set_cache(
                    cache_key=cache_key,
                    value=result,
                    ttl_minutes=120,  # 2小时缓存
                    metadata={
                        "task_id": task.task_id,
                        "file_path": task.file_path,
                        "processing_options": task.processing_options,
                    },
                )

                logger.info(f"任务完成: {task.task_id}")
            else:
                task.status = "failed"
                task.error = result.get("error", "处理失败")

        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            logger.error(f"任务处理失败: {task.task_id}, 错误: {str(e)}")

        return task

    async def worker_loop(self):
        """工作线程循环"""
        while True:
            try:
                # 从队列获取任务
                task = await self.task_queue.get()

                # 处理任务
                processed_task = await self.process_task(task)

                # 添加到完成列表
                self.completed_tasks.append(processed_task)
                self.stats["completed_tasks"] += 1

                # 如果任务失败，增加失败计数
                if processed_task.status == "failed":
                    self.stats["failed_tasks"] += 1

                # 更新平均处理时间
                self._update_stats()

            except Exception as e:
                logger.error(f"工作线程错误: {str(e)}")
                await asyncio.sleep(1)  # 避免无限循环

    def _update_stats(self):
        """更新统计信息"""
        if not self.completed_tasks:
            return

        # 计算平均处理时间
        completed_tasks = [t for t in self.completed_tasks if t.status == "completed"]
        if completed_tasks:
            total_time = sum(
                (t.completed_at - t.started_at).total_seconds() for t in completed_tasks
            )
            self.stats["avg_processing_time"] = total_time / len(completed_tasks)

        # 计算缓存命中率
        total_requests = self.cache_hits + self.cache_misses
        if total_requests > 0:
            self.stats["cache_hit_rate"] = self.cache_hits / total_requests

        # 计算并行效率
        if self.stats["total_tasks"] > 0:
            self.stats["parallel_efficiency"] = (
                len(self.completed_tasks) / self.stats["total_tasks"]
            )

    async def process_batch(
        self,
        file_paths: list[str],
        processing_options: dict[str, Any] = None,
        max_concurrent: int | None = None,
    ) -> list[ProcessingTask]:
        """批量处理文件"""
        processing_options = processing_options or {}
        max_concurrent = max_concurrent or min(len(file_paths), self.max_workers)

        # 创建任务
        tasks = []
        for file_path in file_paths:
            task_id = await self.submit_task(file_path, processing_options)
            tasks.append(task_id)

        # 等待所有任务完成
        results = []
        for task_id in tasks:
            # 轮询任务状态
            while True:
                task = next(
                    (t for t in self.completed_tasks if t.task_id == task_id), None
                )
                if task and task.status in ["completed", "failed"]:
                    results.append(task)
                    break
                await asyncio.sleep(0.5)

        return results

    def get_task_status(self, task_id: str) -> ProcessingTask | None:
        """获取任务状态"""
        # 在活跃任务中查找
        for task in self.completed_tasks:
            if task.task_id == task_id:
                return task

        return None

    def get_queue_status(self) -> dict[str, Any]:
        """获取队列状态"""
        return {
            "queue_size": self.task_queue.qsize(),
            "active_tasks": len(self.active_tasks),
            "completed_tasks": len(self.completed_tasks),
            "max_workers": self.max_workers,
        }

    def get_cache_stats(self) -> dict[str, Any]:
        """获取缓存统计"""
        with self._cache_lock:
            total_entries = len(self.memory_cache)
            total_size = sum(entry.size_bytes for entry in self.memory_cache.values())

            return {
                "total_entries": total_entries,
                "total_size_bytes": total_size,
                "total_size_mb": total_size / (1024 * 1024),
                "hit_rate": self.stats["cache_hit_rate"],
                "max_entries": self.max_cache_size,
                "oldest_entry": min(
                    (
                        entry.created_at.isoformat()
                        for entry in self.memory_cache.values()
                    ),
                    default=None,
                )
                if self.memory_cache
                else None,
            }

    def get_performance_stats(self) -> dict[str, Any]:
        """获取性能统计"""
        return {
            **self.stats,
            "queue_status": self.get_queue_status(),
            "cache_stats": self.get_cache_stats(),
            "timestamp": datetime.now().isoformat(),
        }

    def clear_cache(self):
        """清空缓存"""
        with self._cache_lock:
            cleared_count = len(self.memory_cache)
            self.memory_cache.clear()
            logger.info(f"缓存已清空，清理了 {cleared_count} 个条目")

    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        # 这里可以实现任务取消逻辑
        # 由于使用线程池，任务取消比较复杂
        # 这里只是简单的标记实现
        return False

    def shutdown(self):
        """关闭处理器"""
        logger.info("正在关闭并行PDF处理器...")

        # 关闭线程池
        self.executor.shutdown(wait=True)

        # 清空队列
        while not self.task_queue.empty():
            try:
                self.task_queue.get_nowait(timeout=1)
            except (Exception, queue.Empty, OSError):
                # 队列操作完成时退出循环
                break

        logger.info("并行PDF处理器已关闭")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()


# 缓存装饰器
def cached_result(
    ttl_minutes: int = 60, cache_strategy: CacheStrategy = CacheStrategy.MEMORY_ONLY
):
    """缓存结果装饰器"""

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = f"{func.__name__}_{hash(str(args) + str(kwargs))}"

            # 全局处理器实例
            processor = get_parallel_processor()

            # 尝试从缓存获取
            cached = processor._get_from_cache(cache_key)
            if cached:
                logger.debug(f"缓存命中: {func.__name__}")
                return cached

            # 执行函数
            result = await func(*args, **kwargs)

            # 存入缓存
            processor._set_cache(
                cache_key=cache_key, value=result, ttl_minutes=ttl_minutes
            )

            return result

        return wrapper

    return decorator


# 全局处理器实例
_global_processor: ParallelPDFProcessor | None = None


def get_parallel_processor() -> ParallelPDFProcessor:
    """获取全局并行处理器实例"""
    global _global_processor
    if _global_processor is None:
        _global_processor = ParallelPDFProcessor()
        # 启动工作线程
        for _ in range(_global_processor.max_workers):
            asyncio.create_task(_global_processor.worker_loop())
    return _global_processor


# 便捷函数
async def process_pdf_parallel(
    file_path: str,
    processing_options: dict[str, Any] = None,
    priority: TaskPriority = TaskPriority.NORMAL,
) -> str:
    """并行处理PDF文件"""
    processor = get_parallel_processor()
    return await processor.submit_task(file_path, processing_options or {}, priority)


async def process_batch_parallel(
    file_paths: list[str], processing_options: dict[str, Any] = None
) -> list[ProcessingTask]:
    """并行批量处理PDF文件"""
    processor = get_parallel_processor()
    return await processor.process_batch(file_paths, processing_options)


def clear_pdf_cache():
    """清空PDF缓存"""
    processor = get_parallel_processor()
    processor.clear_cache()


def get_processing_stats() -> dict[str, Any]:
    """获取处理统计信息"""
    processor = get_parallel_processor()
    return processor.get_performance_stats()
