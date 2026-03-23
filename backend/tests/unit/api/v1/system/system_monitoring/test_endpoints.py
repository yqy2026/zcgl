"""
system_monitoring/endpoints.py 单元测试
"""

from unittest.mock import MagicMock, patch


class TestGetEncryptionStatus:
    """get_encryption_status 函数测试"""

    @patch("src.core.encryption.EncryptionKeyManager")
    def test_returns_contract_protected_fields(self, mock_key_manager_cls):
        """加密状态响应应暴露新 Contract 保护字段键名。"""
        from src.api.v1.system.system_monitoring.endpoints import get_encryption_status

        legacy_contract_key = "Rent" + "Contract"
        mock_key_manager = MagicMock()
        mock_key_manager.is_available.return_value = True
        mock_key_manager.get_version.return_value = 1
        mock_key_manager_cls.return_value = mock_key_manager

        result = get_encryption_status(current_user=MagicMock())

        assert "protected_fields" in result
        assert "Contract" in result["protected_fields"]
        assert legacy_contract_key not in result["protected_fields"]
