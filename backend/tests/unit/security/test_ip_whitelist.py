"""
Unit tests for IP Whitelist Manager

Tests IP range validation, dangerous range blocking, and environment-specific behavior.
"""

import os
from ipaddress import IPv4Network, ip_network
from unittest.mock import patch

# Set test environment before importing
os.environ["TESTING_MODE"] = "true"

from src.security.ip_whitelist import IPRange, IPWhitelistManager, ip_whitelist


class TestIPRange:
    """Test IPRange data class"""

    def test_ip_range_creation(self):
        """Test creating IPRange with valid CIDR"""
        ip_range = IPRange(cidr="192.168.1.0/24", added_by="admin")
        assert ip_range.cidr == "192.168.1.0/24"
        assert ip_range.added_by == "admin"
        assert ip_range.network == ip_network("192.168.1.0/24")
        assert ip_range.created_at is not None


class TestIPWhitelistManagerInit:
    """Test IPWhitelistManager initialization"""

    def test_init_default(self):
        """Test default initialization"""
        manager = IPWhitelistManager()
        assert len(manager.whitelist) == 0
        assert manager.env is not None

    def test_load_from_env(self):
        """Test loading whitelist from environment variable"""
        import os

        # Set the environment variable before creating manager
        original_value = os.environ.get("IP_WHITELIST")
        try:
            os.environ["IP_WHITELIST"] = "192.168.1.0/24,10.0.0.0/8"
            manager = IPWhitelistManager()
            assert len(manager.whitelist) == 2
            assert IPv4Network("192.168.1.0/24") in manager.whitelist
            assert IPv4Network("10.0.0.0/8") in manager.whitelist
        finally:
            # Restore original value
            if original_value is None:
                os.environ.pop("IP_WHITELIST", None)
            else:
                os.environ["IP_WHITELIST"] = original_value


class TestValidateRange:
    """Test IP range validation"""

    def test_valid_cidr(self):
        """Test validating valid CIDR ranges"""
        manager = IPWhitelistManager()
        assert manager.validate_range("192.168.1.0/24") is True
        assert manager.validate_range("10.0.0.0/8") is True
        assert manager.validate_range("172.16.0.0/12") is True
        assert manager.validate_range("8.8.8.8/32") is True

    def test_invalid_cidr_format(self):
        """Test rejecting invalid CIDR format"""
        manager = IPWhitelistManager()
        assert manager.validate_range("invalid") is False
        assert manager.validate_range("256.256.256.256/24") is False
        assert manager.validate_range("192.168.1.0/33") is False

    def test_blocked_dangerous_ranges(self):
        """Test blocking dangerous 0.0.0.0/0 range"""
        manager = IPWhitelistManager()
        # 0.0.0.0/0 matches everything and should be blocked
        assert manager.validate_range("0.0.0.0/0") is False

    def test_blocked_range_overlaps(self):
        """Test blocking only exact 0.0.0.0/0 range (not all overlapping ranges)"""
        manager = IPWhitelistManager()
        # Only 0.0.0.0/0 itself should be blocked
        assert manager.validate_range("0.0.0.0/0") is False
        # Smaller ranges that overlap with 0.0.0.0/0 are allowed
        # (since 0.0.0.0/0 matches everything, we can't block all overlaps)
        assert manager.validate_range("0.0.0.0/1") is True
        assert manager.validate_range("128.0.0.0/1") is True

    @patch("src.core.ip_whitelist.get_environment")
    def test_private_ranges_in_production(self, mock_get_env):
        """Test rejecting private ranges in production"""
        from src.core.environment import Environment

        mock_get_env.return_value = Environment.PRODUCTION

        manager = IPWhitelistManager()

        # Private ranges should be rejected in production
        assert manager.validate_range("10.0.0.0/8") is False
        assert manager.validate_range("172.16.0.0/12") is False
        assert manager.validate_range("192.168.0.0/16") is False

    @patch("src.core.ip_whitelist.get_environment")
    def test_private_ranges_allowed_in_development(self, mock_get_env):
        """Test allowing private ranges in development"""
        from src.core.environment import Environment

        mock_get_env.return_value = Environment.DEVELOPMENT

        manager = IPWhitelistManager()

        # Private ranges should be allowed in development
        assert manager.validate_range("10.0.0.0/8") is True
        assert manager.validate_range("172.16.0.0/12") is True
        assert manager.validate_range("192.168.0.0/16") is True

    def test_public_ranges_always_allowed(self):
        """Test that public IP ranges are always allowed"""
        manager = IPWhitelistManager()
        assert manager.validate_range("8.8.8.8/32") is True  # Google DNS
        assert manager.validate_range("1.1.1.1/32") is True  # Cloudflare DNS
        assert manager.validate_range("9.9.9.0/24") is True  # Quad9


