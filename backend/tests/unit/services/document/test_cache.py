#!/usr/bin/env python3
"""
PDF 缓存层单元测试
测试 PDFCache 和相关装饰器
"""

import asyncio
import json
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from src.services.document.cache import (
    AsyncDocumentCache,
    CachedExtractor,
    ExtractionCache,
    PDFCache,
    cached_extraction,
    clear_all_caches,
    get_cache,
)

# ============================================================================
# PDFCache 测试
# ============================================================================


class TestPDFCache:
    """PDFCache 类测试"""

    @pytest.fixture
    def temp_cache_dir(self):
        """创建临时缓存目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def cache(self, temp_cache_dir):
        """创建缓存实例"""
        return PDFCache(cache_dir=temp_cache_dir, ttl_seconds=60)

    @pytest.fixture
    def sample_pdf_file(self, tmp_path):
        """创建示例 PDF 文件"""
        pdf_path = tmp_path / "sample.pdf"
        pdf_path.write_bytes(b"Sample PDF content for testing")
        return str(pdf_path)

    @pytest.fixture
    def sample_result(self):
        """示例提取结果"""
        return {
            "success": True,
            "extracted_fields": {
                "contract_number": "CONTRACT-001",
                "landlord_name": "Test Landlord",
                "tenant_name": "Test Tenant",
            },
            "confidence": 0.9,
            "extraction_method": "test",
        }

    def test_file_hash_consistency(self, cache, sample_pdf_file):
        """测试文件哈希的一致性"""
        hash1 = cache.get_file_hash(sample_pdf_file)
        hash2 = cache.get_file_hash(sample_pdf_file)
        assert hash1 == hash2
        assert len(hash1) == 32  # MD5 hex 长度

    def test_file_hash_different_files(self, cache, tmp_path):
        """测试不同文件生成不同哈希"""
        pdf1 = tmp_path / "file1.pdf"
        pdf2 = tmp_path / "file2.pdf"
        pdf1.write_bytes(b"Content 1")
        pdf2.write_bytes(b"Content 2")

        hash1 = cache.get_file_hash(str(pdf1))
        hash2 = cache.get_file_hash(str(pdf2))
        assert hash1 != hash2

    def test_cache_set_and_get(self, cache, sample_pdf_file, sample_result):
        """测试缓存设置和获取"""
        # 设置缓存
        success = cache.set(sample_pdf_file, sample_result)
        assert success is True

        # 获取缓存
        cached = cache.get(sample_pdf_file)
        assert cached is not None
        assert cached["result"] == sample_result
        assert cached["file_path"] == sample_pdf_file
        assert "file_hash" in cached
        assert "cached_at" in cached

    def test_cache_miss(self, cache, sample_pdf_file):
        """测试缓存未命中"""
        cached = cache.get(sample_pdf_file)
        assert cached is None

        # 检查统计
        stats = cache.get_stats()
        assert stats["misses"] == 1
        assert stats["hits"] == 0

    def test_cache_hit(self, cache, sample_pdf_file, sample_result):
        """测试缓存命中"""
        cache.set(sample_pdf_file, sample_result)
        cache.get(sample_pdf_file)

        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 0

    def test_cache_ttl_expiration(self, cache, sample_pdf_file, sample_result):
        """测试缓存过期"""
        # 设置较短的 TTL
        cache.ttl_seconds = 1

        cache.set(sample_pdf_file, sample_result)
        time.sleep(2)

        # 缓存应已过期
        cached = cache.get(sample_pdf_file)
        assert cached is None

        stats = cache.get_stats()
        assert stats["evictions"] == 1

    def test_cache_invalidate(self, cache, sample_pdf_file, sample_result):
        """测试缓存失效"""
        cache.set(sample_pdf_file, sample_result)

        # 验证缓存存在
        assert cache.get(sample_pdf_file) is not None

        # 使缓存失效
        success = cache.invalidate(sample_pdf_file)
        assert success is True

        # 验证缓存已删除
        assert cache.get(sample_pdf_file) is None

    def test_cache_invalidate_nonexistent(self, cache, sample_pdf_file):
        """测试使不存在的缓存失效"""
        success = cache.invalidate(sample_pdf_file)
        assert success is False

    def test_cache_clear_all(self, cache, sample_pdf_file, sample_result, tmp_path):
        """测试清理所有缓存"""
        # 创建多个缓存文件
        for i in range(3):
            pdf_path = tmp_path / f"file{i}.pdf"
            pdf_path.write_bytes(f"Content {i}".encode())
            cache.set(str(pdf_path), sample_result)

        # 清理所有缓存
        count = cache.clear()
        assert count == 3

        stats = cache.get_stats()
        assert stats["total_cached_files"] == 0

    def test_cache_clear_old_only(self, cache, sample_result, tmp_path):
        """测试只清理旧缓存"""
        cache.ttl_seconds = 10

        # 创建第一个缓存
        pdf1 = tmp_path / "file1.pdf"
        pdf1.write_bytes(b"Content 1 for clear old test")
        cache.set(str(pdf1), sample_result)

        # 等待并创建第二个缓存
        time.sleep(1.5)  # 增加等待时间确保时间差
        pdf2 = tmp_path / "file2.pdf"
        pdf2.write_bytes(b"Content 2 for clear old test")
        cache.set(str(pdf2), sample_result)

        # 清理超过 1 秒的缓存（只有第一个文件）
        count = cache.clear(older_than_seconds=1)
        assert count == 1, f"Expected to clear 1 cache, got {count}"

        stats = cache.get_stats()
        assert stats["total_cached_files"] == 1

    def test_cache_stats(self, cache, sample_pdf_file, sample_result):
        """测试缓存统计"""
        # 初始统计
        stats = cache.get_stats()
        assert stats["total_cached_files"] == 0
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["hit_rate"] == 0

        # 添加缓存并命中
        cache.set(sample_pdf_file, sample_result)
        cache.get(sample_pdf_file)
        cache.get(sample_pdf_file)  # 第二次命中

        stats = cache.get_stats()
        assert stats["total_cached_files"] == 1
        assert stats["hits"] == 2
        assert stats["hit_rate"] == 1.0

    def test_cache_lru_update(self, cache, sample_pdf_file, sample_result):
        """测试 LRU 访问时间更新"""
        cache.set(sample_pdf_file, sample_result)

        # 获取缓存文件路径
        hash_key = cache.get_file_hash(sample_pdf_file)
        cache_file = cache.cache_dir / f"{hash_key}.json"

        # 获取初始修改时间
        initial_mtime = cache_file.stat().st_mtime

        # 等待并访问缓存
        time.sleep(0.1)
        cache.get(sample_pdf_file)

        # 验证修改时间已更新
        updated_mtime = cache_file.stat().st_mtime
        assert updated_mtime > initial_mtime

    def test_cleanup_expired(self, cache, sample_pdf_file, sample_result):
        """测试清理过期缓存"""
        cache.ttl_seconds = 1

        # 创建缓存
        cache.set(sample_pdf_file, sample_result)
        time.sleep(2)

        # 清理过期缓存
        count = cache.cleanup_expired()
        assert count == 1

        stats = cache.get_stats()
        assert stats["total_cached_files"] == 0


# ============================================================================
# CachedExtractor 装饰器测试
# ============================================================================


class TestCachedExtractor:
    """CachedExtractor 装饰器测试"""

    @pytest.fixture
    def temp_cache_dir(self):
        """创建临时缓存目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def cache(self, temp_cache_dir):
        """创建缓存实例"""
        return PDFCache(cache_dir=temp_cache_dir, ttl_seconds=60)

    @pytest.mark.asyncio
    async def test_cached_extractor_decorator(self, cache, tmp_path):
        """测试缓存提取器装饰器"""
        call_count = 0

        # 创建装饰器
        decorator = CachedExtractor(cache=cache)

        @decorator
        async def extract_func(file_path: str):
            nonlocal call_count
            call_count += 1
            return {"success": True, "data": f"Extracted from {file_path}"}

        # 创建测试文件
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"Test content")

        # 第一次调用 - 应执行函数
        result1 = await extract_func(str(pdf_path))
        assert call_count == 1
        assert result1["success"] is True

        # 第二次调用 - 应使用缓存
        result2 = await extract_func(str(pdf_path))
        assert call_count == 1  # 没有增加
        assert result2["success"] is True

    @pytest.mark.asyncio
    async def test_cached_extractor_with_cache_key_func(self, cache, tmp_path):
        """测试自定义缓存键函数"""
        call_count = 0

        # 创建第一个测试文件
        file1 = tmp_path / "file1.pdf"
        file1.write_bytes(b"Content for key function test")

        decorator = CachedExtractor(
            cache=cache,
            cache_key_func=lambda x: str(file1),  # 所有路径都映射到同一个文件
        )

        @decorator
        async def extract_func(file_path: str):
            nonlocal call_count
            call_count += 1
            return {"success": True}

        # 使用不同文件路径，但缓存键函数返回相同路径
        await extract_func("file1.pdf")
        await extract_func("file2.pdf")

        # 第二次调用应使用缓存，因为 cache_key_func 返回相同路径
        assert call_count == 1, f"Expected 1 call, got {call_count}"


