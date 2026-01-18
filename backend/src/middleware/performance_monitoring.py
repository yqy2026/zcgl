"""
性能监控中间件
监控API响应时间、请求频率和资源使用情况
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Any

import psutil
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from ..core.api_errors import bad_request

logger = logging.getLogger(__name__)


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """性能监控中间件"""

    def __init__(self, app: Any, max_requests_per_minute: int = 1000) -> None:
        super().__init__(app)
        self.max_requests_per_minute = max_requests_per_minute
        self.request_count: dict[str, int] = {}
        self.response_times: dict[str, list[float]] = {}
        self.error_counts: dict[str, int] = {}
        self.slow_queries: list[dict[str, Any]] = []

        # 每分钟重置计数器
        self._reset_task = asyncio.create_task(self._reset_counters())

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """处理请求并收集性能指标"""

        # 获取请求开始时间
        start_time = time.time()
        client_ip = self._get_client_ip(request)
        path = request.url.path

        # 请求频率检查
        if not await self._check_rate_limit(client_ip):
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            raise bad_request("请求过于频繁，请稍后再试")

        # 记录请求
        await self._record_request(path)

        try:
            # 处理请求
            response = await call_next(request)

            # 计算响应时间
            process_time = time.time() - start_time
            await self._record_response_time(path, process_time)

            # 添加性能头
            response.headers["X-Process-Time"] = str(round(process_time, 4))
            response.headers["X-Request-ID"] = str(id(request))

            # 记录慢请求
            if process_time > 2.0:  # 超过2秒的请求
                await self._record_slow_query(path, process_time, request.method)

            # 记录性能日志
            logger.info(
                f"{request.method} {path} - "
                f"Status: {response.status_code} - "
                f"Time: {process_time:.4f}s - "
                f"IP: {client_ip}"
            )

            return response

        except Exception as e:
            # 记录错误
            await self._record_error(path, str(e))
            logger.error(f"Request failed: {request.method} {path} - Error: {str(e)}")
            raise

    def _get_client_ip(self, request: Request) -> str:
        """获取客户端真实IP"""
        # 检查代理头
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # 返回直接连接的IP
        return request.client.host if request.client else "unknown"

    async def _check_rate_limit(self, client_ip: str) -> bool:
        """检查请求频率限制"""
        current_minute = datetime.now().strftime("%Y-%m-%d %H:%M")
        key = f"{client_ip}:{current_minute}"

        count = self.request_count.get(key, 0)
        if count >= self.max_requests_per_minute:
            return False

        self.request_count[key] = count + 1
        return True

    async def _record_request(self, path: str) -> None:
        """记录请求统计"""
        # 按路径分组统计
        if path not in self.response_times:
            self.response_times[path] = []

    async def _record_response_time(self, path: str, process_time: float) -> None:
        """记录响应时间"""
        if path in self.response_times:
            # 保留最近100个请求的响应时间
            times = self.response_times[path]
            times.append(process_time)
            if len(times) > 100:
                times.pop(0)

    async def _record_slow_query(
        self, path: str, process_time: float, method: str
    ) -> None:
        """记录慢查询"""
        self.slow_queries.append(
            {
                "path": path,
                "method": method,
                "process_time": process_time,
                "timestamp": datetime.now().isoformat(),
            }
        )

        # 保留最近50个慢查询记录
        if len(self.slow_queries) > 50:
            self.slow_queries.pop(0)

    async def _record_error(self, path: str, error: str) -> None:
        """记录错误统计"""
        self.error_counts[path] = self.error_counts.get(path, 0) + 1

    async def _reset_counters(self) -> None:
        """每分钟重置计数器"""
        while True:
            try:
                await asyncio.sleep(60)  # 等待1分钟

                # 清理过期的请求计数
                current_minute = datetime.now().strftime("%Y-%m-%d %H:%M")
                expired_keys = [
                    key
                    for key in self.request_count.keys()
                    if key.split(":")[1] != current_minute
                ]
                for key in expired_keys:
                    del self.request_count[key]

                # 记录系统性能指标
                await self._log_system_performance()

            except Exception as e:
                logger.error(f"Performance monitoring reset error: {e}")

    async def _log_system_performance(self) -> None:
        """记录系统性能指标"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)

            # 内存使用率
            memory = psutil.virtual_memory()
            memory_percent = memory.percent

            # 磁盘使用率
            disk = psutil.disk_usage("/")
            disk_percent = (disk.used / disk.total) * 100

            # 网络IO
            network = psutil.net_io_counters()

            logger.info(
                f"System Performance - "
                f"CPU: {cpu_percent}% | "
                f"Memory: {memory_percent}% | "
                f"Disk: {disk_percent:.1f}% | "
                f"Network Sent: {network.bytes_sent / (1024**2):.1f}MB | "
                f"Network Recv: {network.bytes_recv / (1024**2):.1f}MB"
            )

            # 性能警告
            if cpu_percent > 80:
                logger.warning(f"High CPU usage: {cpu_percent}%")
            if memory_percent > 85:
                logger.warning(f"High memory usage: {memory_percent}%")
            if disk_percent > 90:
                logger.warning(f"High disk usage: {disk_percent:.1f}%")

        except Exception as e:
            logger.error(f"Failed to log system performance: {e}")

    def get_performance_stats(self) -> dict[str, Any]:
        """获取性能统计信息"""
        stats = {
            "request_count": len(self.request_count),
            "monitored_paths": len(self.response_times),
            "error_count": sum(self.error_counts.values()),
            "slow_queries_count": len(self.slow_queries),
            "system_info": {},
        }

        # 计算平均响应时间
        path_stats = {}
        for path, times in self.response_times.items():
            if times:
                path_stats[path] = {
                    "avg_time": sum(times) / len(times),
                    "max_time": max(times),
                    "min_time": min(times),
                    "request_count": len(times),
                }

        stats["path_performance"] = path_stats

        # 系统信息
        try:
            stats["system_info"] = {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": (
                    psutil.disk_usage("/").used / psutil.disk_usage("/").total
                )
                * 100,
            }
        except Exception:  # nosec - B110: Intentional graceful degradation for optional system metrics
            pass

        return stats

    def get_slow_queries(self, limit: int = 10) -> list[dict[str, Any]]:
        """获取慢查询列表"""
        return sorted(self.slow_queries, key=lambda x: x["process_time"], reverse=True)[
            :limit
        ]

    async def cleanup(self) -> None:
        """清理资源"""
        if self._reset_task:
            self._reset_task.cancel()
            try:
                await self._reset_task
            except asyncio.CancelledError:
                pass