class TestAddRange:
    """Test adding ranges to whitelist"""

    def test_add_valid_range(self):
        """Test adding valid range to whitelist"""
        manager = IPWhitelistManager()
        result = manager.add_range("192.168.1.0/24", added_by="admin")
        assert result is True
        assert IPv4Network("192.168.1.0/24") in manager.whitelist

    def test_add_invalid_range(self):
        """Test that invalid range cannot be added"""
        manager = IPWhitelistManager()
        result = manager.add_range("0.0.0.0/0", added_by="admin")
        assert result is False
        assert len(manager.whitelist) == 0

    def test_add_duplicate_range(self):
        """Test adding duplicate range doesn't create duplicates"""
        manager = IPWhitelistManager()
        manager.add_range("192.168.1.0/24")
        manager.add_range("192.168.1.0/24")
        assert len(manager.whitelist) == 1


class TestRemoveRange:
    """Test removing ranges from whitelist"""

    def test_remove_existing_range(self):
        """Test removing existing range"""
        manager = IPWhitelistManager()
        manager.add_range("192.168.1.0/24")
        result = manager.remove_range("192.168.1.0/24")
        assert result is True
        assert len(manager.whitelist) == 0

    def test_remove_nonexistent_range(self):
        """Test removing range that doesn't exist"""
        manager = IPWhitelistManager()
        result = manager.remove_range("192.168.1.0/24")
        assert result is False

    def test_remove_invalid_range(self):
        """Test removing invalid range returns False"""
        manager = IPWhitelistManager()
        result = manager.remove_range("invalid")
        assert result is False


class TestIsAllowed:
    """Test IP address checking"""

    def test_allow_when_whitelist_empty_in_development(self):
        """Test that empty whitelist allows all in development"""
        manager = IPWhitelistManager()
        with patch.object(manager, "env") as mock_env:
            mock_env.environment = "development"
            assert manager.is_allowed("192.168.1.100") is True
            assert manager.is_allowed("8.8.8.8") is True

    def test_deny_when_whitelist_empty_in_production(self):
        """Test that empty whitelist denies all in production"""
        from src.core.environment import Environment

        manager = IPWhitelistManager()
        manager.env = Environment.PRODUCTION
        assert manager.is_allowed("192.168.1.100") is False
        assert manager.is_allowed("8.8.8.8") is False

    def test_allow_ip_in_whitelist(self):
        """Test allowing IP that matches whitelist entry"""
        manager = IPWhitelistManager()
        manager.add_range("192.168.1.0/24")
        assert manager.is_allowed("192.168.1.100") is True
        assert manager.is_allowed("192.168.1.1") is True

    def test_deny_ip_not_in_whitelist(self):
        """Test denying IP that doesn't match whitelist"""
        manager = IPWhitelistManager()
        manager.add_range("192.168.1.0/24")
        assert manager.is_allowed("192.168.2.100") is False
        assert manager.is_allowed("10.0.0.1") is False

    def test_deny_invalid_ip_format(self):
        """Test denying invalid IP address format"""
        manager = IPWhitelistManager()
        assert manager.is_allowed("invalid") is False
        assert manager.is_allowed("999.999.999.999") is False

    def test_allow_exact_ip_match(self):
        """Test allowing exact IP match with /32"""
        manager = IPWhitelistManager()
        manager.add_range("8.8.8.8/32")
        assert manager.is_allowed("8.8.8.8") is True
        assert manager.is_allowed("8.8.8.9") is False