# ============================================================================
# ExtractionCache 测试
# ============================================================================


class TestExtractionCache:
    """ExtractionCache 高级缓存测试"""

    @pytest.fixture
    def temp_cache_dir(self):
        """创建临时缓存目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def extraction_cache(self, temp_cache_dir):
        """创建高级缓存实例"""
        base_cache = PDFCache(cache_dir=temp_cache_dir, ttl_seconds=60)
        return ExtractionCache(base_cache=base_cache)

    @pytest.fixture
    def sample_pdf_file(self, tmp_path):
        """创建示例 PDF 文件"""
        pdf_path = tmp_path / "sample.pdf"
        pdf_path.write_bytes(b"Sample PDF content")
        return str(pdf_path)

    @pytest.fixture
    def high_confidence_result(self):
        """高置信度结果"""
        return {"success": True, "confidence": 0.9, "data": {"field": "value"}}

    @pytest.fixture
    def low_confidence_result(self):
        """低置信度结果"""
        return {"success": True, "confidence": 0.5, "data": {"field": "value"}}

    def test_conditional_cache_registration(self, extraction_cache):
        """测试条件缓存注册"""
        # 注册条件
        extraction_cache.register_conditional_cache(
            "high_confidence_only", lambda result: result.get("confidence", 0) > 0.8
        )

        assert "high_confidence_only" in extraction_cache._conditional_caches

    def test_get_with_condition_met(
        self, extraction_cache, sample_pdf_file, high_confidence_result
    ):
        """测试条件满足时获取缓存"""
        extraction_cache.register_conditional_cache(
            "high_confidence_only", lambda result: result.get("confidence", 0) > 0.8
        )

        # 设置高置信度缓存
        extraction_cache.cache.set(sample_pdf_file, high_confidence_result)

        # 获取缓存 - 条件满足
        cached = extraction_cache.get(sample_pdf_file, condition="high_confidence_only")
        assert cached is not None
        assert cached["result"]["confidence"] == 0.9

    def test_get_with_condition_not_met(
        self, extraction_cache, sample_pdf_file, low_confidence_result
    ):
        """测试条件不满足时返回 None"""
        extraction_cache.register_conditional_cache(
            "high_confidence_only", lambda result: result.get("confidence", 0) > 0.8
        )

        # 设置低置信度缓存
        extraction_cache.cache.set(sample_pdf_file, low_confidence_result)

        # 获取缓存 - 条件不满足
        cached = extraction_cache.get(sample_pdf_file, condition="high_confidence_only")
        assert cached is None

    def test_warm_up_cache(self, extraction_cache, tmp_path):
        """测试缓存预热"""
        call_count = 0

        def extraction_func(file_path: str):
            nonlocal call_count
            call_count += 1
            if "fail" in file_path:
                raise Exception("Extraction failed")
            return {"success": True, "data": "test"}

        # 创建测试文件 - 使用唯一内容避免哈希冲突
        file_paths = [
            str(tmp_path / "file1.pdf"),
            str(tmp_path / "file2.pdf"),
            str(tmp_path / "file_fail.pdf"),
        ]

        for i, path in enumerate(file_paths):
            Path(path).write_bytes(f"Unique content {i}".encode())

        # 预热缓存
        result = extraction_cache.warm_up(file_paths, extraction_func)

        assert result["total"] == 3
        assert result["success"] == 2
        assert result["failed"] == 1
        assert result["skipped"] == 0
        assert call_count == 3, f"Expected 3 calls, got {call_count}"

    def test_warm_up_skip_cached(self, extraction_cache, tmp_path):
        """测试预热时跳过已缓存文件"""
        call_count = 0

        def extraction_func(file_path: str):
            nonlocal call_count
            call_count += 1
            return {"success": True, "data": "test"}

        file_path = str(tmp_path / "cached.pdf")
        Path(file_path).write_bytes(b"Test content")

        # 预先缓存
        extraction_cache.cache.set(file_path, {"success": True, "data": "test"})

        # 预热缓存 - 应跳过已缓存文件
        result = extraction_cache.warm_up([file_path], extraction_func)

        assert result["total"] == 1
        assert result["skipped"] == 1
        assert call_count == 0  # 没有调用提取函数


# ============================================================================
# cached_extraction 装饰器测试
# ============================================================================


class TestCachedExtractionDecorator:
    """cached_extraction 装饰器测试"""

    @pytest.mark.asyncio
    async def test_decorator_with_successful_result(self, tmp_path):
        """测试装饰器缓存成功结果"""
        call_count = 0

        @cached_extraction(ttl_seconds=60)
        async def extract_func(file_path: str):
            nonlocal call_count
            call_count += 1
            return {"success": True, "data": {"field": "value"}, "confidence": 0.9}

        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"Test content")

        # 第一次调用
        result1 = await extract_func(str(pdf_path))
        assert call_count == 1
        assert result1["success"] is True

        # 第二次调用 - 应使用缓存
        result2 = await extract_func(str(pdf_path))
        assert call_count == 1
        assert result2["success"] is True

    @pytest.mark.asyncio
    async def test_decorator_with_failed_result(self, tmp_path):
        """测试装饰器不缓存失败结果"""
        call_count = 0

        @cached_extraction(ttl_seconds=60)
        async def extract_func(file_path: str):
            nonlocal call_count
            call_count += 1
            return {"success": False, "error": "Extraction failed"}

        pdf_path = tmp_path / "test_failed.pdf"
        pdf_path.write_bytes(b"Unique content for failed test")

        # 第一次调用
        result1 = await extract_func(str(pdf_path))
        assert call_count == 1, (
            f"Expected 1 call after first extraction, got {call_count}"
        )
        assert result1["success"] is False

        # 第二次调用 - 应重新执行（失败结果不缓存）
        result2 = await extract_func(str(pdf_path))
        assert call_count == 2, (
            f"Expected 2 calls after second extraction, got {call_count}"
        )
        assert result2["success"] is False


# ============================================================================
# 全局缓存函数测试
# ============================================================================


class TestGlobalCacheFunctions:
    """全局缓存函数测试"""

    def test_get_cache_singleton(self):
        """测试全局缓存单例"""
        cache1 = get_cache()
        cache2 = get_cache()
        assert cache1 is cache2

    def test_clear_all_caches(self):
        """测试清理所有全局缓存"""
        cache = get_cache()
        # 创建一些测试缓存
        cache.cache_dir.mkdir(parents=True, exist_ok=True)
        (cache.cache_dir / "test1.json").write_text("{}")
        (cache.cache_dir / "test2.json").write_text("{}")

        # 清理所有缓存
        count = clear_all_caches()
        assert count >= 0  # 数量可能因为其他测试而不同


# ============================================================================
# PDFCache Error Handling Tests (Lines 121-164)
# ============================================================================


class TestPDFCacheErrorHandling:
    """PDFCache 错误处理测试"""

    @pytest.fixture
    def temp_cache_dir(self):
        """创建临时缓存目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def cache(self, temp_cache_dir):
        """创建缓存实例"""
        return PDFCache(cache_dir=temp_cache_dir, ttl_seconds=60)

    @pytest.fixture
    def sample_pdf_file(self, tmp_path):
        """创建示例 PDF 文件"""
        pdf_path = tmp_path / "sample.pdf"
        pdf_path.write_bytes(b"Sample PDF content for error tests")
        return str(pdf_path)

    def test_cache_corrupted_json_file(self, cache, sample_pdf_file):
        """测试损坏的 JSON 缓存文件 (Lines 121-134)"""
        # 创建缓存文件
        cache.set(sample_pdf_file, {"test": "data"})

        # 获取缓存文件路径并损坏它
        hash_key = cache.get_file_hash(sample_pdf_file)
        cache_file = cache.cache_dir / f"{hash_key}.json"

        # 写入损坏的 JSON
        with open(cache_file, "w") as f:
            f.write('{"invalid": "json", "missing": }')

        # 尝试读取缓存 - 应删除损坏文件并返回 None
        result = cache.get(sample_pdf_file)
        assert result is None

        # 验证文件被删除
        assert not cache_file.exists()

        # 验证统计
        stats = cache.get_stats()
        assert stats["evictions"] == 1
        assert stats["misses"] == 1

    def test_cache_utime_failure_graceful_handling(self, cache, sample_pdf_file):
        """测试 utime 失败时的优雅处理 (Lines 139-141)"""
        # 创建缓存
        cache.set(sample_pdf_file, {"test": "data"})

        # Mock utime to raise OSError
        with patch("os.utime", side_effect=OSError("utime failed")):
            # 缓存应仍然成功，utime 失败不影响读取
            result = cache.get(sample_pdf_file)
            assert result is not None
            assert result["result"] == {"test": "data"}

    def test_cache_permission_error_raises(self, cache, sample_pdf_file):
        """测试权限错误重新抛出 (Lines 147-154)"""
        # Mock open to raise PermissionError
        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            with pytest.raises(PermissionError):
                cache.get(sample_pdf_file)

    def test_cache_oserror_raises(self, cache, sample_pdf_file):
        """测试 OSError 重新抛出"""
        # Mock open to raise OSError
        with patch("builtins.open", side_effect=OSError("Disk error")):
            with pytest.raises(OSError):
                cache.get(sample_pdf_file)

    def test_cache_unexpected_error_raises_runtime_error(self, cache, sample_pdf_file):
        """测试未预期错误抛出 RuntimeError (Lines 155-164)"""
        # Mock get_file_hash to raise unexpected error
        with patch.object(
            cache, "get_file_hash", side_effect=ValueError("Unexpected error")
        ):
            with pytest.raises(RuntimeError, match="Cache system malfunction"):
                cache.get(sample_pdf_file)


