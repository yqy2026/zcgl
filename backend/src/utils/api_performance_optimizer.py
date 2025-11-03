#!/usr/bin/env python
"""
API响应时间优化器
提供快速响应、缓存、异步处理等优化功能
"""

import hashlib
import logging
import time
from collections.abc import Callable
from datetime import datetime
from functools import wraps
from typing import Any

logger = logging.getLogger(__name__)


class PerformanceOptimizer:
    """API性能优化器"""

    def __init__(self):
        self.response_cache = {}  # 简单缓存
        self.request_times = {}  # 请求时间记录
        self.slow_requests = []  # 慢请求记录
        self.performance_stats = {
            "total_requests": 0,
            "avg_response_time": 0.0,
            "max_response_time": 0.0,
            "slow_requests_count": 0,
            "cache_hit_rate": 0.0,
            "error_rate": 0.0,
        }

    def timing_decorator(self, target_time_ms: float = 500.0):
        """性能监控装饰器"""

        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                start_time = time.time()

                try:
                    result = await func(*args, **kwargs)

                    # 记录性能统计
                    response_time = (time.time() - start_time) * 1000  # 转换为毫秒

                    self._record_performance_stats(response_time)

                    # 检查是否超出目标时间
                    if response_time > target_time_ms:
                        self._record_slow_request(
                            func.__name__, response_time, args, kwargs
                        )
                        logger.warning(
                            f"API响应缓慢: {func.__name__} 耗时 {response_time:.1f}ms "
                            f"(目标: {target_time_ms:.1f}ms)"
                        )

                    return result

                except Exception as e:
                    self._record_error(func.__name__, str(e))
                    logger.error(f"API处理异常: {func.__name__} - {str(e)}")
                    raise

            return wrapper

        return decorator

    def _record_performance_stats(self, response_time: float):
        """记录性能统计"""
        self.performance_stats["total_requests"] += 1

        # 更新平均响应时间
        total = self.performance_stats["total_requests"]
        current_avg = self.performance_stats["avg_response_time"]
        new_avg = ((current_avg * (total - 1)) + response_time) / total
        self.performance_stats["avg_response_time"] = new_avg

        # 更新最大响应时间
        if response_time > self.performance_stats["max_response_time"]:
            self.performance_stats["max_response_time"] = response_time

    def _record_slow_request(self, func_name: str, response_time: float, args, kwargs):
        """记录慢请求"""
        self.slow_requests.append(
            {
                "function": func_name,
                "response_time": response_time,
                "args_count": len(args) + len(kwargs),
                "timestamp": datetime.now().isoformat(),
                "args": {k: str(v) for k, v in list(args) + list(kwargs)},
                "details": f"响应时间: {response_time:.1f}ms",
            }
        )
        self.performance_stats["slow_requests_count"] += 1

    def _record_error(self, func_name: str, error: str):
        """记录错误"""
        self.performance_stats["error_rate"] += 1
        logger.error(f"API错误: {func_name} - {error}")

    async def async_cache_result(
        self, cache_key: str, func: Callable, *args, **kwargs
    ) -> Any:
        """异步缓存装饰器"""
        # 检查缓存
        if cache_key in self.response_cache:
            cached_result, timestamp = self.response_cache[cache_key]
            age = (datetime.now() - timestamp).total_seconds()

            if age < 300:  # 5分钟内的缓存
                logger.info(f"缓存命中: {cache_key} (缓存时间: {age:.1f}秒)")
                self.performance_stats["cache_hit_rate"] += 1
                return cached_result
            else:
                # 移除过期缓存
                if cache_key in self.response_cache:
                    del self.response_cache[cache_key]
                    logger.info(f"缓存过期已移除: {cache_key}")

        # 执行函数
        start_time = time.time()
        result = await func(*args, **kwargs)

        # 缓存结果（排除错误结果）
        if self._should_cache_result(result):
            self.response_cache[cache_key] = (result, datetime.now())
            logger.info(f"结果已缓存: {cache_key}")
        else:
            logger.info(
                f"结果未缓存: {cache_key} - {self._should_cache_result(result)}"
            )

        # 记录性能
        response_time = (time.time() - start_time) * 1000
        self._record_performance_stats(response_time)

        return result

    def _should_cache_result(self, result: Any) -> bool:
        """判断是否应该缓存结果"""
        # 只缓存成功的、较小的结果
        try:
            # 检查是否为字典且包含success字段
            if isinstance(result, dict):
                is_success = result.get("success", False)
                text_length = len(str(result.get("text_extracted", "")))

                return is_success and text_length < 1000  # 成功且文本不太大
            return False
        except (Exception, ValueError, TypeError):
            # 通用异常处理时返回False
            return False

    def get_cache_key(self, *args, **kwargs) -> str:
        """生成缓存键"""
        # 使用函数名和参数生成唯一键
        key_parts = []
        key_parts.append(args[0].__name__ if args else "unknown")

        # 添加关键参数
        if "file" in kwargs:
            key_parts.append(
                f"file_{hashlib.md5(kwargs['file'].filename.encode('utf-8')).hexdigest()}"
            )

        if "options" in kwargs:
            options_str = str(sorted(kwargs["options"].items()))
            key_parts.append(
                f"options_{hashlib.md5(options_str.encode('utf-8')).hexdigest()}"
            )

        return "_".join(key_parts)

    def get_performance_report(self) -> dict[str, Any]:
        """获取性能报告"""
        now = datetime.now()

        return {
            "timestamp": now.isoformat(),
            "performance_stats": self.performance_stats,
            "cache_stats": {
                "cache_size": len(self.response_cache),
                "cache_hit_rate": self.performance_stats["cache_hit_rate"]
                / max(self.performance_stats["total_requests"], 1),
                "cache_hit_details": [
                    f"{k}: {v[0]},{v[1].isoformat()}"
                    for k, v in list(self.response_cache.items())[-5:]
                ],
            },
            "slow_requests_summary": {
                "count": len(self.slow_requests),
                "count_in_last_hour": len(
                    [
                        r
                        for r in self.slow_requests
                        if (
                            now - datetime.fromisoformat(r["timestamp"])
                        ).total_seconds()
                        < 3600
                    ]
                ),
                "avg_response_time": sum(r["response_time"] for r in self.slow_requests)
                / len(self.slow_requests)
                if self.slow_requests
                else 0,
                "slowest_requests": sorted(
                    self.slow_requests, key=lambda x: x["response_time"], reverse=True
                )[:3],
            },
            "recommendations": self._generate_optimization_recommendations(),
            "request_patterns": self._analyze_request_patterns(),
        }

    def _generate_optimization_recommendations(self) -> list[str]:
        """生成优化建议"""
        recommendations = []

        avg_time = self.performance_stats["avg_response_time"]
        slow_count = self.performance_stats["slow_requests_count"]
        total_requests = self.performance_stats["total_requests"]

        # 响应时间建议
        if avg_time > 1000:  # 大于1秒
            recommendations.append("平均响应时间较长(>1s)，建议优化数据库查询")
        elif avg_time > 500:  # 大于500ms
            recommendations.append("建议减少外部API调用时间")

        # 错误率建议
        error_rate = (
            (self.performance_stats["error_rate"] / total_requests) * 100
            if total_requests > 0
            else 0
        )
        if error_rate > 5:
            recommendations.append("错误率较高，建议增强错误处理机制")

        # 慢请求建议
        if slow_count > total_requests * 0.05:  # 超过5%的请求慢
            recommendations.append("慢请求较多，建议分析瓶颈并优化")

        # 缓存效率建议
        cache_hit_rate = (
            self.performance_stats["cache_hit_rate"] / total_requests * 100
            if total_requests > 0
            else 0
        )
        if cache_hit_rate < 30:
            recommendations.append("缓存命中率较低，建议增加缓存策略")

        if not recommendations:
            recommendations.append("性能表现良好，建议保持当前配置")

        return recommendations

    def _analyze_request_patterns(self) -> dict[str, Any]:
        """分析请求模式"""
        if not self.slow_requests:
            return {"patterns": [], "analysis": "无慢请求数据"}

        # 分析慢请求模式
        functions = {}
        for request in self.slow_requests[-10:]:  # 最近10个慢请求
            func_name = request["function"]
            functions[func_name] = functions.get(
                func_name, {"count": 0, "avg_time": 0.0}
            )
            functions[func_name]["count"] += 1
            functions[func_name]["avg_time"] += request["response_time"]

        return {
            "patterns": [
                {"function": k, "count": v["count"], "avg_time": v["avg_time"]}
                for k, v in functions.items()
            ],
            "analysis": "已分析慢请求模式，建议针对性优化",
        }

    def clear_cache(self):
        """清空缓存"""
        self.response_cache.clear()
        logger.info("性能缓存已清空")

    def clear_old_cache(self, max_age_minutes: int = 30):
        """清空旧缓存"""
        now = datetime.now()
        keys_to_remove = []

        for key, (result, timestamp) in self.response_cache.items():
            age = (now - timestamp).total_seconds()
            if age > max_age_minutes * 60:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self.response_cache[key]

        logger.info(f"已清空{len(keys_to_remove)}个过期缓存条目")


