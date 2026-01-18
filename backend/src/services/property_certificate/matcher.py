"""
Asset Matching Service
智能资产匹配服务
"""

from dataclasses import dataclass
from difflib import SequenceMatcher

from sqlalchemy.orm import Session
from src.models.asset import Asset


@dataclass
class AssetMatch:
    """资产匹配结果"""
    asset_id: str
    name: str
    address: str
    confidence: float
    match_reasons: list[str]


class AssetMatchingService:
    """资产匹配服务"""

    def __init__(self, db: Session):
        self.db = db

    def find_matches(
        self,
        property_address: str | None,
        property_name: str | None,
        owner_name: str | None = None,
        top_n: int = 3
    ) -> list[AssetMatch]:
        """查找匹配的资产"""
        if not property_address and not property_name:
            return []

        # Get all assets
        assets = self.db.query(Asset).all()

        # Score each asset
        scored_matches = []
        for asset in assets:
            score, reasons = self._calculate_match_score(
                asset,
                property_address,
                property_name,
                owner_name
            )
            if score > 0.3:  # Minimum threshold
                scored_matches.append(AssetMatch(
                    asset_id=asset.id,
                    name=asset.property_name,
                    address=asset.address,
                    confidence=score,
                    match_reasons=reasons
                ))

        # Sort by confidence and return top N
        scored_matches.sort(key=lambda x: x.confidence, reverse=True)
        return scored_matches[:top_n]

    def _calculate_match_score(
        self,
        asset: Asset,
        property_address: str | None,
        property_name: str | None,
        owner_name: str | None
    ) -> tuple[float, list[str]]:
        """计算匹配置信度"""
        score = 0.0
        reasons = []

        # Address similarity (highest weight: 0.5)
        if property_address and asset.address:
            address_sim = SequenceMatcher(None, property_address, asset.address).ratio()
            if address_sim > 0.6:
                score += 0.5 * address_sim
                reasons.append(f"地址相似度: {address_sim:.0%}")

        # Name similarity (medium weight: 0.3)
        if property_name and asset.property_name:
            name_sim = SequenceMatcher(None, property_name, asset.property_name).ratio()
            if name_sim > 0.5:
                score += 0.3 * name_sim
                reasons.append(f"名称相似度: {name_sim:.0%}")

        # Owner match (lower weight: 0.2)
        if owner_name and asset.ownership_entity:
            owner_sim = SequenceMatcher(None, owner_name, asset.ownership_entity).ratio()
            if owner_sim > 0.7:
                score += 0.2 * owner_sim
                reasons.append(f"权属方匹配: {owner_sim:.0%}")

        return score, reasons