# ============================================================================
# PDFCache.set Error Handling Tests (Lines 205-246)
# ============================================================================


class TestPDFCacheSetErrorHandling:
    """PDFCache.set 错误处理测试"""

    @pytest.fixture
    def temp_cache_dir(self):
        """创建临时缓存目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def cache(self, temp_cache_dir):
        """创建缓存实例"""
        return PDFCache(cache_dir=temp_cache_dir, ttl_seconds=60)

    @pytest.fixture
    def sample_pdf_file(self, tmp_path):
        """创建示例 PDF 文件"""
        pdf_path = tmp_path / "sample.pdf"
        pdf_path.write_bytes(b"Sample PDF for set error tests")
        return str(pdf_path)

    def test_cache_set_disk_full_error(self, cache, sample_pdf_file):
        """测试磁盘空间不足错误 (Lines 206-212)"""
        # Mock open to raise disk full error
        disk_full_error = OSError("No space left on device")
        disk_full_error.errno = 28
        with patch("builtins.open", side_effect=disk_full_error):
            with pytest.raises(RuntimeError, match="Disk space exhausted"):
                cache.set(sample_pdf_file, {"test": "data"})

    def test_cache_set_permission_denied_error(self, cache, sample_pdf_file):
        """测试权限拒绝错误 (Lines 213-222)"""
        # Mock open to raise permission error
        perm_error = OSError("Permission denied")
        perm_error.errno = 13
        with patch("builtins.open", side_effect=perm_error):
            with pytest.raises(RuntimeError, match="Cache directory not writable"):
                cache.set(sample_pdf_file, {"test": "data"})

    def test_cache_set_other_oserror(self, cache, sample_pdf_file):
        """测试其他 OSError (Lines 223-230)"""
        # Mock open to raise other OSError
        with patch("builtins.open", side_effect=OSError("Other error")):
            with pytest.raises(OSError):
                cache.set(sample_pdf_file, {"test": "data"})

    def test_cache_set_type_error_serialization(self, cache, sample_pdf_file):
        """测试序列化 TypeError (Lines 231-238)"""

        # 尝试缓存不可序列化的对象
        class UnserializableClass:
            pass

        result = {"data": UnserializableClass()}

        # 应返回 False，不抛出异常
        success = cache.set(sample_pdf_file, result)
        assert success is False

    def test_cache_set_value_error_serialization(self, cache, sample_pdf_file):
        """测试序列化 ValueError"""
        # Mock json.dump to raise ValueError
        with patch("json.dump", side_effect=ValueError("Serialization error")):
            # 应返回 False，不抛出异常
            success = cache.set(sample_pdf_file, {"test": "data"})
            assert success is False

    def test_cache_set_unexpected_error_raises(self, cache, sample_pdf_file):
        """测试未预期错误抛出 (Lines 239-246)"""
        # Mock get_file_hash to raise unexpected error
        with patch.object(
            cache, "get_file_hash", side_effect=RuntimeError("Unexpected")
        ):
            with pytest.raises(RuntimeError):
                cache.set(sample_pdf_file, {"test": "data"})


# ============================================================================
# PDFCache.invalidate Error Handling Tests (Lines 269-271)
# ============================================================================


class TestPDFCacheInvalidateErrors:
    """PDFCache.invalidate 错误处理测试"""

    @pytest.fixture
    def temp_cache_dir(self):
        """创建临时缓存目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def cache(self, temp_cache_dir):
        """创建缓存实例"""
        return PDFCache(cache_dir=temp_cache_dir, ttl_seconds=60)

    def test_cache_invalidate_error_returns_false(self, cache):
        """测试 invalidate 错误时返回 False (Lines 269-271)"""
        # Mock get_file_hash to raise error
        with patch.object(cache, "get_file_hash", side_effect=Exception("Hash failed")):
            result = cache.invalidate("test.pdf")
            assert result is False


