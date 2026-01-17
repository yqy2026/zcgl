"""
缺陷趋势和分析模块
"""

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Query

from .database import (
    generate_defect_recommendations,
    get_db_connection,
    get_module_severity,
)
from .models import DefectAnalysis, DefectTrend

router = APIRouter()


@router.get("/trends", response_model=list[DefectTrend])
async def get_defect_trends(
    days: int = Query(default=30, ge=1, le=365, description="查询天数"),
    group_by: str = Query(default="day", description="分组方式: day, week, month"),
) -> list[DefectTrend]:
    """
    获取缺陷趋势数据
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    start_date = datetime.now() - timedelta(days=days)

    if group_by == "week":
        date_format = "%Y-%W"
        date_select = "strftime('%Y-%W', created_at) as period"
    elif group_by == "month":
        date_format = "%Y-%m"
        date_select = "strftime('%Y-%m', created_at) as period"
    else:
        date_format = "%Y-%m-%d"
        date_select = "date(created_at) as period"

    sql_query = f"""
        SELECT
            {date_select},
            COUNT(*) as open_count,
            SUM(CASE WHEN status = 'resolved' THEN 1 ELSE 0 END) as resolved_count,
            SUM(CASE WHEN status = 'reopened' THEN 1 ELSE 0 END) as reopened_count
        FROM defect_reports
        WHERE created_at >= ?
        GROUP BY period
        ORDER BY period
    """
    cursor.execute(sql_query, (start_date,))

    rows = cursor.fetchall()

    trends = []
    for row in rows:
        cursor.execute(
            """
            SELECT COUNT(*) as active_count
            FROM defect_reports
            WHERE status IN ('open', 'in_progress', 'reopened')
            AND created_at <= ?
        """,
            (row["period"] + " 23:59:59",),
        )

        active_count = cursor.fetchone()["active_count"]

        trends.append(
            DefectTrend(
                date=datetime.strptime(row["period"], date_format),
                open_count=row["open_count"],
                resolved_count=row["resolved_count"],
                reopened_count=row["reopened_count"],
                total_active=active_count,
            )
        )

    conn.close()
    return trends


@router.get("/analysis", response_model=DefectAnalysis)
async def get_defect_analysis(
    days: int = Query(default=30, ge=1, le=365, description="分析天数"),
) -> DefectAnalysis:
    """
    获取缺陷分析报告
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    start_date = datetime.now() - timedelta(days=days)

    cursor.execute(
        """
        SELECT
            COUNT(*) as total_defects,
            COUNT(CASE WHEN created_at >= ? THEN 1 END) as new_defects,
            COUNT(CASE WHEN status = 'resolved' AND resolved_at >= ? THEN 1 END) as resolved_defects,
            AVG(CASE WHEN status = 'resolved' AND resolved_at >= ?
                THEN (julianday(resolved_at) - julianday(created_at)) * 24 END) as avg_resolution_time
        FROM defect_reports
        WHERE created_at >= ? OR status = 'resolved'
    """,
        (start_date, start_date, start_date, start_date),
    )

    stats = cursor.fetchone()

    cursor.execute(
        """
        SELECT severity, COUNT(*) as count
        FROM defect_reports
        WHERE created_at >= ?
        GROUP BY severity
    """,
        (start_date,),
    )
    severity_distribution = {row["severity"]: row["count"] for row in cursor.fetchall()}

    cursor.execute(
        """
        SELECT category, COUNT(*) as count
        FROM defect_reports
        WHERE created_at >= ?
        GROUP BY category
    """,
        (start_date,),
    )
    category_distribution = {row["category"]: row["count"] for row in cursor.fetchall()}

    cursor.execute(
        """
        SELECT module, COUNT(*) as count
        FROM defect_reports
        WHERE created_at >= ?
        GROUP BY module
        ORDER BY count DESC
    """,
        (start_date,),
    )
    module_distribution = {row["module"]: row["count"] for row in cursor.fetchall()}

    total_new = stats["new_defects"]
    total_resolved = stats["resolved_defects"]
    resolution_rate = (total_resolved / total_new * 100) if total_new > 0 else 0

    cursor.execute(
        """
        SELECT COUNT(*) as reopened_count
        FROM defect_reports
        WHERE status = 'reopened' AND created_at >= ?
    """,
        (start_date,),
    )
    reopened_count = cursor.fetchone()["reopened_count"]
    reopen_rate = (reopened_count / total_resolved * 100) if total_resolved > 0 else 0

    hotspots = []
    for module, count in module_distribution.items():
        if count > 5:
            hotspots.append(
                {
                    "module": module,
                    "defect_count": count,
                    "severity": get_module_severity(conn, module, start_date),
                }
            )

    recommendations = generate_defect_recommendations(
        severity_distribution, category_distribution, module_distribution
    )

    conn.close()

    return DefectAnalysis(
        period_start=start_date,
        period_end=datetime.now(),
        total_defects=stats["total_defects"] or 0,
        new_defects=stats["new_defects"] or 0,
        resolved_defects=stats["resolved_defects"] or 0,
        average_resolution_time=stats["avg_resolution_time"] or 0,
        severity_distribution=severity_distribution,
        category_distribution=category_distribution,
        module_distribution=module_distribution,
        resolution_rate=resolution_rate,
        reopen_rate=reopen_rate,
        hotspots=hotspots,
        recommendations=recommendations,
    )
