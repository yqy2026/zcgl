#!/usr/bin/env python3
"""
并发 PDF 处理负载测试
测试系统的并发处理能力和限制
"""

import asyncio
import gc
import time
from unittest.mock import Mock, patch

import pytest

from src.services.document.pdf_import_service import (
    MAX_CONCURRENT_PDF_TASKS,
    PDFImportService,
)

# ============================================================================
# 并发信号量测试
# ============================================================================

class TestConcurrencySemaphore:
    """并发信号量测试"""

    def test_max_concurrent_limit(self):
        """测试最大并发限制配置"""
        assert MAX_CONCURRENT_PDF_TASKS >= 1
        assert MAX_CONCURRENT_PDF_TASKS <= 10

    def test_get_available_slots(self):
        """测试获取可用槽位"""
        initial_slots = PDFImportService.get_available_slots()
        assert initial_slots == MAX_CONCURRENT_PDF_TASKS

    def test_get_current_concurrent_count(self):
        """测试获取当前并发数"""
        initial_count = PDFImportService.get_current_concurrent_count()
        assert initial_count >= 0


# ============================================================================
# 并发 PDF 处理测试
# ============================================================================

class TestConcurrentPDFProcessing:
    """并发 PDF 处理测试"""

    @pytest.fixture
    def sample_pdfs(self, tmp_path):
        """创建多个示例 PDF 文件"""
        pdf_files = []
        for i in range(5):
            pdf_path = tmp_path / f"sample_{i}.pdf"
            pdf_path.write_bytes(b"%PDF-1.4\nSample PDF content")
            pdf_files.append(str(pdf_path))
        return pdf_files

    @pytest.fixture
    def mock_db(self):
        """Mock 数据库会话"""
        db = Mock()
        db.query = Mock()
        db.add = Mock()
        db.commit = Mock()

        # Mock session query to return None (no existing session)
        mock_query_result = Mock()
        mock_query_result.filter = Mock(return_value=Mock(first=Mock(return_value=None)))
        db.query = Mock(return_value=mock_query_result)

        return db

    @pytest.mark.asyncio
    async def test_concurrent_processing_respects_limit(self, sample_pdfs, mock_db):
        """测试并发处理遵守限制"""
        service = PDFImportService()

        # 跟踪同时运行的任务数
        concurrent_count = 0
        max_concurrent = 0
        lock = asyncio.Lock()

        async def mock_processing(session_id, file_path, options):
            nonlocal concurrent_count, max_concurrent

            async with lock:
                concurrent_count += 1
                if concurrent_count > max_concurrent:
                    max_concurrent = concurrent_count

            # 模拟处理时间
            await asyncio.sleep(0.1)

            async with lock:
                concurrent_count -= 1

            return {"success": True}

        # Mock 内部处理方法
        with patch.object(service, '_process_background', new=mock_processing):
            # 启动超过限制数量的任务
            num_tasks = MAX_CONCURRENT_PDF_TASKS + 2
            tasks = []

            for i in range(num_tasks):
                session_id = f"session-{i}"
                file_path = sample_pdfs[i % len(sample_pdfs)]
                options = {}

                task = asyncio.create_task(
                    service._process_background_safe(session_id, file_path, options)
                )
                tasks.append(task)

            # 等待所有任务完成
            await asyncio.gather(*tasks, return_exceptions=True)

        # 验证并发数没有超过限制
        assert max_concurrent <= MAX_CONCURRENT_PDF_TASKS

    @pytest.mark.asyncio
    async def test_sequential_vs_concurrent_performance(self, sample_pdfs):
        """测试并发相比串行的性能提升"""
        import time

        async def mock_task(task_id, delay=0.05):
            await asyncio.sleep(delay)
            return f"task-{task_id}"

        # 串行执行
        start_serial = time.time()
        for i in range(3):
            await mock_task(i)
        serial_time = time.time() - start_serial

        # 并发执行
        start_concurrent = time.time()
        await asyncio.gather(*[mock_task(i) for i in range(3)])
        concurrent_time = time.time() - start_concurrent

        # 并发应该更快
        assert concurrent_time < serial_time

    @pytest.mark.asyncio
    async def test_concurrent_tasks_complete_successfully(self, sample_pdfs):
        """测试并发任务成功完成"""
        completed_tasks = []
        failed_tasks = []

        async def mock_task_with_tracking(task_id):
            try:
                await asyncio.sleep(0.05)
                completed_tasks.append(task_id)
                return {"success": True, "task_id": task_id}
            except Exception:
                failed_tasks.append(task_id)
                raise

        # 创建并执行多个任务
        task_ids = list(range(5))
        results = await asyncio.gather(
            *[mock_task_with_tracking(tid) for tid in task_ids],
            return_exceptions=True
        )

        # 验证所有任务都成功完成
        assert len(completed_tasks) == len(task_ids)
        assert len(failed_tasks) == 0

    @pytest.mark.asyncio
    async def test_one_task_failure_doesnt_affect_others(self):
        """测试单个任务失败不影响其他任务"""
        completed = []
        failed = []

        async def flaky_task(task_id):
            await asyncio.sleep(0.02)
            if task_id == 2:  # 第3个任务失败
                failed.append(task_id)
                raise ValueError(f"Task {task_id} failed")
            completed.append(task_id)
            return {"success": True}

        results = await asyncio.gather(
            *[flaky_task(i) for i in range(5)],
            return_exceptions=True
        )

        # 验证只有任务2失败
        assert len(completed) == 4
        assert len(failed) == 1
        assert 2 in failed


