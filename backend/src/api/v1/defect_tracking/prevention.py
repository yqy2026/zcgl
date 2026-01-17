"""
缺陷预防措施模块
"""

import json
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Query

from ....core.api_errors import internal_error

from .database import get_db_connection, row_to_prevention
from .models import DefectCategory, DefectPrevention, DefectPriority

router = APIRouter()


@router.post("/prevention", response_model=DefectPrevention)
async def create_prevention_measure(prevention: DefectPrevention) -> DefectPrevention:
    """
    创建缺陷预防措施
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        prevention_id = (
            f"PREV-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
        )

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

        cursor.execute(
            "SELECT * FROM defect_prevention WHERE prevention_id = ?", (prevention_id,)
        )
        row = cursor.fetchone()

        conn.commit()
        return row_to_prevention(row)

    except Exception as e:
        conn.rollback()
        raise internal_error(f"创建预防措施失败: {str(e)}")
    finally:
        conn.close()


@router.get("/prevention", response_model=list[DefectPrevention])
async def get_prevention_measures(
    category: DefectCategory | None = Query(None, description="分类过滤"),
    priority: DefectPriority | None = Query(None, description="优先级过滤"),
) -> list[DefectPrevention]:
    """
    获取预防措施列表
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM defect_prevention WHERE 1=1"
    params: list[Any] = []

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
    return [row_to_prevention(row) for row in rows]
