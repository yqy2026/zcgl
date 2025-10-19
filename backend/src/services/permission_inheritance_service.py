"""
权限继承和委托服务
支持权限的自动继承、委托和临时授权
"""

from typing import List, Optional, Dict, Any, Tuple, Set
from datetime import datetime, timedelta
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
import uuid

from ..models.rbac import Role, Permission, UserRoleAssignment
from ..models.auth import User
from ..models.organization import Organization
from ..models.dynamic_permission import DynamicPermissionAudit
from ..exceptions import BusinessLogicError


class InheritanceType(str, Enum):
    """继承类型"""
    ROLE_INHERITANCE = "role_inheritance"          # 角色继承
    ORGANIZATION_INHERITANCE = "org_inheritance"  # 组织继承
    POSITION_INHERITANCE = "position_inheritance"  # 职位继承
    DELEGATED = "delegated"                       # 委托权限


class DelegationScope(str, Enum):
    """委托范围"""
    SPECIFIC_RESOURCE = "specific_resource"       # 特定资源
    RESOURCE_TYPE = "resource_type"              # 资源类型
    ORGANIZATION = "organization"                 # 组织范围
    GLOBAL = "global"                            # 全局范围


class PermissionInheritanceService:
    """权限继承和委托服务"""

    def __init__(self, db: Session):
        self.db = db

    def get_inherited_permissions(
        self,
        user_id: str,
        inheritance_types: Optional[List[InheritanceType]] = None
    ) -> List[Dict[str, Any]]:
        """
        获取用户继承的权限

        Args:
            user_id: 用户ID
            inheritance_types: 继承类型筛选

        Returns:
            继承的权限列表
        """
        inherited_permissions = []

        # 获取用户的基本角色权限
        role_permissions = self._get_role_inherited_permissions(user_id)
        inherited_permissions.extend(role_permissions)

        # 获取组织层级继承权限
        org_permissions = self._get_organization_inherited_permissions(user_id)
        inherited_permissions.extend(org_permissions)

        # 获取职位继承权限
        position_permissions = self._get_position_inherited_permissions(user_id)
        inherited_permissions.extend(position_permissions)

        # 获取委托权限
        delegated_permissions = self._get_delegated_permissions(user_id)
        inherited_permissions.extend(delegated_permissions)

        # 按继承类型筛选
        if inheritance_types:
            inherited_permissions = [
                perm for perm in inherited_permissions
                if perm.get("inheritance_type") in inheritance_types
            ]

        # 去重并合并权限
        unique_permissions = self._merge_duplicate_permissions(inherited_permissions)

        return unique_permissions

    def delegate_permission(
        self,
        delegator_id: str,
        delegatee_id: str,
        permission_codes: List[str],
        delegation_scope: DelegationScope,
        scope_id: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        conditions: Optional[Dict[str, Any]] = None,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        委托权限给其他用户

        Args:
            delegator_id: 委托人ID
            delegatee_id: 被委托人ID
            permission_codes: 权限代码列表
            delegation_scope: 委托范围
            scope_id: 范围ID（当scope不是global时需要）
            expires_at: 过期时间
            conditions: 委托条件
            reason: 委托原因

        Returns:
            委托结果
        """
        # 验证用户存在
        delegator = self.db.query(User).filter(User.id == delegator_id).first()
        delegatee = self.db.query(User).filter(User.id == delegatee_id).first()

        if not delegator or not delegatee:
            raise BusinessLogicError("用户不存在")

        # 验证委托人是否具有被委托的权限
        delegator_permissions = self._get_user_effective_permissions(delegator_id)

        for permission_code in permission_codes:
            if permission_code not in [p["code"] for p in delegator_permissions]:
                raise BusinessLogicError(f"委托人不具有权限: {permission_code}")

        # 创建委托权限记录
        delegation_id = str(uuid.uuid4())

        # 这里需要创建一个权限委托模型，暂时使用动态权限模型
        from ..services.dynamic_permission_service import DynamicPermissionService
        dynamic_service = DynamicPermissionService(self.db)

        delegated_permissions = []
        for permission_code in permission_codes:
            # 获取权限ID
            permission = self.db.query(Permission).filter(
                Permission.code == permission_code
            ).first()

            if permission:
                # 通过动态权限服务创建委托权限
                dynamic_perms = dynamic_service.assign_dynamic_permission(
                    user_id=delegatee_id,
                    permission_ids=[permission.id],
                    permission_type="delegated",
                    scope=delegation_scope,
                    scope_id=scope_id,
                    expires_at=expires_at,
                    conditions={
                        **(conditions or {}),
                        "delegated_by": delegator_id,
                        "delegation_id": delegation_id
                    },
                    assigned_by=delegator_id,
                    reason=reason or f"权限委托: {permission_code}"
                )
                delegated_permissions.extend(dynamic_perms)

        # 记录委托审计日志
        self._log_delegation_audit(
            delegator_id=delegator_id,
            delegatee_id=delegatee_id,
            permission_codes=permission_codes,
            delegation_scope=delegation_scope,
            scope_id=scope_id,
            expires_at=expires_at,
            reason=reason
        )

        return {
            "delegation_id": delegation_id,
            "delegator_id": delegator_id,
            "delegatee_id": delegatee_id,
            "permission_codes": permission_codes,
            "scope": delegation_scope,
            "scope_id": scope_id,
            "expires_at": expires_at,
            "delegated_permissions": [
                {
                    "id": perm.id,
                    "permission_id": perm.permission_id,
                    "expires_at": perm.expires_at
                } for perm in delegated_permissions
            ]
        }

    def revoke_delegation(
        self,
        delegation_id: str,
        revoked_by: str,
        reason: Optional[str] = None
    ) -> bool:
        """
        撤销权限委托

        Args:
            delegation_id: 委托ID
            revoked_by: 撤销人ID
            reason: 撤销原因

        Returns:
            是否成功撤销
        """
        from ..services.dynamic_permission_service import DynamicPermissionService
        dynamic_service = DynamicPermissionService(self.db)

        # 查找所有相关的委托权限
        delegated_permissions = self.db.query(DynamicPermissionAudit).filter(
            and_(
                DynamicPermissionAudit.assigned_by.contains({"delegation_id": delegation_id}),
                DynamicPermissionAudit.action == "ASSIGN"
            )
        ).all()

        revoked_count = 0
        for delegation in delegated_permissions:
            # 撤销动态权限
            success = dynamic_service.revoke_dynamic_permission(
                permission_id=delegation.permission_id,
                user_id=delegation.user_id,
                revoked_by=revoked_by,
                reason=reason
            )
            if success:
                revoked_count += 1

        # 记录撤销审计日志
        self._log_delegation_revoke_audit(
            delegation_id=delegation_id,
            revoked_by=revoked_by,
            revoked_count=revoked_count,
            reason=reason
        )

        return revoked_count > 0

    def get_delegation_chain(
        self,
        user_id: str,
        max_depth: int = 5
    ) -> List[Dict[str, Any]]:
        """
        获取权限委托链

        Args:
            user_id: 用户ID
            max_depth: 最大深度

        Returns:
            委托链信息
        """
        delegation_chain = []
        visited_users = set()

        def _build_chain(current_user_id: str, depth: int, path: List[str]):
            if depth >= max_depth or current_user_id in visited_users:
                return

            visited_users.add(current_user_id)

            # 查找当前用户的委托权限
            delegated_from = self.db.query(DynamicPermissionAudit).filter(
                and_(
                    DynamicPermissionAudit.user_id == current_user_id,
                    DynamicPermissionAudit.action == "ASSIGN",
                    DynamicPermissionAudit.conditions.contains({"delegated_by": {"$exists": True}})
                )
            ).all()

            for delegation in delegated_from:
                delegator_id = delegation.conditions.get("delegated_by")
                if delegator_id and delegator_id not in path:
                    new_path = path + [delegator_id]
                    delegation_chain.append({
                        "delegator_id": delegator_id,
                        "delegatee_id": current_user_id,
                        "depth": depth,
                        "path": new_path,
                        "permission_id": delegation.permission_id,
                        "delegated_at": delegation.created_at
                    })

                    # 递归查找上级委托
                    _build_chain(delegator_id, depth + 1, new_path)

        _build_chain(user_id, 0, [user_id])

        # 按深度排序
        delegation_chain.sort(key=lambda x: x["depth"])

        return delegation_chain

    def get_permission_inheritance_tree(
        self,
        user_id: str,
        permission_code: str
    ) -> Dict[str, Any]:
        """
        获取特定权限的继承树

        Args:
            user_id: 用户ID
            permission_code: 权限代码

        Returns:
            权限继承树
        """
        # 获取用户的所有权限继承路径
        inherited_permissions = self.get_inherited_permissions(user_id)

        # 筛选指定权限的继承路径
        permission_inheritance = [
            perm for perm in inherited_permissions
            if perm.get("permission_code") == permission_code
        ]

        return {
            "user_id": user_id,
            "permission_code": permission_code,
            "inheritance_paths": permission_inheritance,
            "total_paths": len(permission_inheritance),
            "inheritance_types": list(set([
                perm.get("inheritance_type") for perm in permission_inheritance
            ]))
        }

    def calculate_effective_permissions(
        self,
        user_id: str,
        include_inherited: bool = True,
        include_delegated: bool = True
    ) -> List[Dict[str, Any]]:
        """
        计算用户的有效权限

        Args:
            user_id: 用户ID
            include_inherited: 是否包含继承权限
            include_delegated: 是否包含委托权限

        Returns:
            有效权限列表
        """
        effective_permissions = []

        # 获取直接权限（角色权限）
        direct_permissions = self._get_user_direct_permissions(user_id)
        effective_permissions.extend(direct_permissions)

        if include_inherited:
            # 获取继承权限
            inherited_permissions = self.get_inherited_permissions(user_id)
            effective_permissions.extend(inherited_permissions)

        if include_delegated:
            # 获取委托权限
            delegated_permissions = self._get_delegated_permissions(user_id)
            effective_permissions.extend(delegated_permissions)

        # 合并和去重
        unique_permissions = self._merge_duplicate_permissions(effective_permissions)

        return unique_permissions

    def _get_role_inherited_permissions(self, user_id: str) -> List[Dict[str, Any]]:
        """获取角色继承权限"""
        user_roles = self.db.query(UserRoleAssignment).filter(
            and_(
                UserRoleAssignment.user_id == user_id,
                UserRoleAssignment.is_active == True,
                or_(
                    UserRoleAssignment.expires_at.is_(None),
                    UserRoleAssignment.expires_at > datetime.utcnow()
                )
            )
        ).all()

        inherited_permissions = []
        for role_assignment in user_roles:
            role = self.db.query(Role).filter(Role.id == role_assignment.role_id).first()
            if role:
                # 获取角色权限
                role_permissions = self.db.query(Permission).join(
                    # 这里需要关联角色权限表
                    # 暂时简化处理
                ).all()

                for permission in role_permissions:
                    inherited_permissions.append({
                        "user_id": user_id,
                        "permission_id": permission.id,
                        "permission_code": permission.code,
                        "permission_name": permission.name,
                        "inheritance_type": InheritanceType.ROLE_INHERITANCE,
                        "source_id": role.id,
                        "source_name": role.name,
                        "inherited_at": role_assignment.assigned_at
                    })

        return inherited_permissions

    def _get_organization_inherited_permissions(self, user_id: str) -> List[Dict[str, Any]]:
        """获取组织继承权限"""
        # 获取用户所属组织
        user_orgs = self.db.query(Organization).join(
            # 这里需要关联用户组织表
            # 暂时简化处理
        ).filter(
            # 添加用户组织关联条件
        ).all()

        inherited_permissions = []
        for org in user_orgs:
            # 获取组织权限
            org_permissions = self._get_organization_permissions(org.id)

            for permission in org_permissions:
                inherited_permissions.append({
                    "user_id": user_id,
                    "permission_id": permission["id"],
                    "permission_code": permission["code"],
                    "permission_name": permission["name"],
                    "inheritance_type": InheritanceType.ORGANIZATION_INHERITANCE,
                    "source_id": org.id,
                    "source_name": org.name,
                    "inherited_at": datetime.utcnow()  # 这里应该记录实际继承时间
                })

        return inherited_permissions

    def _get_position_inherited_permissions(self, user_id: str) -> List[Dict[str, Any]]:
        """获取职位继承权限"""
        # 获取用户职位信息
        # 这里需要关联员工表和职位表
        # 暂时返回空列表
        return []

    def _get_delegated_permissions(self, user_id: str) -> List[Dict[str, Any]]:
        """获取委托权限"""
        from ..services.dynamic_permission_service import DynamicPermissionService
        dynamic_service = DynamicPermissionService(self.db)

        delegated_permissions = dynamic_service.get_user_dynamic_permissions(
            user_id=user_id,
            include_expired=False
        )

        # 筛选出委托类型的权限
        delegated = [
            {
                "user_id": user_id,
                "permission_id": perm["permission_id"],
                "permission_code": perm["permission_code"],
                "permission_name": perm["permission_name"],
                "inheritance_type": InheritanceType.DELEGATED,
                "source_id": perm.get("assigned_by"),
                "source_name": "委托人",
                "inherited_at": perm["assigned_at"],
                "expires_at": perm["expires_at"],
                "conditions": perm.get("conditions", {})
            }
            for perm in delegated_permissions
            if perm.get("permission_type") == "delegated"
        ]

        return delegated

    def _get_user_direct_permissions(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户直接权限"""
        # 获取用户的直接角色权限
        user_roles = self.db.query(UserRoleAssignment).filter(
            and_(
                UserRoleAssignment.user_id == user_id,
                UserRoleAssignment.is_active == True
            )
        ).all()

        direct_permissions = []
        for role_assignment in user_roles:
            role = self.db.query(Role).filter(Role.id == role_assignment.role_id).first()
            if role:
                # 这里需要获取角色的直接权限
                # 暂时简化处理
                pass

        return direct_permissions

    def _get_user_effective_permissions(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户有效权限（用于委托验证）"""
        return self.calculate_effective_permissions(user_id)

    def _get_organization_permissions(self, organization_id: str) -> List[Dict[str, Any]]:
        """获取组织权限"""
        # 这里需要实现组织权限查询
        # 暂时返回空列表
        return []

    def _merge_duplicate_permissions(self, permissions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """合并重复权限"""
        unique_permissions = {}

        for perm in permissions:
            key = perm.get("permission_code")
            if key:
                if key not in unique_permissions:
                    unique_permissions[key] = perm
                else:
                    # 合并继承信息
                    existing = unique_permissions[key]
                    if "inheritance_sources" not in existing:
                        existing["inheritance_sources"] = []

                    existing["inheritance_sources"].append({
                        "inheritance_type": perm.get("inheritance_type"),
                        "source_id": perm.get("source_id"),
                        "source_name": perm.get("source_name"),
                        "inherited_at": perm.get("inherited_at")
                    })

        return list(unique_permissions.values())

    def _log_delegation_audit(
        self,
        delegator_id: str,
        delegatee_id: str,
        permission_codes: List[str],
        delegation_scope: DelegationScope,
        scope_id: Optional[str],
        expires_at: Optional[datetime],
        reason: Optional[str]
    ):
        """记录委托审计日志"""
        audit_log = DynamicPermissionAudit(
            user_id=delegatee_id,
            permission_id="",  # 这里可以记录为批量权限ID
            action="DELEGATE_PERMISSION",
            permission_type="delegated",
            scope=delegation_scope,
            scope_id=scope_id,
            assigned_by=delegator_id,
            reason=reason or f"委托权限: {', '.join(permission_codes)}",
            conditions={
                "delegated_permissions": permission_codes,
                "delegation_scope": delegation_scope,
                "expires_at": expires_at.isoformat() if expires_at else None
            },
            created_at=datetime.utcnow()
        )
        self.db.add(audit_log)
        self.db.commit()

    def _log_delegation_revoke_audit(
        self,
        delegation_id: str,
        revoked_by: str,
        revoked_count: int,
        reason: Optional[str]
    ):
        """记录委托撤销审计日志"""
        audit_log = DynamicPermissionAudit(
            user_id="",  # 系统操作
            permission_id="",
            action="REVOKE_DELEGATION",
            permission_type="delegated",
            scope="global",
            scope_id=None,
            assigned_by=revoked_by,
            reason=reason or f"撤销委托: {delegation_id}",
            conditions={
                "delegation_id": delegation_id,
                "revoked_count": revoked_count
            },
            created_at=datetime.utcnow()
        )
        self.db.add(audit_log)
        self.db.commit()