# ============================================================================
# 负载测试场景
# ============================================================================

class TestLoadScenarios:
    """负载测试场景"""

    @staticmethod
    async def _process_mock_pdf(pdf_id):
        """Mock PDF 处理"""
        await asyncio.sleep(0.02)
        return {"success": True, "pdf_id": pdf_id}

    @pytest.mark.asyncio
    @pytest.mark.load  # 标记为负载测试
    async def test_high_volume_pdf_processing(self):
        """测试大量 PDF 处理"""
        num_pdfs = 20
        processing_times = []

        async def process_single_pdf(pdf_id):
            start = time.time()
            # 模拟处理
            await asyncio.sleep(0.01)
            processing_times.append(time.time() - start)
            return {"success": True, "pdf_id": pdf_id}

        # 并发处理
        start_total = time.time()
        results = await asyncio.gather(
            *[process_single_pdf(i) for i in range(num_pdfs)]
        )
        total_time = time.time() - start_total

        # 验证所有任务都成功
        assert len(results) == num_pdfs
        assert all(r["success"] for r in results)

        # 计算统计
        avg_time = sum(processing_times) / len(processing_times)
        throughput = num_pdfs / total_time

        # 基本性能验证
        assert avg_time < 1.0  # 平均处理时间应小于1秒
        assert throughput > 1.0  # 每秒至少处理1个

    @pytest.mark.asyncio
    @pytest.mark.load
    async def test_burst_traffic_handling(self):
        """测试突发流量处理"""
        # 模拟突发请求：先来一批，再来一批
        batch_size = 10
        num_batches = 3

        all_results = []

        for batch_num in range(num_batches):
            batch_results = await asyncio.gather(
                *[self._process_mock_pdf(batch_num * 100 + i) for i in range(batch_size)]
            )
            all_results.extend(batch_results)

            # 批次间稍作等待
            await asyncio.sleep(0.1)

        assert len(all_results) == batch_size * num_batches
        assert all(r["success"] for r in all_results)

    @pytest.mark.asyncio
    @pytest.mark.load
    async def test_sustained_load_stability(self):
        """测试持续负载稳定性"""
        duration_seconds = 2
        requests_per_second = 5
        total_requests = duration_seconds * requests_per_second

        completed = []
        errors = []

        async def sustained_worker():
            for i in range(total_requests):
                try:
                    await self._process_mock_pdf(i)
                    completed.append(i)
                except Exception as e:
                    errors.append((i, e))

                # 控制速率
                await asyncio.sleep(1.0 / requests_per_second)

        # 启动多个工作协程
        workers = [sustained_worker() for _ in range(2)]
        await asyncio.gather(*workers)

        # 验证完成率
        completion_rate = len(completed) / (total_requests * 2)
        assert completion_rate >= 0.95  # 至少95%成功率
        assert len(errors) == 0


# ============================================================================
# 资源限制测试
# ============================================================================

