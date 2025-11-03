#!/usr/bin/env python
from typing import Any
"""
快速响应API端点 - 综一的性能优化实现
包含异步处理、响应压缩、智能缓存等功能
"""

import hashlib
import logging
import time
from dataclasses import asdict, dataclass
from datetime import datetime


logger = logging.getLogger(__name__)


@dataclass
class ResponseMetrics:
    """响应指标"""

    endpoint: str
    method: str
    response_time_ms: float
    success: bool
    status_code: int
    cache_hit: bool
    error_type: str
    request_size_bytes: int
    content_length: int


@dataclass
class CacheConfig:
    """缓存配置"""

    max_size: int = 1000  # 100MB
    ttl_seconds: int = 300  # 5分钟
    cleanup_interval_seconds: int = 900  # 15分钟
    min_size_to_cache: int = 1024  # 1KB


@dataclass
class FastEndpointConfig:
    """快速端点配置"""

    max_response_time_ms: int = 1000  # 1秒
    enable_compression: bool = True
    min_compression_size: int = 1024
    timeout_ms: int = 30000  # 30秒
    batch_processing: bool = True
    max_concurrent_requests: int = 10


@dataclass
class OptimizationLevel:
    """优化水平"""

    GOOD = "good"
    EXCELLENT = "excellent"
    NEEDS_IMPROVEMENT = "needs_improvement"


