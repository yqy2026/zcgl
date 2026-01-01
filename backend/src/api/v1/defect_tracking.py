from typing import Any

"""
缺陷跟踪和分析API模块
提供缺陷报告、分析、趋势跟踪和预防建议功能
"""

import json
import os
import sqlite3
import uuid
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/defects", tags=["defect-tracking"])


class DefectSeverity(str, Enum):
    """缺陷严重程度"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DefectPriority(str, Enum):
    """缺陷优先级"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class DefectStatus(str, Enum):
    """缺陷状态"""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"
    REOPENED = "reopened"


class DefectCategory(str, Enum):
    """缺陷分类"""

    FUNCTIONAL = "functional"
    PERFORMANCE = "performance"
    SECURITY = "security"
    USABILITY = "usability"
    COMPATIBILITY = "compatibility"
    INTEGRATION = "integration"
    CONFIGURATION = "configuration"


class DefectReport(BaseModel):
    """缺陷报告模型"""

    defect_id: str | None = Field(None, description="缺陷ID")
    title: str = Field(..., description="缺陷标题")
    description: str = Field(..., description="缺陷描述")
    severity: DefectSeverity = Field(..., description="严重程度")
    priority: DefectPriority = Field(..., description="优先级")
    status: DefectStatus = Field(default=DefectStatus.OPEN, description="状态")
    category: DefectCategory = Field(..., description="分类")
    module: str = Field(..., description="所属模块")
    reproduction_steps: list[str] = Field(..., description="重现步骤")
    expected_behavior: str = Field(..., description="预期行为")
    actual_behavior: str = Field(..., description="实际行为")
    reporter: str = Field(..., description="报告人")
    assigned_to: str | None = Field(None, description="指派给")
    environment: str | None = Field(None, description="环境信息")
    attachments: list[str] | None = Field(default=[], description="附件")
    tags: list[str] | None = Field(default=[], description="标签")
    test_coverage_impact: dict[str, Any] | None = Field(
        None, description="测试覆盖率影响"
    )
    created_at: datetime | None = Field(None, description="创建时间")
    updated_at: datetime | None = Field(None, description="更新时间")
    resolved_at: datetime | None = Field(None, description="解决时间")
    fix_version: str | None = Field(None, description="修复版本")
    root_cause: str | None = Field(None, description="根本原因")
    resolution: str | None = Field(None, description="解决方案")


class DefectTrend(BaseModel):
    """缺陷趋势数据"""

    date: datetime = Field(..., description="日期")
    open_count: int = Field(..., description="新增缺陷数")
    resolved_count: int = Field(..., description="解决缺陷数")
    reopened_count: int = Field(..., description="重新打开数")
    total_active: int = Field(..., description="活跃缺陷总数")


class DefectAnalysis(BaseModel):
    """缺陷分析报告"""

    period_start: datetime = Field(..., description="分析开始时间")
    period_end: datetime = Field(..., description="分析结束时间")
    total_defects: int = Field(..., description="总缺陷数")
    new_defects: int = Field(..., description="新增缺陷数")
    resolved_defects: int = Field(..., description="解决缺陷数")
    average_resolution_time: float = Field(..., description="平均解决时间(小时)")
    severity_distribution: dict[str, int] = Field(..., description="严重程度分布")
    category_distribution: dict[str, int] = Field(..., description="分类分布")
    module_distribution: dict[str, int] = Field(..., description="模块分布")
    resolution_rate: float = Field(..., description="解决率")
    reopen_rate: float = Field(..., description="重新打开率")
    hotspots: list[dict[str, Any]] = Field(..., description="热点区域")
    recommendations: list[str] = Field(..., description="改进建议")


class DefectPrevention(BaseModel):
    """缺陷预防建议"""

    prevention_id: str = Field(..., description="预防ID")
    category: DefectCategory = Field(..., description="适用分类")
    title: str = Field(..., description="预防措施标题")
    description: str = Field(..., description="详细描述")
    implementation_steps: list[str] = Field(..., description="实施步骤")
    estimated_impact: str = Field(..., description="预期影响")
    priority: DefectPriority = Field(..., description="优先级")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")


