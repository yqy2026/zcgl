import pytest
from unittest.mock import Mock, patch
from src.services.property_certificate.service import PropertyCertificateService


def test_service_initialization():
    """测试服务初始化"""
    mock_db = Mock()

    # Mock all the dependencies
    with patch('src.services.property_certificate.service.PromptManager'), \
         patch('src.services.property_certificate.service.AssetMatchingService'), \
         patch('src.services.property_certificate.service.PropertyCertAdapter'):

        service = PropertyCertificateService(mock_db)
        assert service.db is mock_db