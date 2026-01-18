import pytest
from unittest.mock import Mock, MagicMock
from src.services.property_certificate.matcher import AssetMatchingService, AssetMatch


class TestAssetMatchingService:
    """资产匹配服务测试"""

    def test_find_matches_empty_inputs(self):
        """测试空输入"""
        # Mock database session
        mock_db = Mock()
        mock_db.query.return_value.all.return_value = []

        matcher = AssetMatchingService(mock_db)
        matches = matcher.find_matches(
            property_address=None,
            property_name=None
        )

        assert len(matches) == 0

    def test_find_matches_with_assets(self):
        """测试有资产的匹配"""
        # Mock database session
        mock_db = Mock()

        # Mock asset object
        mock_asset = Mock()
        mock_asset.id = "test-asset-id"
        mock_asset.property_name = "测试物业"
        mock_asset.address = "测试地址"
        mock_asset.ownership_entity = "测试权属人"

        mock_db.query.return_value.all.return_value = [mock_asset]

        matcher = AssetMatchingService(mock_db)
        matches = matcher.find_matches(
            property_address="测试地址",
            property_name=None
        )

        assert len(matches) > 0
        assert matches[0].asset_id == "test-asset-id"
        assert matches[0].confidence >= 0.5

    def test_calculate_match_score_address_match(self):
        """测试地址匹配分数计算"""
        # Mock asset object
        mock_asset = Mock()
        mock_asset.address = "北京市朝阳区某某街道123号"
        mock_asset.property_name = "测试物业"
        mock_asset.ownership_entity = "测试权属人"

        matcher = AssetMatchingService(Mock())

        # Test address match
        score, reasons = matcher._calculate_match_score(
            mock_asset,
            "北京市朝阳区某某街道123号",
            None,
            None
        )

        assert score >= 0.5
        assert "地址相似度" in reasons[0]

    def test_calculate_match_score_name_match(self):
        """测试名称匹配分数计算"""
        # Mock asset object
        mock_asset = Mock()
        mock_asset.address = "北京市朝阳区某某街道123号"
        mock_asset.property_name = "测试物业"
        mock_asset.ownership_entity = "测试权属人"

        matcher = AssetMatchingService(Mock())

        # Test name match
        score, reasons = matcher._calculate_match_score(
            mock_asset,
            None,
            "测试物业",
            None
        )

        assert score >= 0.3
        assert "名称相似度" in reasons[0]

    def test_calculate_match_score_owner_match(self):
        """测试权属方匹配分数计算"""
        # Mock asset object
        mock_asset = Mock()
        mock_asset.address = "北京市朝阳区某某街道123号"
        mock_asset.property_name = "测试物业"
        mock_asset.ownership_entity = "测试权属人"

        matcher = AssetMatchingService(Mock())

        # Test owner match
        score, reasons = matcher._calculate_match_score(
            mock_asset,
            None,
            None,
            "测试权属人"
        )

        assert score >= 0.2
        assert "权属方匹配" in reasons[0]

    def test_calculate_match_score_no_match(self):
        """测试无匹配"""
        # Mock asset object
        mock_asset = Mock()
        mock_asset.address = "北京市朝阳区某某街道123号"
        mock_asset.property_name = "测试物业"
        mock_asset.ownership_entity = "测试权属人"

        matcher = AssetMatchingService(Mock())

        # Test no match
        score, reasons = matcher._calculate_match_score(
            mock_asset,
            "完全不相关的地址",
            "完全不相关的名称",
            "完全不相关的权属人"
        )

        assert score == 0.0
        assert len(reasons) == 0

    def test_find_matches_top_n_limitation(self):
        """测试返回数量限制"""
        # Mock database session with multiple assets
        mock_db = Mock()

        # Create mock assets
        mock_assets = []
        for i in range(5):
            mock_asset = Mock()
            mock_asset.id = f"test-asset-{i}"
            mock_asset.address = "测试地址"
            mock_asset.property_name = "测试物业"
            mock_asset.ownership_entity = "测试权属人"
            mock_assets.append(mock_asset)

        mock_db.query.return_value.all.return_value = mock_assets

        matcher = AssetMatchingService(mock_db)
        matches = matcher.find_matches(
            property_address="测试地址",
            property_name=None,
            top_n=2
        )

        assert len(matches) == 2

    def test_find_matches_below_threshold(self):
        """测试低于阈值的匹配不返回"""
        # Mock database session with asset that has low similarity
        mock_db = Mock()

        # Mock asset object with different address
        mock_asset = Mock()
        mock_asset.id = "test-asset-id"
        mock_asset.address = "完全不同的地址"
        mock_asset.property_name = "完全不同的名称"
        mock_asset.ownership_entity = "完全不同的权属人"

        mock_db.query.return_value.all.return_value = [mock_asset]

        matcher = AssetMatchingService(mock_db)
        matches = matcher.find_matches(
            property_address="测试地址",
            property_name="测试物业",
            owner_name="测试权属人"
        )

        # Should return empty since similarities are below threshold
        assert len(matches) == 0