class TestGetRanges:
    """Test getting whitelist ranges"""

    def test_get_empty_ranges(self):
        """Test getting ranges when whitelist is empty"""
        manager = IPWhitelistManager()
        ranges = manager.get_ranges()
        assert ranges == []
        assert isinstance(ranges, list)

    def test_get_multiple_ranges(self):
        """Test getting multiple ranges as CIDR strings"""
        manager = IPWhitelistManager()
        manager.add_range("192.168.1.0/24")
        manager.add_range("10.0.0.0/8")
        ranges = manager.get_ranges()
        assert len(ranges) == 2
        assert "192.168.1.0/24" in ranges
        assert "10.0.0.0/8" in ranges


class TestClear:
    """Test clearing whitelist"""

    def test_clear_whitelist(self):
        """Test clearing all whitelist entries"""
        manager = IPWhitelistManager()
        manager.add_range("192.168.1.0/24")
        manager.add_range("10.0.0.0/8")
        manager.clear()
        assert len(manager.whitelist) == 0


class TestSingletonInstance:
    """Test the singleton ip_whitelist instance"""

    def test_singleton_instance_exists(self):
        """Test that singleton instance is available"""
        assert ip_whitelist is not None
        assert isinstance(ip_whitelist, IPWhitelistManager)

    def test_singleton_is_shared(self):
        """Test that singleton is the same instance"""
        from src.core.ip_whitelist import ip_whitelist as ip_whitelist_2

        assert ip_whitelist is ip_whitelist_2


class TestEnvironmentBehavior:
    """Test environment-specific IP whitelist behavior"""

    @patch("src.core.ip_whitelist.get_environment")
    def test_production_mode_blocks_private_ranges(self, mock_get_env):
        """Test production mode blocks private range additions"""
        from src.core.environment import Environment

        mock_get_env.return_value = Environment.PRODUCTION

        manager = IPWhitelistManager()

        # Should not be able to add private ranges in production
        assert manager.add_range("10.0.0.0/8") is False
        assert manager.add_range("172.16.0.0/12") is False
        assert manager.add_range("192.168.0.0/16") is False

    @patch("src.core.ip_whitelist.get_environment")
    def test_development_mode_allows_private_ranges(self, mock_get_env):
        """Test development mode allows private range additions"""
        from src.core.environment import Environment

        mock_get_env.return_value = Environment.DEVELOPMENT

        manager = IPWhitelistManager()

        # Should be able to add private ranges in development
        assert manager.add_range("10.0.0.0/8") is True
        assert manager.add_range("172.16.0.0/12") is True
        assert manager.add_range("192.168.0.0/16") is True


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_single_ip_range(self):
        """Test /32 single IP range"""
        manager = IPWhitelistManager()
        assert manager.validate_range("192.168.1.1/32") is True
        manager.add_range("192.168.1.1/32")
        assert manager.is_allowed("192.168.1.1") is True
        assert manager.is_allowed("192.168.1.2") is False

    def test_large_network_range(self):
        """Test large network range"""
        manager = IPWhitelistManager()
        assert manager.validate_range("10.0.0.0/8") is True

    def test_whitelist_with_mixed_ranges(self):
        """Test whitelist with mixed range sizes"""
        manager = IPWhitelistManager()
        manager.add_range("192.168.1.0/24")
        manager.add_range("10.0.0.1/32")
        manager.add_range("172.16.0.0/16")

        assert manager.is_allowed("192.168.1.100") is True
        assert manager.is_allowed("10.0.0.1") is True
        assert manager.is_allowed("172.16.5.5") is True
        assert manager.is_allowed("10.0.0.2") is False

    def test_ip_format_variations(self):
        """Test that IP address format is normalized"""
        manager = IPWhitelistManager()
        # Standard formats work
        assert manager.validate_range("192.168.1.0/24") is True
        # Leading zeros in octets aren't supported by Python's ipaddress module
        # (this is correct behavior - they're non-standard)
        assert manager.validate_range("192.168.001.000/024") is False
