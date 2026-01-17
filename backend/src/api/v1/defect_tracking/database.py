"""
缺陷跟踪数据库初始化和连接
"""

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path

from .models import DefectPrevention, DefectReport


def get_db_connection() -> sqlite3.Connection:
    """获取数据库连接"""
    db_path = Path(__file__).parent.parent.parent.parent / "data" / "defect_tracking.db"
    os.makedirs(db_path.parent, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_defect_db() -> None:
    """初始化缺陷跟踪数据库"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 创建缺陷报告表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS defect_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            defect_id TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            severity TEXT NOT NULL,
            priority TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            category TEXT NOT NULL,
            module TEXT NOT NULL,
            reproduction_steps TEXT NOT NULL,
            expected_behavior TEXT NOT NULL,
            actual_behavior TEXT NOT NULL,
            reporter TEXT NOT NULL,
            assigned_to TEXT,
            environment TEXT,
            attachments TEXT,
            tags TEXT,
            test_coverage_impact TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolved_at TIMESTAMP,
            fix_version TEXT,
            root_cause TEXT,
            resolution TEXT
        )
    """)

    # 创建缺陷历史记录表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS defect_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            defect_id TEXT NOT NULL,
            action TEXT NOT NULL,
            old_value TEXT,
            new_value TEXT,
            changed_by TEXT NOT NULL,
            changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            comment TEXT,
            FOREIGN KEY (defect_id) REFERENCES defect_reports (defect_id)
        )
    """)

    # 创建缺陷预防措施表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS defect_prevention (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prevention_id TEXT UNIQUE NOT NULL,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            implementation_steps TEXT NOT NULL,
            estimated_impact TEXT NOT NULL,
            priority TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 创建索引
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_defect_status ON defect_reports(status)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_defect_severity ON defect_reports(severity)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_defect_module ON defect_reports(module)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_defect_category ON defect_reports(category)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_defect_created_at ON defect_reports(created_at)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_defect_history_defect_id ON defect_history(defect_id)"
    )

    conn.commit()
    conn.close()


def row_to_defect_report(row: sqlite3.Row) -> DefectReport:
    """将数据库行转换为DefectReport对象"""
    return DefectReport(
        defect_id=row["defect_id"],
        title=row["title"],
        description=row["description"],
        severity=row["severity"],
        priority=row["priority"],
        status=row["status"],
        category=row["category"],
        module=row["module"],
        reproduction_steps=json.loads(row["reproduction_steps"]),
        expected_behavior=row["expected_behavior"],
        actual_behavior=row["actual_behavior"],
        reporter=row["reporter"],
        assigned_to=row["assigned_to"],
        environment=row["environment"],
        attachments=json.loads(row["attachments"]) if row["attachments"] else [],
        tags=json.loads(row["tags"]) if row["tags"] else [],
        test_coverage_impact=json.loads(row["test_coverage_impact"])
        if row["test_coverage_impact"]
        else None,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        resolved_at=row["resolved_at"],
        fix_version=row["fix_version"],
        root_cause=row["root_cause"],
        resolution=row["resolution"],
    )


def row_to_prevention(row: sqlite3.Row) -> DefectPrevention:
    """将数据库行转换为DefectPrevention对象"""
    return DefectPrevention(
        prevention_id=row["prevention_id"],
        category=row["category"],
        title=row["title"],
        description=row["description"],
        implementation_steps=json.loads(row["implementation_steps"]),
        estimated_impact=row["estimated_impact"],
        priority=row["priority"],
        created_at=row["created_at"],
    )


async def add_defect_history(
    cursor: sqlite3.Cursor,
    defect_id: str,
    action: str,
    old_value: str | None,
    new_value: str | None,
    changed_by: str,
    comment: str,
) -> None:
    """添加缺陷历史记录"""
    cursor.execute(
        """
        INSERT INTO defect_history
        (defect_id, action, old_value, new_value, changed_by, comment)
        VALUES (?, ?, ?, ?, ?, ?)
    """,
        (defect_id, action, old_value, new_value, changed_by, comment),
    )


def get_module_severity(
    conn: sqlite3.Connection, module: str, start_date: datetime
) -> str:
    """获取模块的缺陷严重程度"""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT severity, COUNT(*) as count
        FROM defect_reports
        WHERE module = ? AND created_at >= ?
        GROUP BY severity
    """,
        (module, start_date),
    )

    severity_counts = {row["severity"]: row["count"] for row in cursor.fetchall()}

    critical_count = severity_counts.get("critical", 0)
    high_count = severity_counts.get("high", 0)

    if critical_count > 0:
        return "critical"
    elif high_count > 2:
        return "high"
    elif high_count > 0:
        return "medium"
    else:
        return "low"


def generate_defect_recommendations(
    severity_dist: dict[str, int],
    category_dist: dict[str, int],
    module_dist: dict[str, int],
) -> list[str]:
    """生成缺陷改进建议"""
    recommendations = []

    critical_count = severity_dist.get("critical", 0)
    if critical_count > 0:
        recommendations.append(
            f"发现 {critical_count} 个严重缺陷，需要优先处理并制定预防措施"
        )

    functional_count = category_dist.get("functional", 0)
    performance_count = category_dist.get("performance", 0)
    security_count = category_dist.get("security", 0)

    if functional_count > 10:
        recommendations.append("功能缺陷较多，建议加强代码审查和单元测试覆盖率")
    if performance_count > 5:
        recommendations.append("性能问题突出，建议建立性能测试基准和监控")
    if security_count > 2:
        recommendations.append("存在安全问题，建议进行安全审计和漏洞扫描")

    high_risk_modules = [
        (module, count) for module, count in module_dist.items() if count > 8
    ]
    if high_risk_modules:
        modules = ", ".join(
            [f"{module}({count})" for module, count in high_risk_modules[:3]]
        )
        recommendations.append(f"模块 {modules} 缺陷较多，建议进行专项重构和测试")

    recommendations.extend(
        [
            "定期分析缺陷模式和根本原因",
            "建立缺陷预防机制，在开发阶段避免常见问题",
            "加强测试覆盖率，特别是边界条件和异常情况",
            "改进需求分析和技术设计，减少理解偏差",
        ]
    )

    return recommendations[:8]
