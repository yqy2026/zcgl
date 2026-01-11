#!/usr/bin/env python3
"""
Unit tests for BatchStatusTracker
批处理状态追踪器单元测试
"""

import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.services.document.processing_tracker import BatchStatusTracker


class TestBatchStatusTracker:
    """BatchStatusTracker 测试套件"""

    def test_init_without_redis(self):
        """测试无 Redis 时的初始化"""
        tracker = BatchStatusTracker(redis_host=None)

        assert tracker._use_redis is False
        assert tracker._redis_client is None
        assert isinstance(tracker._fallback_store, dict)

    def test_init_with_redis_unavailable(self):
        """测试 Redis 不可用时回退到内存"""
        with patch('src.services.document.processing_tracker.REDIS_AVAILABLE', False):
            tracker = BatchStatusTracker(redis_host="localhost")

            assert tracker._use_redis is False
            assert tracker._redis_client is None

    def test_create_batch(self):
        """测试创建批处理记录"""
        tracker = BatchStatusTracker(redis_host=None)

        result = tracker.create_batch(
            batch_id="test-batch-001",
            total=5,
            user_id=123,
            organization_id=456,
        )

        assert result is True

        # 验证数据
        status = tracker.get_status("test-batch-001")
        assert status is not None
        assert status["batch_id"] == "test-batch-001"
        assert status["total"] == 5
        assert status["status"] == "pending"
        assert status["processed"] == 0
        assert status["failed"] == 0

    def test_get_status_nonexistent(self):
        """测试获取不存在的批处理状态"""
        tracker = BatchStatusTracker(redis_host=None)

        status = tracker.get_status("nonexistent-batch")
        assert status is None

    def test_update_progress(self):
        """测试更新进度"""
        tracker = BatchStatusTracker(redis_host=None)

        tracker.create_batch("test-batch-002", total=10)

        # 更新已处理数量
        result = tracker.update_progress("test-batch-002", processed=3)
        assert result is True

        status = tracker.get_status("test-batch-002")
        assert status["processed"] == 3

        # 更新失败数量
        result = tracker.update_progress("test-batch-002", failed=1)
        assert result is True

        status = tracker.get_status("test-batch-002")
        assert status["failed"] == 1

    def test_set_status(self):
        """测试设置状态"""
        tracker = BatchStatusTracker(redis_host=None)

        tracker.create_batch("test-batch-003", total=5)

        result = tracker.set_status("test-batch-003", "processing")
        assert result is True

        status = tracker.get_status("test-batch-003")
        assert status["status"] == "processing"

    def test_delete_batch(self):
        """测试删除批处理记录"""
        tracker = BatchStatusTracker(redis_host=None)

        tracker.create_batch("test-batch-004", total=5)
        assert tracker.get_status("test-batch-004") is not None

        result = tracker.delete_batch("test-batch-004")
        assert result is True

        assert tracker.get_status("test-batch-004") is None

    def test_list_batches(self):
        """测试列出批处理记录"""
        tracker = BatchStatusTracker(redis_host=None)

        tracker.create_batch("batch-1", total=5)
        tracker.create_batch("batch-2", total=10)
        tracker.create_batch("batch-3", total=15)

        # 设置不同状态
        tracker.set_status("batch-1", "completed")
        tracker.set_status("batch-2", "processing")
        tracker.set_status("batch-3", "failed")

        # 列出所有
        all_batches = tracker.list_batches()
        assert len(all_batches) == 3

        # 按状态过滤
        processing_batches = tracker.list_batches(status_filter="processing")
        assert len(processing_batches) == 1
        assert processing_batches[0]["batch_id"] == "batch-2"

        # 限制数量
        limited_batches = tracker.list_batches(limit=2)
        assert len(limited_batches) == 2

    def test_cleanup_old_batches(self):
        """测试清理旧批处理记录"""
        tracker = BatchStatusTracker(redis_host=None)

        # 创建两个批处理记录
        tracker.create_batch("old-batch", total=5)
        tracker.create_batch("new-batch", total=5)

        # 手动修改创建时间（模拟旧记录）
        import time
        old_batch = tracker._fallback_store["old-batch"]
        old_batch["created_at"] = "2020-01-01T00:00:00"

        # 清理超过 1 小时的记录
        cleaned = tracker.cleanup_old_batches(older_than_hours=1)
        assert cleaned >= 1

        # 旧记录应该被清理
        assert tracker.get_status("old-batch") is None

    def test_get_stats(self):
        """测试获取统计信息"""
        tracker = BatchStatusTracker(redis_host=None)

        tracker.create_batch("batch-1", total=5)
        tracker.set_status("batch-1", "processing")

        tracker.create_batch("batch-2", total=5)
        tracker.set_status("batch-2", "completed")

        stats = tracker.get_stats()

        assert stats["storage_type"] == "memory"
        assert stats["total_batches"] == 2
        assert stats["active_batches"] == 1
        assert stats["completed_batches"] == 1

    @pytest.mark.asyncio
    async def test_concurrent_operations(self):
        """测试并发操作"""
        tracker = BatchStatusTracker(redis_host=None)

        # 创建批处理
        tracker.create_batch("concurrent-batch", total=100)

        # 模拟并发更新
        async def update_progress():
            for i in range(10):
                tracker.update_progress("concurrent-batch", processed=1)
                await asyncio.sleep(0.01)

        # 并发执行多个更新任务
        tasks = [update_progress() for _ in range(5)]
        await asyncio.gather(*tasks)

        # 验证最终状态
        status = tracker.get_status("concurrent-batch")
        assert status["processed"] == 50  # 5个任务 * 10次更新

    def test_update_progress_nonexistent_batch(self):
        """测试更新不存在的批处理"""
        tracker = BatchStatusTracker(redis_host=None)

        result = tracker.update_progress("nonexistent", processed=1)
        assert result is False

    def test_set_status_with_completed_timestamp(self):
        """测试设置完成状态时添加时间戳"""
        tracker = BatchStatusTracker(redis_host=None)

        tracker.create_batch("test-batch-005", total=5)
        tracker.set_status("test-batch-005", "completed")

        status = tracker.get_status("test-batch-005")
        assert status["status"] == "completed"
        assert "completed_at" in status

    def test_list_batches_with_custom_limit(self):
        """测试自定义限制列出批处理"""
        tracker = BatchStatusTracker(redis_host=None)

        # 创建多个批处理
        for i in range(15):
            tracker.create_batch(f"batch-{i}", total=i + 1)

        # 限制返回 10 个
        batches = tracker.list_batches(limit=10)
        assert len(batches) == 10

    def test_get_status_returns_integers(self):
        """测试 get_status 返回整数类型的数值"""
        tracker = BatchStatusTracker(redis_host=None)

        tracker.create_batch("test-batch-006", total=10)
        tracker.update_progress("test-batch-006", processed=5, failed=2)

        status = tracker.get_status("test-batch-006")

        # 确保数值类型为 int（不是 str）
        assert isinstance(status["total"], int)
        assert isinstance(status["processed"], int)
        assert isinstance(status["failed"], int)
        assert status["total"] == 10
        assert status["processed"] == 5
        assert status["failed"] == 2
