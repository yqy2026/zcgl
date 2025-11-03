from typing import Any
"""
异步任务队列系统 - 支持后台任务处理
功能: 任务队列、任务调度、进度追踪、失败重试
时间: 2025-11-03
"""

import functools
import logging
import threading
import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from queue import PriorityQueue


logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """任务状态"""

    PENDING = "pending"  # 待处理
    PROCESSING = "processing"  # 处理中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败
    RETRYING = "retrying"  # 重试中


class TaskPriority(int, Enum):
    """任务优先级"""

    LOW = 3
    NORMAL = 2
    HIGH = 1
    CRITICAL = 0


@dataclass
class Task:
    """任务定义"""

    id: str
    func_name: str
    args: tuple = ()
    kwargs: dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.NORMAL
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    retry_count: int = 0
    max_retries: int = 3
    error_message: str | None = None
    progress: int = 0  # 0-100

    def __lt__(self, other):
        """用于优先级队列的比较"""
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        return self.created_at < other.created_at

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data["status"] = self.status.value
        data["priority"] = self.priority.value
        data["created_at"] = self.created_at.isoformat()
        if self.started_at:
            data["started_at"] = self.started_at.isoformat()
        if self.completed_at:
            data["completed_at"] = self.completed_at.isoformat()
        return data


class TaskQueue:
    """任务队列管理器"""

    def __init__(self, max_workers: int = 4):
        self.queue: PriorityQueue = PriorityQueue()
        self.tasks: dict[str, Task] = {}  # 任务存储
        self.max_workers = max_workers
        self.active_workers = 0
        self.worker_threads = []
        self.is_running = False
        self.callbacks: dict[str, Callable] = {}  # 任务处理函数

    def register_callback(self, func_name: str, func: Callable) -> None:
        """注册任务处理函数"""
        self.callbacks[func_name] = func
        logger.info(f"已注册任务处理函数: {func_name}")

    def submit_task(
        self,
        func_name: str,
        args: tuple = (),
        kwargs: dict | None = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        max_retries: int = 3,
    ) -> str:
        """
        提交任务到队列

        Returns:
            任务ID
        """
        if kwargs is None:
            kwargs = {}

        task = Task(
            id=str(uuid.uuid4()),
            func_name=func_name,
            args=args,
            kwargs=kwargs,
            priority=priority,
            max_retries=max_retries,
        )

        self.tasks[task.id] = task
        self.queue.put((task.priority.value, task.created_at, task))

        logger.info(f"✅ 任务已提交: {task.id} ({func_name})")
        return task.id

    def get_task_status(self, task_id: str) -> dict[str, Any] | None:
        """获取任务状态"""
        if task_id not in self.tasks:
            return None

        task = self.tasks[task_id]
        return {
            "id": task.id,
            "status": task.status.value,
            "progress": task.progress,
            "error": task.error_message,
        }

    def process_task(self, task: Task) -> bool:
        """处理单个任务"""
        try:
            task.status = TaskStatus.PROCESSING
            task.started_at = datetime.now()
            task.progress = 10

            # 获取处理函数
            if task.func_name not in self.callbacks:
                raise ValueError(f"未找到处理函数: {task.func_name}")

            func = self.callbacks[task.func_name]

            # 更新进度
            task.progress = 50

            # 执行函数
            func(*task.args, **task.kwargs)

            task.progress = 90
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            task.progress = 100

            logger.info(f"✅ 任务已完成: {task.id}")
            return True

        except Exception as e:
            task.error_message = str(e)

            # 重试逻辑
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = TaskStatus.RETRYING
                self.queue.put((task.priority.value, task.created_at, task))
                logger.warning(f"⚠️  任务重试: {task.id} (第{task.retry_count}次)")
                return False
            else:
                task.status = TaskStatus.FAILED
                logger.error(f"❌ 任务失败: {task.id} - {str(e)}")
                return False

    def worker(self) -> None:
        """工作线程"""
        while self.is_running:
            try:
                # 获取任务
                _, _, task = self.queue.get(timeout=1)

                # 处理任务
                self.process_task(task)

                self.queue.task_done()

            except Exception as e:
                if "Empty" not in str(type(e)):
                    logger.error(f"工作线程错误: {e}")

    def start(self) -> None:
        """启动任务队列"""
        if self.is_running:
            return

        self.is_running = True

        # 启动工作线程
        for i in range(self.max_workers):
            thread = threading.Thread(target=self.worker, daemon=True)
            thread.start()
            self.worker_threads.append(thread)

        logger.info(f"✅ 任务队列已启动 ({self.max_workers} 个工作线程)")

    def stop(self, wait: bool = True) -> None:
        """停止任务队列"""
        self.is_running = False

        if wait:
            self.queue.join()

        logger.info("✅ 任务队列已停止")

    def get_stats(self) -> dict[str, Any]:
        """获取队列统计"""
        pending = sum(1 for t in self.tasks.values() if t.status == TaskStatus.PENDING)
        processing = sum(
            1 for t in self.tasks.values() if t.status == TaskStatus.PROCESSING
        )
        completed = sum(
            1 for t in self.tasks.values() if t.status == TaskStatus.COMPLETED
        )
        failed = sum(1 for t in self.tasks.values() if t.status == TaskStatus.FAILED)

        return {
            "pending": pending,
            "processing": processing,
            "completed": completed,
            "failed": failed,
            "total": len(self.tasks),
            "queue_size": self.queue.qsize(),
        }


# 全局任务队列实例
_task_queue: TaskQueue | None = None


def get_task_queue() -> TaskQueue:
    """获取全局任务队列实例"""
    global _task_queue
    if _task_queue is None:
        _task_queue = TaskQueue(max_workers=4)
        _task_queue.start()
    return _task_queue


def async_task(
    priority: TaskPriority = TaskPriority.NORMAL, max_retries: int = 3
) -> Callable:
    """
    异步任务装饰器

    例子:
        @async_task(priority=TaskPriority.HIGH, max_retries=3)
        def process_pdf_import(file_path: str, org_id: str):
            # PDF处理逻辑
            pass

        # 异步执行
        task_id = submit_async_task(process_pdf_import, file_path, org_id)
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 同步调用，支持异步提交
            return func(*args, **kwargs)

        # 添加异步提交方法
        def submit_async(*args, **kwargs) -> str:
            queue = get_task_queue()
            queue.register_callback(func.__name__, func)
            return queue.submit_task(
                func_name=func.__name__,
                args=args,
                kwargs=kwargs,
                priority=priority,
                max_retries=max_retries,
            )

        # 使用一个字典来存储子函数
        wrapper_dict = vars(wrapper)  # type: ignore
        wrapper_dict["submit_async"] = submit_async
        return wrapper

    return decorator


def submit_task(
    func: Callable,
    *args,
    priority: TaskPriority = TaskPriority.NORMAL,
    max_retries: int = 3,
    **kwargs,
) -> str:
    """
    提交异步任务

    Args:
        func: 要执行的函数
        *args: 位置参数
        **kwargs: 关键字参数
        priority: 优先级
        max_retries: 最大重试次数

    Returns:
        任务ID
    """
    queue = get_task_queue()
    queue.register_callback(func.__name__, func)
    return queue.submit_task(
        func_name=func.__name__,
        args=args,
        kwargs=kwargs,
        priority=priority,
        max_retries=max_retries,
    )


def get_task_status(task_id: str) -> dict[str, Any] | None:
    """获取任务状态"""
    queue = get_task_queue()
    return queue.get_task_status(task_id)
