#!/usr/bin/env python3
from typing import Any

"""
Contract Extractor Manager
Manages all contract extractors and provides the best extraction strategy
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ContractExtractorManager:
    """Contract Extractor Manager"""

    def __init__(self):
        """Initialize extractor manager"""
        self.extractors = {}
        self._load_extractors()

    def _load_extractors(self):
        """Load all extractors"""
        try:
            # Import contract extractor (main extractor)
            from .contract_extractor import extract_contract_info

            self.extractors["main"] = extract_contract_info
            logger.info("Contract extractor loaded successfully")
        except Exception as e:
            logger.warning(f"Contract extractor failed to load: {e}")

    def extract_contract_info(
        self, text: str, strategy: str = "auto"
    ) -> dict[str, Any]:
        """
        Extract contract information

        Args:
            text: Contract text
            strategy: Extraction strategy ('auto', 'ultra_enhanced', 'enhanced', 'rent_contract', 'fallback')

        Returns:
            Extraction result dictionary
        """
        if strategy == "auto":
            return self._auto_extract(text)
        elif strategy in self.extractors:
            return self._extract_with_strategy(text, strategy)
        else:
            logger.warning(f"未知的提取策�? {strategy}")
            return self._auto_extract(text)

    def _auto_extract(self, text: str) -> dict[str, Any]:
        """Automatically select best extraction strategy"""
        results = {}

        # Use main extractor
        if "main" in self.extractors:
            try:
                result = self._extract_with_strategy(text, "main")
                if result.get("success") and result.get("overall_confidence", 0) > 0.7:
                    logger.info("Main extractor used successfully")
                    return result
                results["main"] = result
            except Exception as e:
                logger.warning(f"Main extractor execution failed: {e}")

        # If all extractors fail, return best result
        if results:
            best_result = max(
                results.values(), key=lambda x: x.get("overall_confidence", 0)
            )
            logger.warning(
                f"All extractors performed poorly, returning best result (confidence: {best_result.get('overall_confidence', 0):.2f})"
            )
            return best_result

        # Complete failure
        return {
            "success": False,
            "error": "All extractors failed to process the text",
            "overall_confidence": 0.0,
            "extraction_summary": {
                "attempted_strategies": list(self.extractors.keys()),
                "all_failed": True,
            },
        }

    def _extract_with_strategy(self, text: str, strategy: str) -> dict[str, Any]:
        """Extract information using specified strategy"""
        if strategy not in self.extractors:
            raise ValueError(f"Unknown extraction strategy: {strategy}")

        try:
            result = self.extractors[strategy](text)
            result["extraction_strategy"] = strategy
            result["extraction_time"] = datetime.now().isoformat()
            return result
        except Exception as e:
            logger.error(f"Extraction strategy {strategy} execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "extraction_strategy": strategy,
                "overall_confidence": 0.0,
            }

    def get_available_strategies(self) -> list[str]:
        """Get available extraction strategies"""
        return list(self.extractors.keys())

    def get_strategy_info(self) -> dict[str, Any]:
        """Get extractor information"""
        return {
            "available_strategies": self.get_available_strategies(),
            "total_extractors": len(self.extractors),
            "recommended_strategy": "primary"
            if "primary" in self.extractors
            else "standard",
            "manager_version": "2.0.0",
        }


# Global instance
extractor_manager = ContractExtractorManager()


def extract_contract_info(text: str, strategy: str = "auto") -> dict[str, Any]:
    """
    Convenient function to extract contract information

    Args:
        text: Contract text
        strategy: Extraction strategy

    Returns:
        Extraction result dictionary
    """
    return extractor_manager.extract_contract_info(text, strategy)


def get_extractor_info() -> dict[str, Any]:
    """Get extractor information"""
    return extractor_manager.get_strategy_info()
