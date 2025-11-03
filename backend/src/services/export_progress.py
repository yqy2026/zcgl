"""
导出进度跟踪服务
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ExportStatus(str, Enum):
    """导出状态枚举"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExportProgressTracker:
    """导出进度跟踪器"""

    def __init__(self):
        # 在实际项目中，这应该使用Redis或数据库存储
        # 这里使用内存存储作为演示
        self._tasks: dict[str, dict[str, Any]] = {}
        self._cleanup_interval = 3600  # 1小时后清理完成的任务

    def create_task(
        self,
        total_records: int,
        filters: dict[str, Any] | None = None,
        format: str = "xlsx",
    ) -> str:
        """创建导出任务"""
        task_id = str(uuid.uuid4())

        task_info = {
            "task_id": task_id,
            "status": ExportStatus.PENDING,
            "progress": 0.0,
            "total_records": total_records,
            "processed_records": 0,
            "filters": filters or {},
            "format": format,
            "created_at": datetime.now().isoformat(),
            "started_at": None,
            "completed_at": None,
            "file_path": None,
            "file_name": None,
            "file_size": 0,
            "error_message": None,
            "estimated_completion": None,
        }

        self._tasks[task_id] = task_info
        logger.info(f"创建导出任务: {task_id}, 总记录数: {total_records}")

        return task_id

    def start_task(self, task_id: str) -> bool:
        """开始执行任务"""
        if task_id not in self._tasks:
            return False

        task = self._tasks[task_id]
        task["status"] = ExportStatus.PROCESSING
        task["started_at"] = datetime.now().isoformat()

        # 估算完成时间（假设每1000条记录需要1秒）
        estimated_seconds = max(1, task["total_records"] // 1000)
        estimated_completion = datetime.now() + timedelta(seconds=estimated_seconds)
        task["estimated_completion"] = estimated_completion.isoformat()

        logger.info(f"开始执行导出任务: {task_id}")
        return True

    def update_progress(
        self, task_id: str, processed_records: int, message: str | None = None
    ) -> bool:
        """更新任务进度"""
        if task_id not in self._tasks:
            return False

        task = self._tasks[task_id]
        task["processed_records"] = processed_records

        if task["total_records"] > 0:
            progress = min(100.0, (processed_records / task["total_records"]) * 100)
            task["progress"] = round(progress, 2)

        if message:
            task["message"] = message

        logger.debug(f"更新任务进度: {task_id}, 进度: {task['progress']}%")
        return True

    def complete_task(
        self,
        task_id: str,
        file_path: str,
        file_name: str,
        file_size: int,
        success: bool = True,
        error_message: str | None = None,
    ) -> bool:
        """完成任务"""
        if task_id not in self._tasks:
            return False

        task = self._tasks[task_id]
        task["status"] = ExportStatus.COMPLETED if success else ExportStatus.FAILED
        task["completed_at"] = datetime.now().isoformat()
        task["progress"] = 100.0 if success else task["progress"]

        if success:
            task["file_path"] = file_path
            task["file_name"] = file_name
            task["file_size"] = file_size

        if error_message:
            task["error_message"] = error_message

        logger.info(f"任务完成: {task_id}, 成功: {success}")
        return True

    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        if task_id not in self._tasks:
            return False

        task = self._tasks[task_id]
        if task["status"] in [ExportStatus.COMPLETED, ExportStatus.FAILED]:
            return False  # 已完成的任务不能取消

        task["status"] = ExportStatus.CANCELLED
        task["completed_at"] = datetime.now().isoformat()

        logger.info(f"取消导出任务: {task_id}")
        return True

    def get_task_status(self, task_id: str) -> Dict[str, Any] | None:
        """获取任务状态"""
        return self._tasks.get(task_id)

    def list_tasks(
        self, status: ExportStatus | None = None, limit: int = 50
    ) -> List[dict[str, Any]]:
        """列出任务"""
        tasks = list(self._tasks.values())

        if status:
            tasks = [task for task in tasks if task["status"] == status]

        # 按创建时间倒序排列
        tasks.sort(key=lambda x: x["created_at"], reverse=True)

        return tasks[:limit]

    def cleanup_old_tasks(self, max_age_hours: int = 24) -> int:
        """清理旧任务"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)

        tasks_to_remove = []
        for task_id, task in self._tasks.items():
            completed_at = task.get("completed_at")
            if completed_at:
                completed_time = datetime.fromisoformat(completed_at)
                if completed_time < cutoff_time:
                    tasks_to_remove.append(task_id)

        for task_id in tasks_to_remove:
            del self._tasks[task_id]

        logger.info(f"清理了 {len(tasks_to_remove)} 个旧任务")
        return len(tasks_to_remove)

    def get_task_statistics(self) -> Dict[str, Any]:
        """获取任务统计信息"""
        total_tasks = len(self._tasks)
        status_counts = {}

        for task in self._tasks.values():
            status = task["status"]
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "total_tasks": total_tasks,
            "status_distribution": status_counts,
            "active_tasks": status_counts.get(ExportStatus.PROCESSING, 0),
            "pending_tasks": status_counts.get(ExportStatus.PENDING, 0),
            "completed_tasks": status_counts.get(ExportStatus.COMPLETED, 0),
            "failed_tasks": status_counts.get(ExportStatus.FAILED, 0),
        }


# 全局进度跟踪器实例
export_progress_tracker = ExportProgressTracker()


async def track_export_progress(
    task_id: str, export_function, *args, **kwargs
) -> Dict[str, Any]:
    """
    包装导出函数以跟踪进度

    Args:
        task_id: 任务ID
        export_function: 导出函数
        *args, **kwargs: 导出函数的参数

    Returns:
        导出结果
    """
    try:
        # 开始任务
        export_progress_tracker.start_task(task_id)

        # 执行导出
        result = await export_function(*args, **kwargs)

        if result["success"]:
            # 完成任务
            export_progress_tracker.complete_task(
                task_id=task_id,
                file_path=result["file_path"],
                file_name=result["file_name"],
                file_size=result["file_size"],
                success=True,
            )
        else:
            # 任务失败
            export_progress_tracker.complete_task(
                task_id=task_id,
                file_path="",
                file_name="",
                file_size=0,
                success=False,
                error_message=result["message"],
            )

        # 添加任务ID到结果中
        result["task_id"] = task_id
        return result

    except Exception as e:
        # 处理异常
        export_progress_tracker.complete_task(
            task_id=task_id,
            file_path="",
            file_name="",
            file_size=0,
            success=False,
            error_message=str(e),
        )

        return {
            "success": False,
            "message": f"导出失败: {str(e)}",
            "task_id": task_id,
            "file_path": None,
            "stats": {"total_records": 0},
        }


def simulate_progress_updates(task_id: str, total_records: int):
    """
    模拟进度更新（在实际导出过程中调用）
    """

    async def update_progress():
        # 模拟分阶段进度更新
        stages = [
            (10, "正在查询数据..."),
            (30, "正在处理数据..."),
            (60, "正在生成Excel文件..."),
            (90, "正在保存文件..."),
            (100, "导出完成"),
        ]

        for progress, message in stages:
            processed = int((progress / 100) * total_records)
            export_progress_tracker.update_progress(task_id, processed, message)
            await asyncio.sleep(0.1)  # 模拟处理时间

    return update_progress
