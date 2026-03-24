"""Unit tests for analytics export payload mapping."""

from src.services.analytics.analytics_export_service import AnalyticsExportService


def _sample_analytics_data() -> dict[str, object]:
    return {
        "total_assets": 10,
        "area_summary": {
            "total_area": 5000.0,
            "total_rentable_area": 4000.0,
            "occupancy_rate": 80.0,
        },
        "financial_summary": {
            "total_annual_income": 200000.0,
            "total_annual_expense": 50000.0,
            "total_net_income": 150000.0,
            "total_monthly_rent": 16000.0,
        },
        "total_income": 180000.0,
        "self_operated_rent_income": 120000.0,
        "agency_service_income": 60000.0,
        "customer_entity_count": 15,
        "customer_contract_count": 22,
        "metrics_version": "req-ana-001-v1",
    }


def test_build_summary_rows_should_include_req_ana_001_metrics_in_fixed_order() -> None:
    service = AnalyticsExportService()

    rows = service.build_summary_rows(_sample_analytics_data())

    metrics = [row["metric"] for row in rows]
    assert metrics.count("总收入（经营口径）") == 1
    assert metrics.count("自营租金收入") == 1
    assert metrics.count("代理服务费收入") == 1
    assert metrics.count("客户主体数") == 1
    assert metrics.count("客户合同数") == 1
    assert metrics[-1] == "口径版本"
    assert rows[-1]["value"] == "req-ana-001-v1"


def test_build_summary_rows_should_fall_back_to_blank_metrics_version() -> None:
    service = AnalyticsExportService()

    analytics_data = _sample_analytics_data()
    analytics_data["metrics_version"] = None

    rows = service.build_summary_rows(analytics_data)

    assert rows[-1]["metric"] == "口径版本"
    assert rows[-1]["value"] == ""


def test_render_csv_should_emit_tabular_text_instead_of_json() -> None:
    service = AnalyticsExportService()

    csv_text = service.render_csv(service.build_summary_rows(_sample_analytics_data()))

    assert "指标,数值,单位" in csv_text
    assert "总收入（经营口径）,180000.00,元" in csv_text
    assert "口径版本,req-ana-001-v1," in csv_text
    assert '"total_income"' not in csv_text
