#!/usr/bin/env python3
"""
任务队列性能基准测试脚本
功能: 测试异步任务队列的性能和可靠性
时间: 2025-11-03
"""

import json
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.task_queue import TaskPriority, get_task_queue, submit_task


class TaskQueueBenchmark:
    """任务队列性能基准测试"""

    def __init__(self, num_tasks: int = 50):
        self.queue = get_task_queue()
        self.num_tasks = num_tasks
        self.test_results = {}

    def dummy_task(self, task_id: int, duration: float = 0.01) -> dict:
        """虚拟任务"""
        time.sleep(duration)
        return {
            "task_id": task_id,
            "completed_at": datetime.now().isoformat(),
            "status": "success"
        }

    def test_submission_performance(self) -> dict:
        """测试任务提交性能"""
        print("\n📝 测试1: 任务提交性能")

        # 注册回调
        self.queue.register_callback("dummy_task", self.dummy_task)

        submission_times = []
        task_ids = []

        start_total = time.time()
        for i in range(self.num_tasks):
            start = time.time()
            task_id = submit_task(
                self.dummy_task,
                task_id=i,
                duration=0.01,
                priority=TaskPriority.NORMAL
            )
            submission_times.append(time.time() - start)
            task_ids.append(task_id)

        total_time = time.time() - start_total

        return {
            "total_tasks": self.num_tasks,
            "total_time_s": total_time,
            "avg_submission_ms": statistics.mean(submission_times) * 1000,
            "min_submission_ms": min(submission_times) * 1000,
            "max_submission_ms": max(submission_times) * 1000,
            "tasks_per_second": self.num_tasks / total_time if total_time > 0 else 0,
            "task_ids": task_ids
        }

    def test_processing_performance(self, task_ids: list[str]) -> dict:
        """测试任务处理性能"""
        print("\n📝 测试2: 任务处理性能")

        # 等待任务处理
        max_wait = 30
        start_wait = time.time()

        completed = 0
        failed = 0

        while time.time() - start_wait < max_wait:
            completed = sum(
                1 for tid in task_ids
                if (task_status := self.queue.get_task_status(tid)) and
                   task_status.get('status') == 'completed'
            )

            if completed == len(task_ids):
                break

            time.sleep(0.5)

        wait_time = time.time() - start_wait

        return {
            "total_tasks": len(task_ids),
            "completed_tasks": completed,
            "wait_time_s": wait_time,
            "avg_time_per_task_ms": (wait_time / completed * 1000) if completed > 0 else 0,
            "completion_rate_percent": (completed / len(task_ids)) * 100
        }

    def test_priority_handling(self) -> dict:
        """测试优先级处理"""
        print("\n📝 测试3: 优先级处理")

        # 提交不同优先级的任务
        low_task = submit_task(
            self.dummy_task,
            task_id=100,
            duration=0.05,
            priority=TaskPriority.LOW
        )

        time.sleep(0.1)

        high_task = submit_task(
            self.dummy_task,
            task_id=101,
            duration=0.05,
            priority=TaskPriority.HIGH
        )

        # 等待执行
        time.sleep(2)

        high_status = self.queue.get_task_status(high_task)
        low_status = self.queue.get_task_status(low_task)

        return {
            "high_priority_completed": high_status['status'] == 'completed' if high_status else False,
            "low_priority_status": low_status['status'] if low_status else 'unknown'
        }

    def test_queue_stats(self) -> dict:
        """测试队列统计"""
        print("\n📝 测试4: 队列统计")

        stats = self.queue.get_stats()

        return {
            "pending": stats['pending'],
            "processing": stats['processing'],
            "completed": stats['completed'],
            "failed": stats['failed'],
            "total": stats['total']
        }

    def run_benchmark(self) -> dict:
        """执行所有基准测试"""
        print("=" * 70)
        print("🚀 开始任务队列性能基准测试")
        print(f"   任务数量: {self.num_tasks}")
        print(f"   工作线程: {self.queue.max_workers}")
        print("=" * 70)

        results = {
            "timestamp": datetime.now().isoformat(),
            "num_tasks": self.num_tasks,
            "tests": {}
        }

        try:
            # 测试1: 提交性能
            submission = self.test_submission_performance()
            results["tests"]["submission"] = submission
            print("   ✅ 提交性能测试完成")

            # 等待任务ID
            task_ids = submission['task_ids']

            # 测试2: 处理性能
            processing = self.test_processing_performance(task_ids)
            results["tests"]["processing"] = processing
            print("   ✅ 处理性能测试完成")

            # 测试3: 优先级
            priority = self.test_priority_handling()
            results["tests"]["priority"] = priority
            print("   ✅ 优先级测试完成")

            # 测试4: 统计
            stats = self.test_queue_stats()
            results["tests"]["stats"] = stats
            print("   ✅ 统计测试完成")

        except Exception as e:
            print(f"   ❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()
            return {}

        return results

    def print_results(self, results: dict):
        """打印测试结果"""
        print("\n" + "=" * 70)
        print("📊 任务队列性能基准测试结果")
        print("=" * 70)

        if not results:
            print("❌ 没有测试结果")
            return

        # 提交性能
        sub = results["tests"]["submission"]
        print("\n✍️  任务提交性能:")
        print(f"   总任务数: {sub['total_tasks']}")
        print(f"   总提交时间: {sub['total_time_s']:.2f}s")
        print(f"   平均提交: {sub['avg_submission_ms']:.4f}ms")
        print(f"   吞吐量: {sub['tasks_per_second']:.0f} 任务/秒")

        # 处理性能
        proc = results["tests"]["processing"]
        print("\n⚡ 任务处理性能:")
        print(f"   已完成: {proc['completed_tasks']}/{proc['total_tasks']}")
        print(f"   完成率: {proc['completion_rate_percent']:.1f}%")
        print(f"   等待时间: {proc['wait_time_s']:.2f}s")
        print(f"   平均处理: {proc['avg_time_per_task_ms']:.2f}ms/任务")

        # 优先级
        pri = results["tests"]["priority"]
        print("\n🎯 优先级处理:")
        print(f"   高优先级完成: {'✅' if pri['high_priority_completed'] else '❌'}")
        print(f"   低优先级状态: {pri['low_priority_status']}")

        # 统计
        stats = results["tests"]["stats"]
        print("\n📈 队列统计:")
        print(f"   待处理: {stats['pending']}")
        print(f"   处理中: {stats['processing']}")
        print(f"   已完成: {stats['completed']}")
        print(f"   失败: {stats['failed']}")

        print("\n" + "=" * 70)

    def save_results(self, results: dict):
        """保存测试结果"""
        if not results:
            return

        output_path = Path(__file__).parent.parent / "task_queue_benchmark_results.json"

        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"\n📁 结果已保存到: {output_path}")


def main():
    """主函数"""
    benchmark = TaskQueueBenchmark(num_tasks=50)
    results = benchmark.run_benchmark()
    benchmark.print_results(results)
    benchmark.save_results(results)

    print("\n💡 说明:")
    print("   - 测试任务提交的吞吐量")
    print("   - 测试任务处理的效率")
    print("   - 验证优先级机制")
    print("   - 统计队列性能")


if __name__ == "__main__":
    main()
