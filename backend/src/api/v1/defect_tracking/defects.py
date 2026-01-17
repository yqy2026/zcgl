"""
缺陷报告CRUD操作模块
"""

import json
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Query

from ....core.api_errors import bad_request, internal_error, not_found

from .database import (
    add_defect_history,
    get_db_connection,
    row_to_defect_report,
)
from .models import (
    DefectCategory,
    DefectReport,
    DefectSeverity,
    DefectStatus,
)

router = APIRouter()


@router.post("/", response_model=DefectReport)
async def create_defect(defect: DefectReport) -> DefectReport:
    """
    创建新的缺陷报告
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        defect_id = (
            f"DEF-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
        )

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

        await add_defect_history(
            cursor=cursor,
            defect_id=defect_id,
            action="created",
            old_value=None,
            new_value=defect.title,
            changed_by=defect.reporter,
            comment="缺陷报告创建",
        )

        cursor.execute("SELECT * FROM defect_reports WHERE defect_id = ?", (defect_id,))
        row = cursor.fetchone()

        conn.commit()
        return row_to_defect_report(row)

    except Exception as e:
        conn.rollback()
        raise internal_error(f"创建缺陷失败: {str(e)}")
    finally:
        conn.close()


@router.get("", response_model=dict[str, Any])
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
) -> dict[str, Any]:
    """
    获取缺陷列表
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM defect_reports WHERE 1=1"
    params: list[Any] = []

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
    if sort_by in ["created_at", "updated_at", "severity", "priority"] and sort_order.upper() in ["ASC", "DESC"]:
        if sort_by == "created_at":
            query += f" ORDER BY created_at {sort_order.upper()}"
        elif sort_by == "updated_at":
            query += f" ORDER BY updated_at {sort_order.upper()}"
        elif sort_by == "severity":
            query += f" ORDER BY severity {sort_order.upper()}"
        elif sort_by == "priority":
            query += f" ORDER BY priority {sort_order.upper()}"
    else:
        query += " ORDER BY created_at DESC"

    query += " LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cursor.execute(query, params)
    rows = cursor.fetchall()

    # 获取总数
    count_query = "SELECT COUNT(*) as total FROM defect_reports WHERE 1=1"
    count_params: list[Any] = []

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

    defects = [row_to_defect_report(row) for row in rows]

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
async def get_defect(defect_id: str) -> DefectReport:
    """
    获取缺陷详情
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM defect_reports WHERE defect_id = ?", (defect_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        raise not_found("未找到指定的缺陷", resource_type="defect", resource_id=defect_id)

    conn.close()
    return row_to_defect_report(row)


@router.put("/{defect_id}", response_model=DefectReport)
async def update_defect(defect_id: str, updates: dict[str, Any]) -> DefectReport:
    """
    更新缺陷报告
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM defect_reports WHERE defect_id = ?", (defect_id,))
        current_defect = cursor.fetchone()

        if not current_defect:
            conn.close()
            raise not_found("未找到指定的缺陷", resource_type="defect", resource_id=defect_id)

        allowed_fields = {
            "title", "description", "severity", "priority", "status",
            "category", "module", "assigned_to", "environment",
            "root_cause", "resolution", "fix_version", "updated_at",
        }

        update_fields = []
        update_params = []
        history_changes = []

        for field, value in updates.items():
            if field in allowed_fields and field != "updated_at":
                update_fields.append(f"{field} = ?")
                update_params.append(value)

                current_value = current_defect[field]
                if current_value != value:
                    history_changes.append(
                        {"field": field, "old_value": current_value, "new_value": value}
                    )

        if not update_fields:
            conn.close()
            raise bad_request("没有有效的更新字段")

        update_fields.append("updated_at = ?")
        update_params.append(datetime.now())
        update_params.append(defect_id)

        update_query = f"UPDATE defect_reports SET {', '.join(update_fields)} WHERE defect_id = ?"
        cursor.execute(update_query, update_params)

        for change in history_changes:
            await add_defect_history(
                cursor=cursor,
                defect_id=defect_id,
                action=f"updated_{change['field']}",
                old_value=str(change["old_value"]),
                new_value=str(change["new_value"]),
                changed_by=updates.get("updated_by", "system"),
                comment=f"更新了 {change['field']} 字段",
            )

        if (
            updates.get("status") == DefectStatus.RESOLVED
            and current_defect["status"] != DefectStatus.RESOLVED
        ):
            cursor.execute(
                "UPDATE defect_reports SET resolved_at = ? WHERE defect_id = ?",
                (datetime.now(), defect_id),
            )

        cursor.execute("SELECT * FROM defect_reports WHERE defect_id = ?", (defect_id,))
        row = cursor.fetchone()

        conn.commit()
        return row_to_defect_report(row)

    except Exception as e:
        conn.rollback()
        raise internal_error(f"更新缺陷失败: {str(e)}")
    finally:
        conn.close()


@router.get("/{defect_id}/history")
async def get_defect_history(defect_id: str) -> list[dict[str, Any]]:
    """
    获取缺陷历史记录
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
