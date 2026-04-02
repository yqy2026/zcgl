"""审批域 Pydantic 模型。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ApprovalProcessStartRequest(BaseModel):
    business_type: str = Field(..., min_length=1)
    business_id: str = Field(..., min_length=1)
    assignee_user_id: str = Field(..., min_length=1)
    comment: str | None = None


class ApprovalTaskActionRequest(BaseModel):
    comment: str | None = None


class ApprovalInstanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    approval_no: str
    business_type: str
    business_id: str
    status: str
    starter_id: str
    assignee_user_id: str
    current_task_id: str | None
    started_at: datetime
    ended_at: datetime | None


class ApprovalTaskSnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    approval_instance_id: str
    business_type: str
    business_id: str
    task_name: str
    assignee_user_id: str
    status: str
    created_at: datetime
    completed_at: datetime | None


class ApprovalActionLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    approval_instance_id: str
    approval_task_snapshot_id: str | None
    action: str
    operator_id: str
    comment: str | None
    context: dict[str, Any] | None
    created_at: datetime