# 创建全局性能优化器实例
performance_optimizer = PerformanceOptimizer()
logger.info("API性能优化器初始化完成")


def optimize_api_response_time(target_ms: float = 500.0):
    """快速响应时间优化装饰器"""
    return performance_optimizer.timing_decorator(target_ms)


def cache_api_result(cache_duration_minutes: int = 5):
    """异步缓存装饰器"""
    return performance_optimizer.async_cache_result


def get_performance_stats():
    """获取性能统计"""
    return performance_optimizer.get_performance_report()


def clear_performance_cache():
    """清空性能缓存"""
    return performance_optimizer.clear_cache()


# 性能监控中间件
class PerformanceMiddleware:
    """性能监控中间件"""

    def __init__(self):
        self.optimizer = performance_optimizer

    async def __call__(self, request, call_next):
        start_time = time.time()

        # 执行下一个中间件
        response = await call_next(request)

        # 记录性能（如果response有body）
        if hasattr(response, "body"):
            response_time = (time.time() - start_time) * 1000
            self.optimizer._record_performance_stats(response_time)

            # 添加性能信息到响应头
            if hasattr(response, "headers"):
                response.headers["X-Response-Time"] = f"{response_time:.1f}ms"
                if response_time > 1000:
                    response.headers["X-Performance-Warning"] = "slow-response"

            # 如果响应太慢，记录详细日志
            if response_time > 2000:  # 大于2秒
                logger.warning(
                    f"慢响应检测: {request.method} {request.url} - {response_time:.1f}ms"
                )

        return response
