from typing import Any
"""
PDF处理结果缓存服务
提供智能缓存机制，提升处理性能和用户体验
"""

import hashlib
import json
import logging
from datetime import UTC, datetime
from pathlib import Path


logger = logging.getLogger(__name__)


class PDFProcessingCache:
    """PDF处理结果缓存服务"""

    def __init__(
        self, cache_dir: str = "cache/pdf_processing", max_cache_size: int = 100
    ):
        """
        初始化PDF处理缓存

        Args:
            cache_dir: 缓存目录
            max_cache_size: 最大缓存条目数
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "pdf_cache.json"
        self.max_cache_size = max_cache_size
        self.cache = {}

        # 启动时加载现有缓存
        self._load_cache()

    def _generate_cache_key(self, file_path: Path, method: str, **kwargs) -> str:
        """生成缓存键"""
        # 基于文件路径、大小、修改时间和处理方法生成唯一键
        file_stat = file_path.stat()
        method_params = "_".join(
            sorted(f"{k}_{v}" for k, v in kwargs.items() if v is not None)
        )

        key_data = [
            str(file_path),  # 文件路径
            str(file_stat.st_size),  # 文件大小
            str(int(file_stat.st_mtime)),  # 修改时间
            method,  # 处理方法
            method_params,  # 方法参数
        ]

        return hashlib.md5("_".join(key_data).encode()).hexdigest()

    def _load_cache(self) -> None:
        """加载缓存文件"""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, encoding="utf-8") as f:
                    self.cache = json.load(f)
                    logger.info(f"已加载 {len(self.cache)} 个PDF处理缓存条目")
                    # 清理过期缓存
                    self._cleanup_expired_cache()
            else:
                logger.info("缓存文件不存在，创建新缓存")
        except Exception as e:
            logger.error(f"加载缓存失败: {e}")
            self.cache = {}

    def _save_cache(self) -> None:
        """保存缓存文件"""
        try:
            # 按LRU策略限制缓存大小
            if len(self.cache) > self.max_cache_size:
                # 获取所有缓存项的访问时间
                cache_items = list(self.cache.items())
                cache_items.sort(key=lambda x: x[1]["access_time"], reverse=True)

                # 保留最近的缓存项
                self.cache = dict(cache_items[: self.max_cache_size])
                logger.info(f"缓存已满，清理到 {self.max_cache_size} 个条目")

            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
                logger.info(f"缓存已保存，包含 {len(self.cache)} 个条目")
        except Exception as e:
            logger.error(f"保存缓存失败: {e}")

    def _cleanup_expired_cache(self, max_age_hours: int = 24) -> None:
        """清理过期缓存"""
        current_time = datetime.now(UTC).timestamp()
        expired_keys = []

        for key, value in self.cache.items():
            if "access_time" in value:
                access_time = value["access_time"]
                if (current_time - access_time) > max_age_hours * 3600:
                    expired_keys.append(key)

        for key in expired_keys:
            del self.cache[key]

        if expired_keys:
            logger.info(f"清理了 {len(expired_keys)} 个过期缓存条目")

    def get(self, file_path: Path, method: str, **kwargs) -> dict[str, Any] | None:
        """获取缓存结果"""
        cache_key = self._generate_cache_key(file_path, method, **kwargs)

        if cache_key in self.cache:
            cache_entry = self.cache[cache_key]
            cache_entry["access_time"] = datetime.now(UTC).timestamp()
            logger.info(f"缓存命中: {cache_key}")
            return cache_entry["result"]

        return None

    def set(
        self, file_path: Path, method: str, result: dict[str, Any], **kwargs
    ) -> None:
        """设置缓存结果"""
        cache_key = self._generate_cache_key(file_path, method, **kwargs)

        self.cache[cache_key] = {
            "result": result,
            "access_time": datetime.now(UTC).timestamp(),
            "file_size": file_path.stat().st_size,
            "processing_time": result.get("processing_time_seconds", 0),
            "method": method,
            "success": result.get("success", False),
        }

        # 检查缓存大小限制
        if len(self.cache) > self.max_cache_size:
            self._cleanup_expired_cache()

        logger.info(f"缓存已设置: {cache_key}")
        self._save_cache()

    def clear(self, pattern: str = None) -> None:
        """清理缓存"""
        if pattern:
            # 清理匹配模式的缓存
            keys_to_remove = [k for k in self.cache.keys() if pattern in k]
        else:
            # 清理所有缓存
            keys_to_remove = list(self.cache.keys())

        for key in keys_to_remove:
            del self.cache[key]

        logger.info(f"清理缓存: {len(keys_to_remove)} 个条目")
        self._save_cache()

    def get_cache_stats(self) -> dict[str, Any]:
        """获取缓存统计信息"""
        total_entries = len(self.cache)
        successful_entries = sum(
            1 for v in self.cache.values() if v.get("success", False)
        )
        failed_entries = total_entries - successful_entries

        return {
            "total_entries": total_entries,
            "successful_entries": successful_entries,
            "failed_entries": failed_entries,
            "success_rate": successful_entries / total_entries
            if total_entries > 0
            else 0,
            "cache_file_size": self.cache_file.stat().st_size
            if self.cache_file.exists()
            else 0,
        }