# 数据库连接
def get_db_connection():
    """获取数据库连接"""
    db_path = Path(__file__).parent.parent.parent / "data" / "defect_tracking.db"
    os.makedirs(db_path.parent, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_defect_db():
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


# 初始化数据库
init_defect_db()


@router.post("/", response_model=DefectReport)
async def create_defect(defect: DefectReport):
    """
    创建新的缺陷报告

    Args:
        defect: 缺陷报告数据

    Returns:
        DefectReport: 创建的缺陷报告
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 生成缺陷ID
        defect_id = (
            f"DEF-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
        )

        # 插入缺陷报告
        cursor.execute(
            """
            INSERT INTO defect_reports
            (defect_id, title, description, severity, priority, status, category, module,
             reproduction_steps, expected_behavior, actual_behavior, reporter, assigned_to,
             environment, attachments, tags, test_coverage_impact)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                defect_id,
                defect.title,
                defect.description,
                defect.severity,
                defect.priority,
                defect.status,
                defect.category,
                defect.module,
                json.dumps(defect.reproduction_steps),
                defect.expected_behavior,
                defect.actual_behavior,
                defect.reporter,
                defect.assigned_to,
                defect.environment,
                json.dumps(defect.attachments or []),
                json.dumps(defect.tags or []),
                json.dumps(defect.test_coverage_impact)
                if defect.test_coverage_impact
                else None,
            ),
        )

        # 记录创建历史
        await _add_defect_history(
            cursor=cursor,
            defect_id=defect_id,
            action="created",
            new_value=defect.title,
            changed_by=defect.reporter,
            comment="缺陷报告创建",
        )

        # 获取创建的缺陷
        cursor.execute("SELECT * FROM defect_reports WHERE defect_id = ?", (defect_id,))
        row = cursor.fetchone()

        conn.commit()
        return _row_to_defect_report(row)

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"创建缺陷失败: {str(e)}")
    finally:
        conn.close()


