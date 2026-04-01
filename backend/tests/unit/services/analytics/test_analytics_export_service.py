"""
测试 AnalyticsExportService (分析导出映射服务)
"""

from src.services.analytics.analytics_export_service import AnalyticsExportService


class TestAnalyticsExportService:
    """测试分析导出映射服务"""

    def test_build_summary_rows_should_include_req_ana_001_metrics_in_fixed_order(self):
        service = AnalyticsExportService()

        rows = service.build_summary_rows(
            {
                "total_assets": 1,
                "area_summary": {"total_area": 100.0, "total_rentable_area": 80.0},
                "occupancy_rate": {"overall_rate": 50.0},
                "financial_summary": {"total_annual_income": 1000.0},
                "total_income": 1200.0,
                "self_operated_rent_income": 1000.0,
                "agency_service_income": 200.0,
                "customer_entity_count": 2,
                "customer_contract_count": 3,
                "metrics_version": "req-ana-001-v1",
            }
        )

        metrics = [row["metric"] for row in rows]
        assert metrics[-6:] == [
            "总收入（经营口径）",
            "自营租金收入",
            "代理服务费收入",
            "客户主体数",
            "客户合同数",
            "口径版本",
        ]
        assert rows[-1]["value"] == "req-ana-001-v1"
        assert rows[-1]["unit"] == ""

    def test_render_csv_should_return_tabular_text_with_header_and_blank_version(self):
        service = AnalyticsExportService()
        rows = service.build_summary_rows(
            {
                "total_assets": 1,
                "area_summary": {"total_area": 100.0, "total_rentable_area": 80.0},
                "financial_summary": {"total_annual_income": 1000.0},
                "total_income": 1200.0,
                "self_operated_rent_income": 1000.0,
                "agency_service_income": 200.0,
                "customer_entity_count": 2,
                "customer_contract_count": 3,
            }
        )

        content = service.render_csv(rows)
        lines = content.strip().splitlines()

        assert lines[0] == "分组,指标,数值,单位"
        assert "总览,总收入（经营口径）,1200.00,元" in lines
        assert "总览,口径版本,," in lines
        assert '"total_income"' not in content

    def test_build_customer_breakdown_rows_should_include_contract_type_split(self):
        service = AnalyticsExportService()

        rows = service.build_customer_breakdown_rows(
            {
                "customer_entity_breakdown": {
                    "upstream_lease": 1,
                    "downstream_sublease": 2,
                    "entrusted_operation": 3,
                },
                "customer_contract_breakdown": {
                    "upstream_lease": 2,
                    "downstream_sublease": 4,
                    "entrusted_operation": 6,
                },
            }
        )

        assert rows == [
            {
                "section": "客户统计拆分",
                "metric": "上游承租",
                "value": "主体 1 / 合同 2",
                "unit": "",
            },
            {
                "section": "客户统计拆分",
                "metric": "下游转租",
                "value": "主体 2 / 合同 4",
                "unit": "",
            },
            {
                "section": "客户统计拆分",
                "metric": "委托运营",
                "value": "主体 3 / 合同 6",
                "unit": "",
            },
        ]