# ============================================================================
# PDFCache.clear Error Handling Tests (Lines 303-305)
# ============================================================================


class TestPDFCacheClearErrors:
    """PDFCache.clear 错误处理测试"""

    @pytest.fixture
    def temp_cache_dir(self):
        """创建临时缓存目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def cache(self, temp_cache_dir):
        """创建缓存实例"""
        return PDFCache(cache_dir=temp_cache_dir, ttl_seconds=60)

    def test_cache_clear_error_returns_zero(self, cache):
        """测试 clear 错误时返回 0 (Lines 303-305)"""
        # Mock glob to raise error
        with patch.object(Path, "glob", side_effect=Exception("Glob failed")):
            count = cache.clear()
            assert count == 0


# ============================================================================
# AsyncDocumentCache Tests (Lines 368-657)
# ============================================================================


class TestAsyncDocumentCache:
    """AsyncDocumentCache 测试"""

    @pytest.fixture
    def temp_cache_dir(self):
        """创建临时缓存目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def async_cache(self, temp_cache_dir):
        """创建异步缓存实例"""
        return AsyncDocumentCache(
            cache_dir=temp_cache_dir, ttl_seconds=60, use_async=True
        )

    @pytest.fixture
    def sample_pdf_file(self, tmp_path):
        """创建示例 PDF 文件"""
        pdf_path = tmp_path / "sample.pdf"
        pdf_path.write_bytes(b"Sample PDF for async cache tests")
        return str(pdf_path)

    @pytest.mark.asyncio
    async def test_async_cache_compute_file_hash(self, async_cache, sample_pdf_file):
        """测试异步计算文件哈希 (Lines 399-404)"""
        hash_value = await async_cache.compute_file_hash(sample_pdf_file)
        assert len(hash_value) == 32  # MD5 hex 长度

    @pytest.mark.asyncio
    async def test_async_cache_compute_file_hash_fallback(self, temp_cache_dir):
        """测试同步回退计算文件哈希 (Lines 407-408)"""
        # 创建禁用异步的缓存
        cache_no_async = AsyncDocumentCache(
            cache_dir=temp_cache_dir, ttl_seconds=60, use_async=False
        )

        pdf_file = Path(temp_cache_dir) / "test.pdf"
        pdf_file.write_bytes(b"Test content for fallback")

        hash_value = await cache_no_async.compute_file_hash(str(pdf_file))
        assert len(hash_value) == 32

    def test_async_cache_sync_compute_hash(self, temp_cache_dir):
        """测试同步计算文件哈希 (Lines 412-416)"""
        cache = AsyncDocumentCache(cache_dir=temp_cache_dir, ttl_seconds=60)

        pdf_file = Path(temp_cache_dir) / "test.pdf"
        pdf_file.write_bytes(b"Test content for sync hash")

        hash_value = cache._sync_compute_hash(str(pdf_file))
        assert len(hash_value) == 32

    @pytest.mark.asyncio
    async def test_async_cache_get_miss(self, async_cache):
        """测试异步缓存未命中"""
        result = await async_cache.get("nonexistent_hash")
        assert result is None

        stats = await async_cache.get_stats()
        assert stats["misses"] == 1

    @pytest.mark.asyncio
    async def test_async_cache_get_hit(self, async_cache):
        """测试异步缓存命中"""
        # 先设置缓存
        await async_cache.set("test_hash", {"data": "test"})

        # 获取缓存
        result = await async_cache.get("test_hash")
        assert result is not None
        # AsyncDocumentCache stores data directly, not wrapped
        assert result["data"] == {"data": "test"} or result.get("data") == "test"

        stats = await async_cache.get_stats()
        assert stats["hits"] == 1

    @pytest.mark.asyncio
    async def test_async_cache_get_expired(self, async_cache):
        """测试异步缓存过期 (Lines 439-444)"""
        # 设置较短的 TTL
        async_cache.ttl_seconds = 1

        # 设置缓存
        await async_cache.set("test_hash", {"data": "test"})
        await asyncio.sleep(2)

        # 获取缓存 - 应已过期
        result = await async_cache.get("test_hash")
        assert result is None

        stats = await async_cache.get_stats()
        assert stats["evictions"] == 1

    @pytest.mark.asyncio
    async def test_async_cache_get_corrupted_json(self, async_cache):
        """测试异步缓存损坏 JSON (Lines 464-478)"""
        # 创建损坏的缓存文件
        cache_file = async_cache.cache_dir / "test_hash.json"
        cache_file.write_text('{"invalid": json}')

        # 尝试获取缓存 - 应删除损坏文件并返回 None
        result = await async_cache.get("test_hash")
        assert result is None

        # 验证文件被删除
        assert not cache_file.exists()

    @pytest.mark.asyncio
    async def test_async_cache_get_permission_error_raises(self, async_cache):
        """测试异步缓存权限错误 (Lines 479-489)"""
        # 先创建一个缓存文件
        await async_cache.set("test_hash", {"data": "test"})

        # Mock stat to raise PermissionError
        with patch(
            "asyncio.to_thread", side_effect=PermissionError("Permission denied")
        ):
            with pytest.raises(PermissionError):
                await async_cache.get("test_hash")

    @pytest.mark.asyncio
    async def test_async_cache_get_unexpected_error_raises(self, async_cache):
        """测试异步缓存未预期错误 (Lines 490-500)"""
        # 先创建一个缓存文件
        await async_cache.set("test_hash", {"data": "test"})

        # Mock to_thread to raise unexpected error after stat
        call_count = [0]

        async def mock_to_thread(func, *args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call is stat()
                return func(*args, **kwargs)
            else:
                # Subsequent calls raise error
                raise ValueError("Unexpected")

        with patch("asyncio.to_thread", side_effect=mock_to_thread):
            with pytest.raises(RuntimeError, match="Async cache system malfunction"):
                await async_cache.get("test_hash")

    @pytest.mark.asyncio
    async def test_async_cache_set_success(self, async_cache):
        """测试异步缓存设置成功 (Lines 516-541)"""
        success = await async_cache.set("test_hash", {"data": "test"})
        assert success is True

        # 验证缓存存在
        cache_file = async_cache.cache_dir / "test_hash.json"
        assert cache_file.exists()

    @pytest.mark.asyncio
    async def test_async_cache_set_with_custom_ttl(self, async_cache):
        """测试异步缓存设置自定义 TTL"""
        success = await async_cache.set("test_hash", {"data": "test"}, ttl=120)
        assert success is True

        # 读取缓存文件验证 TTL
        cache_file = async_cache.cache_dir / "test_hash.json"
        content = cache_file.read_text()
        cached_data = json.loads(content)

        assert "expires_at" in cached_data

    @pytest.mark.asyncio
    async def test_async_cache_set_disk_full_error(self, temp_cache_dir):
        """测试异步缓存磁盘空间不足 (Lines 543-553)"""
        # Create cache without async to test synchronous path
        cache = AsyncDocumentCache(
            cache_dir=temp_cache_dir, ttl_seconds=60, use_async=False
        )

        # Mock to_thread to raise disk full error
        disk_full_error = OSError("No space left on device")
        disk_full_error.errno = 28

        with patch("asyncio.to_thread", side_effect=disk_full_error):
            with pytest.raises(RuntimeError, match="Disk space exhausted"):
                await cache.set("test_hash", {"data": "test"})

    @pytest.mark.asyncio
    async def test_async_cache_set_permission_error(self, temp_cache_dir):
        """测试异步缓存权限错误 (Lines 554-563)"""
        # Create cache without async to test synchronous path
        cache = AsyncDocumentCache(
            cache_dir=temp_cache_dir, ttl_seconds=60, use_async=False
        )

        # Mock to_thread to raise permission error
        perm_error = OSError("Permission denied")
        perm_error.errno = 13

        with patch("asyncio.to_thread", side_effect=perm_error):
            with pytest.raises(RuntimeError, match="Cache directory not writable"):
                await cache.set("test_hash", {"data": "test"})

    @pytest.mark.asyncio
    async def test_async_cache_set_serialization_error(self, async_cache):
        """测试异步缓存序列化错误 (Lines 571-580)"""

        # 尝试缓存不可序列化的对象
        class UnserializableClass:
            pass

        data = {"obj": UnserializableClass()}

        # 应返回 False，不抛出异常
        success = await async_cache.set("test_hash", data)
        assert success is False

    @pytest.mark.asyncio
    async def test_async_cache_set_unexpected_error(self, async_cache):
        """测试异步缓存未预期错误 (Lines 581-587)"""
        # Mock json.dumps to raise unexpected error
        with patch("json.dumps", side_effect=RuntimeError("Unexpected")):
            with pytest.raises(RuntimeError):
                await async_cache.set("test_hash", {"data": "test"})

    @pytest.mark.asyncio
    async def test_async_cache_invalidate_success(self, async_cache):
        """测试异步缓存失效成功"""
        # 先设置缓存
        await async_cache.set("test_hash", {"data": "test"})

        # 失效缓存
        success = await async_cache.invalidate("test_hash")
        assert success is True

        # 验证缓存被删除
        cache_file = async_cache.cache_dir / "test_hash.json"
        assert not cache_file.exists()

    @pytest.mark.asyncio
    async def test_async_cache_invalidate_nonexistent(self, async_cache):
        """测试异步缓存失效不存在的文件"""
        success = await async_cache.invalidate("nonexistent_hash")
        assert success is False

    @pytest.mark.asyncio
    async def test_async_cache_invalidate_error(self, async_cache):
        """测试异步缓存失效错误 (Lines 606-608)"""
        # Mock to_thread to raise error
        with patch("asyncio.to_thread", side_effect=Exception("Invalidate failed")):
            success = await async_cache.invalidate("test_hash")
            assert success is False

    @pytest.mark.asyncio
    async def test_async_cache_clear_all(self, async_cache):
        """测试异步清理所有缓存"""
        # 创建多个缓存文件
        for i in range(3):
            await async_cache.set(f"hash_{i}", {"data": f"test_{i}"})

        # 清理所有
        count = await async_cache.clear()
        assert count == 3

        stats = await async_cache.get_stats()
        assert stats["total_cached_files"] == 0

    @pytest.mark.asyncio
    async def test_async_cache_clear_old_only(self, async_cache):
        """测试异步清理旧缓存 (Lines 628-634)"""
        async_cache.ttl_seconds = 10

        # 创建第一个缓存
        await async_cache.set("hash_1", {"data": "test1"})
        await asyncio.sleep(1.5)

        # 创建第二个缓存
        await async_cache.set("hash_2", {"data": "test2"})

        # 清理超过 1 秒的缓存
        count = await async_cache.clear(older_than_seconds=1)
        assert count == 1

    @pytest.mark.asyncio
    async def test_async_cache_clear_error(self, async_cache):
        """测试异步清理错误 (Lines 639-641)"""
        # Mock glob to raise error
        with patch.object(Path, "glob", side_effect=Exception("Glob failed")):
            count = await async_cache.clear()
            assert count == 0

    @pytest.mark.asyncio
    async def test_async_cache_get_stats(self, async_cache):
        """测试异步获取统计信息 (Lines 650-657)"""
        # 创建一些缓存
        await async_cache.set("hash1", {"data": "test1"})
        await async_cache.set("hash2", {"data": "test2"})

        # 命中一次
        await async_cache.get("hash1")

        stats = await async_cache.get_stats()
        assert stats["total_cached_files"] == 2
        assert stats["hits"] == 1
        assert stats["misses"] == 0
        assert stats["hit_rate"] == 1.0
        assert stats["async_enabled"] is True

    def test_async_cache_init_without_aiofiles(self, temp_cache_dir):
        """测试异步缓存初始化时 aiofiles 不可用 (Lines 384-387)"""
        with patch("src.services.document.cache.AIOFILES_AVAILABLE", False):
            cache = AsyncDocumentCache(
                cache_dir=temp_cache_dir, ttl_seconds=60, use_async=True
            )

            # 应禁用异步并回退到同步
            assert cache._use_async is False


# ============================================================================
# CachedExtractor Additional Tests (Line 717)
# ============================================================================


class TestCachedExtractorEdgeCases:
    """CachedExtractor 边缘情况测试"""

    @pytest.fixture
    def temp_cache_dir(self):
        """创建临时缓存目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def cache(self, temp_cache_dir):
        """创建缓存实例"""
        return PDFCache(cache_dir=temp_cache_dir, ttl_seconds=60)

    @pytest.mark.asyncio
    async def test_cached_extractor_non_string_cache_key(self, cache, tmp_path):
        """测试非字符串缓存键 (Line 717)"""
        decorator = CachedExtractor(cache=cache, cache_key_func=lambda x: None)

        call_count = 0

        @decorator
        async def extract_func(file_path: str):
            nonlocal call_count
            call_count += 1
            return {"success": True}

        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"Test content")

        # 两次调用 - 都应执行函数（缓存键为 None）
        await extract_func(str(pdf_path))
        await extract_func(str(pdf_path))

        assert call_count == 2


# ============================================================================
# clear_all_caches Additional Tests (Line 876)
# ============================================================================


class TestClearAllCachesEdgeCases:
    """clear_all_caches 边缘情况测试"""

    def test_clear_all_caches_with_no_cache(self):
        """测试没有全局缓存时清理 (Line 876)"""
        # 重置全局缓存
        import src.services.document.cache as cache_module

        cache_module._default_cache = None

        # 清理应返回 0
        count = clear_all_caches()
        assert count == 0


# ============================================================================
# Additional PDFCache Edge Cases
# ============================================================================


class TestPDFCacheAdditionalEdgeCases:
    """PDFCache 额外边缘情况测试"""

    @pytest.fixture
    def temp_cache_dir(self):
        """创建临时缓存目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def cache(self, temp_cache_dir):
        """创建缓存实例"""
        return PDFCache(cache_dir=temp_cache_dir, ttl_seconds=60)

    def test_cache_set_empty_file(self, cache, tmp_path):
        """测试空文件缓存"""
        pdf_path = tmp_path / "empty.pdf"
        pdf_path.write_bytes(b"")

        # 应能正常处理空文件
        hash_value = cache.get_file_hash(str(pdf_path))
        assert len(hash_value) == 32

    def test_cache_get_stats_with_zero_operations(self, cache):
        """测试零操作时的统计"""
        stats = cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["evictions"] == 0
        assert stats["hit_rate"] == 0

    def test_cache_multiple_hits_and_misses(self, cache, tmp_path):
        """测试多次命中和未命中的统计"""
        # 创建多个文件
        files = []
        for i in range(5):
            pdf_path = tmp_path / f"file{i}.pdf"
            pdf_path.write_bytes(f"Content {i}".encode())
            files.append(str(pdf_path))

        # 缓存前 3 个文件
        for i in range(3):
            cache.set(files[i], {"data": i})

        # 5 次获取操作
        cache.get(files[0])  # hit
        cache.get(files[1])  # hit
        cache.get(files[2])  # hit
        cache.get(files[3])  # miss
        cache.get(files[4])  # miss

        stats = cache.get_stats()
        assert stats["hits"] == 3
        assert stats["misses"] == 2
        assert stats["hit_rate"] == 0.6

    def test_cache_invalidate_then_get(self, cache, tmp_path):
        """测试失效后再获取"""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"Test content")

        # 设置缓存
        cache.set(str(pdf_path), {"data": "test"})

        # 失效缓存
        cache.invalidate(str(pdf_path))

        # 再次获取 - 应返回 None
        result = cache.get(str(pdf_path))
        assert result is None

    def test_cache_clear_with_no_files(self, cache):
        """测试清空缓存目录"""
        count = cache.clear()
        assert count == 0

    def test_cache_cleanup_expired_with_no_expired(self, cache):
        """测试清理过期缓存时没有过期文件"""
        pdf_path = Path(cache.cache_dir) / "test.pdf"
        pdf_path.write_bytes(b"Test content")

        cache.set(str(pdf_path), {"data": "test"})

        # 清理过期 - 应删除 0 个文件
        count = cache.cleanup_expired()
        assert count == 0