@router.get("/", response_model=dict[str, Any])
async def get_defects(
    status: DefectStatus | None = Query(None, description="状态过滤"),
    severity: DefectSeverity | None = Query(None, description="严重程度过滤"),
    category: DefectCategory | None = Query(None, description="分类过滤"),
    module: str | None = Query(None, description="模块过滤"),
    reporter: str | None = Query(None, description="报告人过滤"),
    assigned_to: str | None = Query(None, description="指派人过滤"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sort_by: str = Query(default="created_at", description="排序字段"),
    sort_order: str = Query(default="desc", description="排序方向"),
):
    """
    获取缺陷列表

    Args:
        status: 状态过滤
        severity: 严重程度过滤
        category: 分类过滤
        module: 模块过滤
        reporter: 报告人过滤
        assigned_to: 指派人过滤
        limit: 返回数量限制
        offset: 偏移量
        sort_by: 排序字段
        sort_order: 排序方向

    Returns:
        Dict: 缺陷列表和分页信息
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # 构建查询
    query = "SELECT * FROM defect_reports WHERE 1=1"
    params = []

    if status:
        query += " AND status = ?"
        params.append(status)

    if severity:
        query += " AND severity = ?"
        params.append(severity)

    if category:
        query += " AND category = ?"
        params.append(category)

    if module:
        query += " AND module = ?"
        params.append(module)

    if reporter:
        query += " AND reporter = ?"
        params.append(reporter)

    if assigned_to:
        query += " AND assigned_to = ?"
        params.append(assigned_to)

    # 排序 - 防止SQL注入
    if sort_by in [
        "created_at",
        "updated_at",
        "severity",
        "priority",
    ] and sort_order.upper() in ["ASC", "DESC"]:
        # 使用参数化排序，防止SQL注入
        if sort_by == "created_at":
            if sort_order.upper() == "ASC":
                query += " ORDER BY created_at ASC"
            else:
                query += " ORDER BY created_at DESC"
        elif sort_by == "updated_at":
            if sort_order.upper() == "ASC":
                query += " ORDER BY updated_at ASC"
            else:
                query += " ORDER BY updated_at DESC"
        elif sort_by == "severity":
            if sort_order.upper() == "ASC":
                query += " ORDER BY severity ASC"
            else:
                query += " ORDER BY severity DESC"
        elif sort_by == "priority":
            if sort_order.upper() == "ASC":
                query += " ORDER BY priority ASC"
            else:
                query += " ORDER BY priority DESC"
    else:
        query += " ORDER BY created_at DESC"

    # 分页
    query += " LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cursor.execute(query, params)
    rows = cursor.fetchall()

    # 获取总数
    count_query = "SELECT COUNT(*) as total FROM defect_reports WHERE 1=1"
    count_params = []

    if status:
        count_query += " AND status = ?"
        count_params.append(status)
    if severity:
        count_query += " AND severity = ?"
        count_params.append(severity)
    if category:
        count_query += " AND category = ?"
        count_params.append(category)
    if module:
        count_query += " AND module = ?"
        count_params.append(module)
    if reporter:
        count_query += " AND reporter = ?"
        count_params.append(reporter)
    if assigned_to:
        count_query += " AND assigned_to = ?"
        count_params.append(assigned_to)

    cursor.execute(count_query, count_params)
    total = cursor.fetchone()["total"]

    conn.close()

    defects = [_row_to_defect_report(row) for row in rows]

    return {
        "defects": defects,
        "total": total,
        "limit": limit,
        "offset": offset,
        "filters": {
            "status": status,
            "severity": severity,
            "category": category,
            "module": module,
            "reporter": reporter,
            "assigned_to": assigned_to,
        },
    }


@router.get("/{defect_id}", response_model=DefectReport)
async def get_defect(defect_id: str):
    """
    获取缺陷详情

    Args:
        defect_id: 缺陷ID

    Returns:
        DefectReport: 缺陷详情
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM defect_reports WHERE defect_id = ?", (defect_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="未找到指定的缺陷")

    conn.close()
    return _row_to_defect_report(row)


@router.put("/{defect_id}", response_model=DefectReport)
async def update_defect(defect_id: str, updates: dict[str, Any]):
    """
    更新缺陷报告

    Args:
        defect_id: 缺陷ID
        updates: 更新数据

    Returns:
        DefectReport: 更新后的缺陷报告
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 获取当前缺陷
        cursor.execute("SELECT * FROM defect_reports WHERE defect_id = ?", (defect_id,))
        current_defect = cursor.fetchone()

        if not current_defect:
            conn.close()
            raise HTTPException(status_code=404, detail="未找到指定的缺陷")

        # 构建更新语句
        update_fields = []
        update_params = []
        history_changes = []

        for field, value in updates.items():
            if field in [
                "title",
                "description",
                "severity",
                "priority",
                "status",
                "category",
                "module",
                "assigned_to",
                "environment",
                "root_cause",
                "resolution",
                "fix_version",
            ]:
                update_fields.append(f"{field} = ?")
                update_params.append(value)

                # 记录历史变更
                current_value = current_defect[field]
                if current_value != value:
                    history_changes.append(
                        {"field": field, "old_value": current_value, "new_value": value}
                    )

        if not update_fields:
            conn.close()
            raise HTTPException(status_code=400, detail="没有有效的更新字段")

        # 添加更新时间
        update_fields.append("updated_at = ?")
        update_params.append(datetime.now())

        # 添加defect_id参数
        update_params.append(defect_id)

        # 执行更新 - 使用安全的参数化查询
        # 字段名已经通过白名单验证，这里构建的查询是安全的
        allowed_fields = {
            "title",
            "description",
            "severity",
            "priority",
            "status",
            "category",
            "module",
            "assigned_to",
            "environment",
            "root_cause",
            "resolution",
            "fix_version",
            "updated_at",
        }

        # 验证所有字段都在允许的列表中
        for field_part in update_fields:
            field_name = field_part.split(" = ")[0]
            if field_name not in allowed_fields:
                conn.close()
                raise HTTPException(
                    status_code=400, detail=f"不允许的字段: {field_name}"
                )

        update_query = (
            f"UPDATE defect_reports SET {', '.join(update_fields)} WHERE defect_id = ?"
        )  # nosec - B608: update_fields validated against allowlist above
        cursor.execute(update_query, update_params)

        # 记录变更历史
        for change in history_changes:
            await _add_defect_history(
                cursor=cursor,
                defect_id=defect_id,
                action=f"updated_{change['field']}",
                old_value=str(change["old_value"]),
                new_value=str(change["new_value"]),
                changed_by=updates.get("updated_by", "system"),
                comment=f"更新了 {change['field']} 字段",
            )

        # 如果状态变更为解决，记录解决时间
        if (
            updates.get("status") == DefectStatus.RESOLVED
            and current_defect["status"] != DefectStatus.RESOLVED
        ):
            cursor.execute(
                "UPDATE defect_reports SET resolved_at = ? WHERE defect_id = ?",
                (datetime.now(), defect_id),
            )

        # 获取更新后的缺陷
        cursor.execute("SELECT * FROM defect_reports WHERE defect_id = ?", (defect_id,))
        row = cursor.fetchone()

        conn.commit()
        return _row_to_defect_report(row)

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"更新缺陷失败: {str(e)}")
    finally:
        conn.close()


@router.get("/{defect_id}/history")
async def get_defect_history(defect_id: str):
    """
    获取缺陷历史记录

    Args:
        defect_id: 缺陷ID

    Returns:
        List[Dict]: 历史记录列表
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT * FROM defect_history
        WHERE defect_id = ?
        ORDER BY changed_at DESC
    """,
        (defect_id,),
    )

    rows = cursor.fetchall()
    conn.close()

    history = []
    for row in rows:
        history.append(
            {
                "action": row["action"],
                "old_value": row["old_value"],
                "new_value": row["new_value"],
                "changed_by": row["changed_by"],
                "changed_at": row["changed_at"],
                "comment": row["comment"],
            }
        )

    return history


@router.get("/trends", response_model=list[DefectTrend])
async def get_defect_trends(
    days: int = Query(default=30, ge=1, le=365, description="查询天数"),
    group_by: str = Query(default="day", description="分组方式: day, week, month"),
):
    """
    获取缺陷趋势数据

    Args:
        days: 查询天数
        group_by: 分组方式

    Returns:
        List[DefectTrend]: 缺陷趋势数据
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    start_date = datetime.now() - timedelta(days=days)

    # 根据分组方式构建SQL
    if group_by == "week":
        date_format = "%Y-%W"
        date_select = "strftime('%Y-%W', created_at) as period"
    elif group_by == "month":
        date_format = "%Y-%m"
        date_select = "strftime('%Y-%m', created_at) as period"
    else:  # day
        date_format = "%Y-%m-%d"
        date_select = "date(created_at) as period"

    # 获取每日趋势数据
    cursor.execute(  # nosec - B608: date_select set from validated group_by values above
        f"""
        SELECT
            {date_select},
            COUNT(*) as open_count,
            SUM(CASE WHEN status = 'resolved' THEN 1 ELSE 0 END) as resolved_count,
            SUM(CASE WHEN status = 'reopened' THEN 1 ELSE 0 END) as reopened_count
        FROM defect_reports
        WHERE created_at >= ?
        GROUP BY period
        ORDER BY period
    """,
        (start_date,),
    )

    rows = cursor.fetchall()

    trends = []
    for row in rows:
        # 计算活跃缺陷总数（简化计算）
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
):
    """
    获取缺陷分析报告

    Args:
        days: 分析天数

    Returns:
        DefectAnalysis: 缺陷分析报告
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    start_date = datetime.now() - timedelta(days=days)

    # 总体统计
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

    # 严重程度分布
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

    # 分类分布
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

    # 模块分布
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

    # 计算解决率和重新打开率
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

    # 识别热点区域（高缺陷模块）
    hotspots = []
    for module, count in module_distribution.items():
        if count > 5:  # 超过5个缺陷的模块
            hotspots.append(
                {
                    "module": module,
                    "defect_count": count,
                    "severity": _get_module_severity(conn, module, start_date),
                }
            )

    # 生成改进建议
    recommendations = _generate_defect_recommendations(
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


@router.post("/prevention", response_model=DefectPrevention)
async def create_prevention_measure(prevention: DefectPrevention):
    """
    创建缺陷预防措施

    Args:
        prevention: 预防措施数据

    Returns:
        DefectPrevention: 创建的预防措施
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 生成预防ID
        prevention_id = (
            f"PREV-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
        )

        # 插入预防措施
        cursor.execute(
            """
            INSERT INTO defect_prevention
            (prevention_id, category, title, description, implementation_steps,
             estimated_impact, priority)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                prevention_id,
                prevention.category,
                prevention.title,
                prevention.description,
                json.dumps(prevention.implementation_steps),
                prevention.estimated_impact,
                prevention.priority,
            ),
        )

        # 获取创建的预防措施
        cursor.execute(
            "SELECT * FROM defect_prevention WHERE prevention_id = ?", (prevention_id,)
        )
        row = cursor.fetchone()

        conn.commit()
        return _row_to_prevention(row)

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"创建预防措施失败: {str(e)}")
    finally:
        conn.close()


@router.get("/prevention", response_model=list[DefectPrevention])
async def get_prevention_measures(
    category: DefectCategory | None = Query(None, description="分类过滤"),
    priority: DefectPriority | None = Query(None, description="优先级过滤"),
):
    """
    获取预防措施列表

    Args:
        category: 分类过滤
        priority: 优先级过滤

    Returns:
        List[DefectPrevention]: 预防措施列表
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM defect_prevention WHERE 1=1"
    params = []

    if category:
        query += " AND category = ?"
        params.append(category)

    if priority:
        query += " AND priority = ?"
        params.append(priority)

    query += " ORDER BY priority DESC, created_at DESC"

    cursor.execute(query, params)
    rows = cursor.fetchall()

    conn.close()
    return [_row_to_prevention(row) for row in rows]


# 辅助函数
def _row_to_defect_report(row) -> DefectReport:
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


def _row_to_prevention(row) -> DefectPrevention:
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


async def _add_defect_history(
    cursor,
    defect_id: str,
    action: str,
    old_value: str | None,
    new_value: str | None,
    changed_by: str,
    comment: str,
):
    """添加缺陷历史记录"""
    cursor.execute(
        """
        INSERT INTO defect_history
        (defect_id, action, old_value, new_value, changed_by, comment)
        VALUES (?, ?, ?, ?, ?, ?)
    """,
        (defect_id, action, old_value, new_value, changed_by, comment),
    )


def _get_module_severity(conn, module: str, start_date: datetime) -> str:
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

    # 根据严重缺陷数量确定严重程度
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


def _generate_defect_recommendations(
    severity_dist: dict[str, int],
    category_dist: dict[str, int],
    module_dist: dict[str, int],
) -> list[str]:
    """生成缺陷改进建议"""
    recommendations = []

    # 基于严重程度的建议
    critical_count = severity_dist.get("critical", 0)
    if critical_count > 0:
        recommendations.append(
            f"发现 {critical_count} 个严重缺陷，需要优先处理并制定预防措施"
        )

    # 基于分类的建议
    functional_count = category_dist.get("functional", 0)
    performance_count = category_dist.get("performance", 0)
    security_count = category_dist.get("security", 0)

    if functional_count > 10:
        recommendations.append("功能缺陷较多，建议加强代码审查和单元测试覆盖率")
    if performance_count > 5:
        recommendations.append("性能问题突出，建议建立性能测试基准和监控")
    if security_count > 2:
        recommendations.append("存在安全问题，建议进行安全审计和漏洞扫描")

    # 基于模块的建议
    high_risk_modules = [
        (module, count) for module, count in module_dist.items() if count > 8
    ]
    if high_risk_modules:
        modules = ", ".join(
            [f"{module}({count})" for module, count in high_risk_modules[:3]]
        )
        recommendations.append(f"模块 {modules} 缺陷较多，建议进行专项重构和测试")

    # 通用建议
    recommendations.extend(
        [
            "定期分析缺陷模式和根本原因",
            "建立缺陷预防机制，在开发阶段避免常见问题",
            "加强测试覆盖率，特别是边界条件和异常情况",
            "改进需求分析和技术设计，减少理解偏差",
        ]
    )

    return recommendations[:8]  # 限制建议数量
