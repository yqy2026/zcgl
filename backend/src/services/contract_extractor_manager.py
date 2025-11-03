#!/usr/bin/env python3
from typing import Any

"""
合同提取器管理器
统一管理所有合同提取器，提供最佳提取策略
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ContractExtractorManager:
    """合同提取器管理器"""

    def __init__(self):
        """初始化提取器管理器"""
        self.extractors = {}
        self._load_extractors()

    def _load_extractors(self):
        """加载所有提取器"""
        try:
            # 导入合同提取器（主要提取器）
            from .contract_extractor import extract_contract_info

            self.extractors["main"] = extract_contract_info
            logger.info("合同提取器加载成功")
        except Exception as e:
            logger.warning(f"合同提取器加载失败: {e}")

    def extract_contract_info(
        self, text: str, strategy: str = "auto"
    ) -> dict[str, Any]:
        """
        提取合同信息

        Args:
            text: 合同文本
            strategy: 提取策略 ('auto', 'ultra_enhanced', 'enhanced', 'rent_contract', 'fallback')

        Returns:
            提取结果字典
        """
        if strategy == "auto":
            return self._auto_extract(text)
        elif strategy in self.extractors:
            return self._extract_with_strategy(text, strategy)
        else:
            logger.warning(f"未知的提取策略: {strategy}")
            return self._auto_extract(text)

    def _auto_extract(self, text: str) -> dict[str, Any]:
        """自动选择最佳提取策略"""
        results = {}

        # 使用主提取器
        if "main" in self.extractors:
            try:
                result = self._extract_with_strategy(text, "main")
                if result.get("success") and result.get("overall_confidence", 0) > 0.7:
                    logger.info("使用主提取器成功")
                    return result
                results["main"] = result
            except Exception as e:
                logger.warning(f"主提取器执行失败: {e}")

        # 如果所有提取器都失败，返回最佳结果
        if results:
            best_result = max(
                results.values(), key=lambda x: x.get("overall_confidence", 0)
            )
            logger.warning(
                f"所有提取器效果不佳，返回最佳结果 (置信度: {best_result.get('overall_confidence', 0):.2f})"
            )
            return best_result

        # 完全失败
        return {
            "success": False,
            "error": "所有提取器都无法处理该文本",
            "overall_confidence": 0.0,
            "extraction_summary": {
                "attempted_strategies": list(self.extractors.keys()),
                "all_failed": True,
            },
        }

    def _extract_with_strategy(self, text: str, strategy: str) -> dict[str, Any]:
        """使用指定策略提取信息"""
        if strategy not in self.extractors:
            raise ValueError(f"未知的提取策略: {strategy}")

        try:
            result = self.extractors[strategy](text)
            result["extraction_strategy"] = strategy
            result["extraction_time"] = datetime.now().isoformat()
            return result
        except Exception as e:
            logger.error(f"提取策略 {strategy} 执行失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "extraction_strategy": strategy,
                "overall_confidence": 0.0,
            }

    def get_available_strategies(self) -> list[str]:
        """获取可用的提取策略"""
        return list(self.extractors.keys())

    def get_strategy_info(self) -> dict[str, Any]:
        """获取提取器信息"""
        return {
            "available_strategies": self.get_available_strategies(),
            "total_extractors": len(self.extractors),
            "recommended_strategy": "primary"
            if "primary" in self.extractors
            else "standard",
            "manager_version": "2.0.0",
        }


# 全局实例
extractor_manager = ContractExtractorManager()


def extract_contract_info(text: str, strategy: str = "auto") -> dict[str, Any]:
    """
    提取合同信息的便捷函数

    Args:
        text: 合同文本
        strategy: 提取策略

    Returns:
        提取结果字典
    """
    return extractor_manager.extract_contract_info(text, strategy)


def get_extractor_info() -> dict[str, Any]:
    """获取提取器信息"""
    return extractor_manager.get_strategy_info()
