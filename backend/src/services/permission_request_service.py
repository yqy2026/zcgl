from typing import Any

"""
权限申请和审批工作流服务
支持权限申请、审批、驳回等完整工作流程
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import and_
from sqlalchemy.orm import Session

from ..models.auth import User
from ..models.dynamic_permission import DynamicPermissionAudit, PermissionRequest
from ..models.rbac import Permission
from .dynamic_permission_assignment_service import DynamicPermissionService


class PermissionRequestService:
    """权限申请服务"""

    def __init__(self, db: Session):
        self.db = db
        self.dynamic_permission_service = DynamicPermissionService(db)

    def create_permission_request(
        self,
        user_id: str,
        permission_ids: list[str],
        scope: str,
        scope_id: str | None,
        reason: str,
        requested_duration_hours: int | None = None,
        requested_conditions: dict[str, Any] | None = None,
    ) -> PermissionRequest:
        """创建权限申请"""

        # 验证权限是否存在
        permissions = (
            self.db.query(Permission).filter(Permission.id.in_(permission_ids)).all()
        )

        if len(permissions) != len(permission_ids):
            raise ValueError("部分权限ID不存在")

        # 验证用户是否存在
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"用户不存在: {user_id}")

        # 检查是否已有待审批的相同申请
        existing_request = (
            self.db.query(PermissionRequest)
            .filter(
                and_(
                    PermissionRequest.user_id == user_id,
                    PermissionRequest.permission_ids == permission_ids,
                    PermissionRequest.scope == scope,
                    PermissionRequest.scope_id == scope_id,
                    PermissionRequest.status == "pending",
                )
            )
            .first()
        )

        if existing_request:
            raise ValueError("已有相同的权限申请在待审批中")

        # 创建权限申请
        permission_request = PermissionRequest(
            user_id=user_id,
            permission_ids=permission_ids,
            scope=scope,
            scope_id=scope_id,
            reason=reason,
            requested_duration_hours=str(requested_duration_hours)
            if requested_duration_hours
            else None,
            requested_conditions=requested_conditions,
            status="pending",
        )

        self.db.add(permission_request)
        self.db.commit()
        self.db.refresh(permission_request)

        return permission_request

    def approve_permission_request(
        self,
        request_id: str,
        approved_by: str,
        approval_comment: str | None = None,
        custom_duration_hours: int | None = None,
        custom_conditions: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """审批权限申请"""

        # 获取权限申请
        request = (
            self.db.query(PermissionRequest)
            .filter(PermissionRequest.id == request_id)
            .first()
        )

        if not request:
            raise ValueError(f"权限申请不存在: {request_id}")

        if request.status != "pending":
            raise ValueError(f"权限申请状态不是待审批: {request.status}")

        # 更新申请状态
        request.status = "approved"
        request.approved_by = approved_by
        request.approved_at = datetime.now(UTC)
        request.approval_comment = approval_comment

        # 根据申请类型分配权限
        assigned_permissions = []
        errors = []

        for permission_id in request.permission_ids:
            try:
                # 确定权限类型和参数
                if request.requested_duration_hours:
                    # 临时权限
                    duration_hours = custom_duration_hours or int(
                        request.requested_duration_hours
                    )
                    expires_at = datetime.now(UTC) + timedelta(hours=duration_hours)

                    temp_permission = (
                        self.dynamic_permission_service.create_temporary_permission(
                            user_id=request.user_id,
                            permission_id=permission_id,
                            scope=request.scope,
                            scope_id=request.scope_id,
                            expires_at=expires_at,
                            assigned_by=approved_by,
                            reason=f"权限申请批准: {request.reason}",
                        )
                    )
                    assigned_permissions.append(
                        {
                            "type": "temporary",
                            "permission_id": permission_id,
                            "expires_at": expires_at,
                            "id": temp_permission.id,
                        }
                    )

                elif request.requested_conditions:
                    # 条件权限
                    conditions = custom_conditions or request.requested_conditions

                    conditional_permission = (
                        self.dynamic_permission_service.create_conditional_permission(
                            user_id=request.user_id,
                            permission_id=permission_id,
                            scope=request.scope,
                            scope_id=request.scope_id,
                            conditions=conditions,
                            assigned_by=approved_by,
                            reason=f"权限申请批准: {request.reason}",
                        )
                    )
                    assigned_permissions.append(
                        {
                            "type": "conditional",
                            "permission_id": permission_id,
                            "conditions": conditions,
                            "id": conditional_permission.id,
                        }
                    )

                else:
                    # 普通动态权限
                    dynamic_permission = (
                        self.dynamic_permission_service.create_dynamic_permission(
                            user_id=request.user_id,
                            permission_id=permission_id,
                            scope=request.scope,
                            scope_id=request.scope_id,
                            permission_type="request_based",
                            conditions=None,
                            assigned_by=approved_by,
                            reason=f"权限申请批准: {request.reason}",
                        )
                    )
                    assigned_permissions.append(
                        {
                            "type": "dynamic",
                            "permission_id": permission_id,
                            "id": dynamic_permission.id,
                        }
                    )

            except Exception as e:
                errors.append({"permission_id": permission_id, "error": str(e)})

        self.db.commit()

        return {
            "request_id": request_id,
            "status": "approved",
            "assigned_permissions": assigned_permissions,
            "errors": errors,
            "approved_at": request.approved_at,
        }

    def reject_permission_request(
        self, request_id: str, rejected_by: str, rejection_reason: str
    ) -> PermissionRequest:
        """驳回权限申请"""

        # 获取权限申请
        request = (
            self.db.query(PermissionRequest)
            .filter(PermissionRequest.id == request_id)
            .first()
        )

        if not request:
            raise ValueError(f"权限申请不存在: {request_id}")

        if request.status != "pending":
            raise ValueError(f"权限申请状态不是待审批: {request.status}")

        # 更新申请状态
        request.status = "rejected"
        request.approved_by = rejected_by
        request.approved_at = datetime.now(UTC)
        request.approval_comment = rejection_reason

        # 创建审计日志
        audit_log = DynamicPermissionAudit(
            user_id=request.user_id,
            permission_id=",".join(request.permission_ids),  # 多个权限ID用逗号分隔
            action="REJECT_REQUEST",
            permission_type="request",
            scope=request.scope,
            scope_id=request.scope_id,
            assigned_by=rejected_by,
            reason=f"权限申请驳回: {rejection_reason}",
        )
        self.db.add(audit_log)

        self.db.commit()
        self.db.refresh(request)

        return request

    def get_pending_requests(
        self, approver_id: str | None = None, scope: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        """获取待审批的权限申请"""

        query = self.db.query(PermissionRequest).filter(
            PermissionRequest.status == "pending"
        )

        if scope:
            query = query.filter(PermissionRequest.scope == scope)

        requests = query.order_by(PermissionRequest.created_at).limit(limit).all()

        result = []
        for request in requests:
            # 获取权限详情
            permissions = (
                self.db.query(Permission)
                .filter(Permission.id.in_(request.permission_ids))
                .all()
            )

            # 获取用户详情
            user = self.db.query(User).filter(User.id == request.user_id).first()

            result.append(
                {
                    "id": request.id,
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "full_name": user.full_name,
                        "email": user.email,
                    }
                    if user
                    else None,
                    "permissions": [
                        {
                            "id": perm.id,
                            "name": perm.name,
                            "display_name": perm.display_name,
                            "description": perm.description,
                        }
                        for perm in permissions
                    ],
                    "scope": request.scope,
                    "scope_id": request.scope_id,
                    "reason": request.reason,
                    "requested_duration_hours": request.requested_duration_hours,
                    "requested_conditions": request.requested_conditions,
                    "created_at": request.created_at,
                    "status": request.status,
                }
            )

        return result

    def get_user_request_history(
        self, user_id: str, status: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        """获取用户的权限申请历史"""

        query = self.db.query(PermissionRequest).filter(
            PermissionRequest.user_id == user_id
        )

        if status:
            query = query.filter(PermissionRequest.status == status)

        requests = (
            query.order_by(PermissionRequest.created_at.desc()).limit(limit).all()
        )

        result = []
        for request in requests:
            # 获取权限详情
            permissions = (
                self.db.query(Permission)
                .filter(Permission.id.in_(request.permission_ids))
                .all()
            )

            # 获取审批人详情
            approver = None
            if request.approved_by:
                approver = (
                    self.db.query(User).filter(User.id == request.approved_by).first()
                )

            result.append(
                {
                    "id": request.id,
                    "permissions": [
                        {
                            "id": perm.id,
                            "name": perm.name,
                            "display_name": perm.display_name,
                        }
                        for perm in permissions
                    ],
                    "scope": request.scope,
                    "scope_id": request.scope_id,
                    "reason": request.reason,
                    "requested_duration_hours": request.requested_duration_hours,
                    "requested_conditions": request.requested_conditions,
                    "status": request.status,
                    "approval_comment": request.approval_comment,
                    "approver": {
                        "id": approver.id,
                        "username": approver.username,
                        "full_name": approver.full_name,
                    }
                    if approver
                    else None,
                    "created_at": request.created_at,
                    "updated_at": request.updated_at,
                    "approved_at": request.approved_at,
                }
            )

        return result

    def get_request_statistics(
        self, start_date: datetime | None = None, end_date: datetime | None = None
    ) -> dict[str, Any]:
        """获取权限申请统计信息"""

        query = self.db.query(PermissionRequest)

        if start_date:
            query = query.filter(PermissionRequest.created_at >= start_date)

        if end_date:
            query = query.filter(PermissionRequest.created_at <= end_date)

        # 总数统计
        total_requests = query.count()
        pending_requests = query.filter(PermissionRequest.status == "pending").count()
        approved_requests = query.filter(PermissionRequest.status == "approved").count()
        rejected_requests = query.filter(PermissionRequest.status == "rejected").count()

        # 按scope统计
        scope_stats = {}
        for request in query.all():
            scope = request.scope
            if scope not in scope_stats:
                scope_stats[scope] = {
                    "total": 0,
                    "pending": 0,
                    "approved": 0,
                    "rejected": 0,
                }
            scope_stats[scope]["total"] += 1
            scope_stats[scope][request.status] += 1

        # 按日期统计（最近7天）
        daily_stats = {}
        for i in range(7):
            date = datetime.now(UTC).date() - timedelta(days=i)
            daily_stats[date.isoformat()] = {
                "total": 0,
                "pending": 0,
                "approved": 0,
                "rejected": 0,
            }

        recent_requests = query.filter(
            PermissionRequest.created_at >= datetime.now(UTC) - timedelta(days=7)
        ).all()

        for request in recent_requests:
            date_str = request.created_at.date().isoformat()
            if date_str in daily_stats:
                daily_stats[date_str]["total"] += 1
                daily_stats[date_str][request.status] += 1

        return {
            "total": total_requests,
            "pending": pending_requests,
            "approved": approved_requests,
            "rejected": rejected_requests,
            "approval_rate": (approved_requests / total_requests * 100)
            if total_requests > 0
            else 0,
            "scope_statistics": scope_stats,
            "daily_statistics": daily_stats,
        }

    def cleanup_old_requests(self, days: int = 30) -> int:
        """清理旧的权限申请记录"""

        cutoff_date = datetime.now(UTC) - timedelta(days=days)

        # 只清理已处理（approved/rejected）的申请
        old_requests = (
            self.db.query(PermissionRequest)
            .filter(
                and_(
                    PermissionRequest.created_at < cutoff_date,
                    PermissionRequest.status.in_(["approved", "rejected"]),
                )
            )
            .all()
        )

        count = 0
        for request in old_requests:
            self.db.delete(request)
            count += 1

        self.db.commit()
        return count

    def bulk_approve_requests(
        self,
        request_ids: list[str],
        approved_by: str,
        approval_comment: str | None = None,
    ) -> list[dict[str, Any]]:
        """批量审批权限申请"""

        results = []

        for request_id in request_ids:
            try:
                result = self.approve_permission_request(
                    request_id=request_id,
                    approved_by=approved_by,
                    approval_comment=approval_comment,
                )
                results.append(
                    {"request_id": request_id, "success": True, "result": result}
                )
            except Exception as e:
                results.append(
                    {"request_id": request_id, "success": False, "error": str(e)}
                )

        return results

    def bulk_reject_requests(
        self, request_ids: list[str], rejected_by: str, rejection_reason: str
    ) -> list[dict[str, Any]]:
        """批量驳回权限申请"""

        results = []

        for request_id in request_ids:
            try:
                self.reject_permission_request(
                    request_id=request_id,
                    rejected_by=rejected_by,
                    rejection_reason=rejection_reason,
                )
                results.append({"request_id": request_id, "success": True})
            except Exception as e:
                results.append(
                    {"request_id": request_id, "success": False, "error": str(e)}
                )

        return results
