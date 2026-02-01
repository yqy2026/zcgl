"""
Security analyzer tests.
"""

from src.security.security_analyzer import SecurityAnalyzer


class TestSecurityAnalyzerConfig:
    """安全分析器配置测试"""

    def test_blocks_after_threshold(self):
        """达到阈值后应封禁IP"""
        analyzer = SecurityAnalyzer(
            {
                "max_suspicious_requests": 2,
                "enable_ip_block": True,
            }
        )
        ip = "203.0.113.10"

        analyzer.report_suspicious_activity(ip)
        assert ip not in analyzer.blocked_ips

        analyzer.report_suspicious_activity(ip)
        assert ip in analyzer.blocked_ips

    def test_disable_ip_block(self):
        """禁用IP封禁时不应加入封禁列表"""
        analyzer = SecurityAnalyzer(
            {
                "max_suspicious_requests": 1,
                "enable_ip_block": False,
            }
        )
        ip = "203.0.113.11"

        analyzer.report_suspicious_activity(ip)
        assert ip not in analyzer.blocked_ips