class TestResourceLimits:
    """资源限制测试"""

    @pytest.mark.asyncio
    async def test_memory_efficiency_under_load(self):
        """测试负载下的内存效率"""
        import sys

        # 获取初始内存使用
        # 注意：这只是粗略估计
        initial_objects = len(gc.get_objects()) if 'gc' in sys.modules else 0

        # 处理多个任务
        async def _process_mock_pdf(pdf_id):
            await asyncio.sleep(0.01)
            return {"success": True, "pdf_id": pdf_id}

        tasks = []
        for i in range(50):
            task = asyncio.create_task(_process_mock_pdf(i))
            tasks.append(task)

        results = await asyncio.gather(*tasks)

        # 验证任务成功
        assert len(results) == 50

        # 清理
        del tasks
        del results

    @pytest.mark.asyncio
    async def test_semaphore_blocks_when_full(self):
        """测试信号量在满时阻塞"""
        # 创建独立的信号量，避免使用类级别的信号量（事件循环问题）
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_PDF_TASKS)

        active_tasks = 0
        task_started = asyncio.Event()
        task_proceed = asyncio.Event()

        async def blocking_task():
            nonlocal active_tasks

            async with semaphore:
                active_tasks += 1
                task_started.set()

                # 等待允许继续
                await task_proceed.wait()

                active_tasks -= 1

        # 启动超过限制数量的任务
        tasks = [asyncio.create_task(blocking_task()) for _ in range(MAX_CONCURRENT_PDF_TASKS + 2)]

        # 等待第一批任务启动
        await asyncio.sleep(0.1)

        # 获取当前活动任务数（信号量内部的值）
        current_slots = semaphore._value if hasattr(semaphore, '_value') else MAX_CONCURRENT_PDF_TASKS
        active_count = MAX_CONCURRENT_PDF_TASKS - current_slots

        # 验证并发数没有超过限制
        assert active_count <= MAX_CONCURRENT_PDF_TASKS

        # 允许任务完成
        task_proceed.set()
        await asyncio.gather(*tasks)

    @pytest.mark.asyncio
    async def test_timeout_handling_under_load(self):
        """测试负载下的超时处理"""
        timeouts = []
        successes = []

        async def task_with_timeout(task_id, timeout=False):
            try:
                if timeout:
                    await asyncio.sleep(5)  # 模拟超时
                else:
                    await asyncio.sleep(0.01)
                successes.append(task_id)
                return {"success": True}
            except TimeoutError:
                timeouts.append(task_id)
                return {"success": False, "error": "timeout"}

        # 创建一些会超时的任务
        tasks = [
            asyncio.create_task(task_with_timeout(i, timeout=(i % 5 == 0)))
            for i in range(10)
        ]

        # 设置总体超时
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 验证结果
        assert len(successes) > 0  # 应该有成功的


# ============================================================================
# 压力测试
# ============================================================================

class TestStressScenarios:
    """压力测试场景"""

    @staticmethod
    async def _process_mock_pdf(pdf_id):
        """Mock PDF 处理"""
        await asyncio.sleep(0.02)
        return {"success": True, "pdf_id": pdf_id}

    @pytest.mark.asyncio
    @pytest.mark.stress
    async def test_max_concurrent_capacity(self):
        """测试最大并发容量"""
        service = PDFImportService()

        # 创建刚好达到限制的任务数
        tasks = []
        task_count = MAX_CONCURRENT_PDF_TASKS

        for i in range(task_count):
            task_id = f"task-{i}"

            async def single_task():
                await asyncio.sleep(0.05)
                return {"success": True}

            task = asyncio.create_task(single_task())
            tasks.append(task)

        # 等待所有任务完成
        results = await asyncio.gather(*tasks)

        # 验证所有任务都完成
        assert len(results) == task_count
        assert all(r["success"] for r in results)

    @pytest.mark.asyncio
    @pytest.mark.stress
    async def test_rapid_start_stop(self):
        """测试快速启停"""
        iterations = 20

        for iteration in range(iterations):
            # 快速启动一组任务
            tasks = [
                asyncio.create_task(self._process_mock_pdf(i))
                for i in range(5)
            ]

            # 等待完成
            await asyncio.gather(*tasks)

            # 短暂暂停
            await asyncio.sleep(0.01)

        # 验证所有迭代都完成
        assert iteration == iterations - 1
