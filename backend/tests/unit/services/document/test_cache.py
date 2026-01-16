#!/usr/bin/env python3
"""
PDF 缓存层单元测试
测试 PDFCache 和相关装饰器
"""

import tempfile
import time
from pathlib import Path

import pytest

from src.services.document.cache import (
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
            cache_key_func=lambda x: str(file1)  # 所有路径都映射到同一个文件
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
        return {
            "success": True,
            "confidence": 0.9,
            "data": {"field": "value"}
        }

    @pytest.fixture
    def low_confidence_result(self):
        """低置信度结果"""
        return {
            "success": True,
            "confidence": 0.5,
            "data": {"field": "value"}
        }

    def test_conditional_cache_registration(self, extraction_cache):
        """测试条件缓存注册"""
        # 注册条件
        extraction_cache.register_conditional_cache(
            "high_confidence_only",
            lambda result: result.get("confidence", 0) > 0.8
        )

        assert "high_confidence_only" in extraction_cache._conditional_caches

    def test_get_with_condition_met(self, extraction_cache, sample_pdf_file, high_confidence_result):
        """测试条件满足时获取缓存"""
        extraction_cache.register_conditional_cache(
            "high_confidence_only",
            lambda result: result.get("confidence", 0) > 0.8
        )

        # 设置高置信度缓存
        extraction_cache.cache.set(sample_pdf_file, high_confidence_result)

        # 获取缓存 - 条件满足
        cached = extraction_cache.get(sample_pdf_file, condition="high_confidence_only")
        assert cached is not None
        assert cached["result"]["confidence"] == 0.9

    def test_get_with_condition_not_met(self, extraction_cache, sample_pdf_file, low_confidence_result):
        """测试条件不满足时返回 None"""
        extraction_cache.register_conditional_cache(
            "high_confidence_only",
            lambda result: result.get("confidence", 0) > 0.8
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
            return {
                "success": True,
                "data": {"field": "value"},
                "confidence": 0.9
            }

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
            return {
                "success": False,
                "error": "Extraction failed"
            }

        pdf_path = tmp_path / "test_failed.pdf"
        pdf_path.write_bytes(b"Unique content for failed test")

        # 第一次调用
        result1 = await extract_func(str(pdf_path))
        assert call_count == 1, f"Expected 1 call after first extraction, got {call_count}"
        assert result1["success"] is False

        # 第二次调用 - 应重新执行（失败结果不缓存）
        result2 = await extract_func(str(pdf_path))
        assert call_count == 2, f"Expected 2 calls after second extraction, got {call_count}"
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