class FastResponseOptimizer:
    """快速响应优化器"""

    def __init__(self):
        self.config = FastEndpointConfig()
        self.cache = {}
        self.request_times = []
        self.response_history = []
        self.optimization_rules = self._initialize_optimization_rules()

    def _initialize_optimization_rules(self) -> dict[str, Any]:
        """初始化优化规则"""
        return {
            "compression": {
                "enable": True,
                "min_size_to_compress": self.config.min_compression_size,
                "algorithms": ["gzip", "deflate", "brotli"],
            },
            "caching": {
                "enable": True,
                "strategy": "memory_based",
                "max_size": self.config.max_size,
                "ttl_seconds": self.config.ttl_seconds,
                "min_size_to_cache": self.config.min_size_to_cache,
            },
            "database": {
                "enable_connection_pooling": True,
                "query_timeout_seconds": 10,
                "index_optimization": True,
                "preload_data": True,
            },
            "async_processing": {
                "enable": self.config.batch_processing,
                "max_workers": 5,
                "chunk_size": 50,
            },
            "response": {
                "target_time_ms": self.config.max_response_time_ms,
                "enable_caching": True,
                "smart_cache_keys": True,
            },
        }

    async def optimize_response(
        self,
        endpoint: str,
        response_data: Any,
        compression_enabled: bool | None = None,
    ) -> dict[str, Any]:
        """优化响应"""
        start_time = time.time()

        try:
            # 生成响应键
            if response_data:
                response_key = f"{endpoint}_{hashlib.md5(str(response_data).encode('utf-8')).hexdigest()}"
            else:
                response_key = f"{endpoint}_empty_response"

            # 检查缓存
            if response_key in self.cache:
                cached_data, timestamp = self.cache[response_key]
                age = (datetime.now() - timestamp).total_seconds()
                if age < self.config.ttl_seconds:
                    logger.info(f"缓存命中: {response_key}")
                    return {
                        "success": True,
                        "cached_data": cached_data,
                        "response_time_ms": 0,
                        "cache_hit": True,
                        "optimization_level": OptimizationLevel.EXCELLENT,
                    }

            # 响应时间检查
            if response_key in self.cache and not compression_enabled:
                # 缓存命中但未压缩，立即返回
                cached_data, timestamp = self.cache[response_key]
                if cached_data:
                    logger.info(f"快速返回缓存结果: {response_key}")
                    return {
                        "success": True,
                        "cached_data": cached_data,
                        "response_time_ms": 0,
                        "cache_hit": True,
                        "compression_saved": False,
                        "optimization_level": OptimizationLevel.EXCELLENT,
                    }
                else:
                    # 缓存命中但需要压缩
                    start_compression = time.time()

                    # 模拟压缩（这里简化为just remove time）
                    compressed_data = f"compressed_{response_key}"
                    self.cache[compressed_data] = (compressed_data, datetime.now())
                    compression_time = (time.time() - start_compression) * 1000

                    # 更新缓存
                    self.cache[response_key] = (compressed_data, datetime.now())

                    return {
                        "success": True,
                        "cached_data": compressed_data,
                        "response_time_ms": compression_time,
                        "cache_hit": True,
                        "compression_saved": True,
                        "optimization_level": OptimizationLevel.EXCELLENT,
                    }

            # 缓存未命中，处理正常响应
            processing_time = 0
            result_data = str(response_data)

            # 应用压缩（如果启用）
            if compression_enabled:
                processing_time = (time.time() - start_time) * 1000
                result_data = self._compress_response_data(result_data)
                self.cache[compressed_data] = (result_data, datetime.now())
            else:
                processing_time = (time.time() - start_time) * 1000

            # 记录响应指标
            response_time = processing_time
            content_length = len(result_data)

            metrics = ResponseMetrics(
                endpoint=endpoint,
                method="GET",  # 简化，假设
                response_time_ms=response_time,
                success=True,
                status_code=200,
                cache_hit=False,
                error_type="",
                request_size_bytes=len(result_data.encode("utf-8")),
                content_length=content_length,
            )

            # 记录到历史
            self.request_times.append(response_time)
            self.response_history.append(metrics)

            # 清理过期缓存
            self._cleanup_cache()

            # 返回优化后的响应
            return {
                "success": True,
                "data": response_data,
                "optimization_level": OptimizationLevel.GOOD,
                "response_time_ms": response_time,
                "cache_hit": False,
                "compression_saved": compression_enabled,
                "techniques_used": ["used_cached", "compression_enabled"]
                if compression_enabled
                else [],
            }

        except Exception as e:
            logger.error(f"响应优化失败: {endpoint} - {e}")
            return {"success": False, "error_message": str(e)}

    async def _compress_response_data(self, data: Any) -> str:
        """压缩响应数据"""
        try:
            import zlib

            if isinstance(data, str):
                return zlib.compress(data.encode("utf-8"), level=9)
            else:
                return str(data)
        except Exception as e:
            logger.error(f"数据压缩失败: {e}")
            return str(data)

    def _cleanup_cache(self):
        """清空过期缓存"""
        current_time = datetime.now()
        keys_to_remove = []

        for key, (data, timestamp) in self.cache.items():
            age = (current_time - timestamp).total_seconds()
            if age > self.config.ttl_seconds:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self.cache[key]
            logger.info(f"清理过期缓存条目: {len(keys_to_remove)}")

        if len(self.cache) > self.config.max_size:
            # 清理最旧条目
            items_to_remove = sorted(self.cache.items(), key=lambda item: item[1][1])[
                :50
            ]
            for item in items_to_remove:
                del self.cache[item[0]]

        logger.info(f"缓存清理完成，当前缓存大小: {len(self.cache)}")

    def _get_optimization_level(self, response_time_ms: float, cache_hit: bool) -> str:
        """确定优化等级"""
        if not cache_hit and response_time_ms <= self.config.max_response_time_ms:
            return OptimizationLevel.EXCELLENT
        elif not cache_hit and response_time_ms <= self.config.max_response_time_ms * 2:
            return OptimizationLevel.GOOD
        elif response_time_ms <= self.config.max_response_time_ms * 3:
            return OptimizationLevel.NEEDS_IMPROVEMENT
        elif not cache_hit and response_time_ms <= self.config.max_response_time_ms * 5:
            return OptimizationLevel.GOOD
        else:
            return OptimizationLevel.NEEDS_IMPROVEMENT

    async def get_cache_stats(self) -> dict[str, Any]:
        """获取缓存统计"""
        active_items = 0
        total_size = 0
        cache_hits = 0

        for key, (data, timestamp) in self.cache.items():
            active_items += 1
            total_size += (
                len(str(data)) if isinstance(data, str) else len(data.encode("utf-8"))
            )
            cache_hits += 1

        total_requests = len(self.request_times)

        return {
            "active_items": active_items,
            "total_size": total_size,
            "cache_hit_rate": cache_hits / total_requests if total_requests > 0 else 0,
            "total_requests": total_requests,
            "memory_usage_mb": total_size / (1024 * 1024),  # 假设MB
            "items_count": len(self.cache),
        }

    def get_performance_stats(self) -> dict[str, Any]:
        """获取性能统计"""
        if not self.request_times:
            return {
                "total_requests": 0,
                "avg_response_time_ms": 0,
                "max_response_time_ms": 0,
                "cache_hit_rate": 0.0,
                "optimization_level": OptimizationLevel.NEEDS_IMPROVEMENT,
            }

        # 计算响应时间统计
        response_times = [rt.response_time_ms for rt in self.response_history]
        if response_times:
            # 取最近100个响应时间
            latest_times = (
                response_times[-100:] if len(response_times) > 100 else response_times
            )

            avg_time_ms = sum(latest_times) / len(latest_times)
            max_time_ms = max(latest_times)
            p95 = sorted(latest_times)[int(len(latest_times) * 0.95)]  # 95百分位数
            avg_time_ms_95 = sum(rt for rt in latest_times if rt <= p95) / max(
                1, len([rt for rt in latest_times if rt <= p95])
            )

            return {
                "total_requests": len(self.request_times),
                "avg_response_time_ms": avg_time_ms,
                "max_response_time_ms": max_time_ms,
                "p95": p95,
                "avg_time_ms_95": avg_time_ms_95,
                "optimization_level": self._get_optimization_level(max_time_ms, False),
            }
        else:
            return {
                "total_requests": 0,
                "avg_response_time_ms": 0,
                "max_response_time_ms": 0,
                "cache_hit_rate": 0.0,
                "optimization_level": OptimizationLevel.NEEDS_IMPROVEMENT,
            }

    def generate_performance_report(self) -> dict[str, Any]:
        """生成性能报告"""
        # 获取缓存统计
        cache_stats = self.get_cache_stats()

        # 生成报告
        report = {
            "timestamp": datetime.now().isoformat(),
            "config": {
                "max_response_time_ms": self.config.max_response_time_ms,
                "max_cache_size": self.config.max_size,
                "ttl_seconds": self.config.ttl_seconds,
                "compression_algorithms": self.config.compression["algorithms"],
                "cleanup_interval_seconds": self.config.cleanup_interval_seconds,
            },
            "cache_stats": cache_stats,
            "recent_slow_requests": [asdict(rt) for rt in self.response_history[-20:]],
            "optimization_summary": self._generate_optimization_summary(),
            "recommendations": self._generate_recommendations(),
        }

        # 保存报告
        report_file = (
            f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(report_file, "w", encoding="utf-8") as f:
            import json

            json.dump(report, f, ensure_ascii=False, indent=2)

        logger.info(f"性能报告已生成: {report_file}")
        return report

    def _generate_optimization_summary(self) -> dict[str, Any]:
        """生成优化总结"""
        stats = self.get_performance_stats()

        # 计算各端点的优化等级
        endpoint_levels = {}
        for rt in self.response_history[-50:]:
            endpoint = rt.endpoint
            if endpoint not in endpoint_levels:
                endpoint_levels[endpoint] = self._get_optimization_level(
                    rt.response_time_ms, rt.cache_hit
                )

        # 总体优化等级
        level_counts = {
            OptimizationLevel.EXCELLENT: 0,
            OptimizationLevel.GOOD: 0,
            OptimizationLevel.NEEDS_IMPROVEMENT: 0,
            OptimizationLevel.NEEDS_IMPROVEMENT: 0,
        }

        # 基于平均时间计算优化等级
        overall_level = OptimizationLevel.NEEDS_IMPROVEMENT
        if stats["avg_response_time_ms"] <= self.config.max_response_time_ms:
            overall_level = OptimizationLevel.EXCELLENT
        elif stats["avg_response_time_ms"] <= self.config.max_response_time_ms * 2:
            overall_level = OptimizationLevel.NEEDS_IMPROVEMENT
        elif stats["avg_response_time_ms"] <= self.config.max_response_time_ms * 3:
            overall_level = OptimizationLevel.NEEDS_IMPROVEMENT
        elif stats["avg_response_time_ms"] <= self.config.max_response_time_ms * 5:
            overall_level = OptimizationLevel.NEEDS_IMPROVEMENT
        else:
            overall_level = OptimizationLevel.NEEDS_IMPROVEMENT

        return {
            "endpoint_levels": endpoint_levels,
            "level_counts": level_counts,
            "overall_level": overall_level,
            "cache_hit_rate": stats["cache_hit_rate"],
            "avg_response_time_ms": stats["avg_response_time_ms"],
            "optimization_level": overall_level,
        }

    def _generate_recommendations(self) -> list[str]:
        """生成优化建议"""
        recommendations = []

        # 缓存相关建议
        if self.get_cache_stats()["cache_hit_rate"] < 0.5:
            recommendations.append("考虑启用响应缓存以提升性能")
        else:
            recommendations.append("缓存命中率良好，可以继续监控和优化")

        # 数据库优化建议
        if self.get_performance_stats()["avg_response_time_ms"] > 1000:
            recommendations.append("建议优化数据库查询和索引")
            recommendations.append("考虑使用连接池和查询优化")

        # 响应时间建议
        overall_level = self._generate_optimization_summary()["overall_level"]
        if overall_level == OptimizationLevel.EXCELLENT:
            recommendations.append("当前性能表现优秀，建议保持配置")
        elif overall_level == OptimizationLevel.GOOD:
            recommendations.append("性能良好，建议继续优化以获得更好表现")
        elif overall_level == OptimizationLevel.NEEDS_IMPROVEMENT:
            recommendations.append("性能一般，建议分析瓶颈并优化")
        elif overall_level == OptimizationLevel.NEEDS_IMPROVEMENT:
            recommendations.append("性能需要显著改进，建议全面优化")

        return recommendations

    def get_response_time_ms(
        self, endpoint: str, response_time_ms: float
    ) -> OptimizationLevel | None:
        """获取单个端点的优化等级"""
        return self._get_optimization_level(response_time_ms, False)

    def _should_cache_response(self, response_data: Any, response_key: str) -> bool:
        """判断是否应该缓存响应"""
        # 基于数据大小、类型和配置判断
        data_size = (
            len(str(response_data))
            if isinstance(response_data, str)
            else len(response_data.encode("utf-8"))
        )

        # 小响应不缓存
        if data_size < self.config.min_size_to_cache:
            return False

        # 大响应但压缩了
        if response_key in self.cache and response_key.endswith("_compressed"):
            return False  # 已经压缩，不需要再次缓存

        return True

    def _get_cache_key(self, endpoint: str, request_data: Any) -> str:
        """生成缓存键"""
        # 基于请求内容生成唯一键
        if isinstance(request_data, dict):
            # 包含特定字段的使用dict
            fields = ["session_id", "organization_id", "method"]
            key_data = {k: str(v) for k, v in request_data.items() if k in fields}
            key_data.update(
                {
                    "data_hash": hashlib.md5(
                        str(request_data).encode("utf-8")
                    ).hexdigest()
                }
            )
            return f"{endpoint}_{key_data['data_hash']}"
        else:
            data_hash = hashlib.md5(str(request_data).encode("utf-8")).hexdigest()
            return f"{endpoint}_{data_hash}"
