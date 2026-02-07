from datetime import datetime
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...crud.rbac import role_crud
from ...exceptions import BusinessLogicError
from ...models.auth import User
from ...schemas.auth import UserCreate, UserUpdate
from ...schemas.rbac import UserRoleAssignmentCreate
from ..permission.rbac_service import RBACService
from .password_service import PasswordService
from .session_service import AsyncSessionService


class AsyncUserManagementService:
    """用户管理服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.password_service = PasswordService()
        self.session_service = AsyncSessionService(db)
        self.rbac_service = RBACService(db)

    async def _assign_primary_role(
        self,
        user_id: str,
        role_id: str | None,
        assigned_by: str | None = None,
    ) -> None:
        if role_id is None:
            # Default to asset_viewer as the least-privilege baseline role
            role_obj = await role_crud.get_by_name(self.db, name="asset_viewer")
            role_id = str(role_obj.id) if role_obj else None

        if not role_id:
            return

        assignment = UserRoleAssignmentCreate(user_id=user_id, role_id=role_id)
        await self.rbac_service.assign_role_to_user(
            assignment_data=assignment, assigned_by=assigned_by or "system"
        )

    async def get_user_by_id(self, user_id: str) -> User | None:
        stmt = select(User).where(User.id == user_id)
        return (await self.db.execute(stmt)).scalars().first()

    async def get_user_by_username(self, username: str) -> User | None:
        stmt = select(User).where(User.username == username)
        return (await self.db.execute(stmt)).scalars().first()

    async def get_user_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        return (await self.db.execute(stmt)).scalars().first()

    async def create_user(
        self, user_data: UserCreate, assigned_by: str | None = None
    ) -> User:
        stmt = select(User).where(
            or_(User.username == user_data.username, User.email == user_data.email)
        )
        existing_user = (await self.db.execute(stmt)).scalars().first()
        if existing_user:
            if existing_user.username == user_data.username:
                raise BusinessLogicError("用户名已存在")
            raise BusinessLogicError("邮箱已存在")

        if not self.password_service.validate_password_strength(user_data.password):
            raise BusinessLogicError("密码不符合安全要求")

        hashed_password = self.password_service.get_password_hash(user_data.password)
        db_user = User()
        db_user.username = user_data.username
        db_user.email = user_data.email
        db_user.full_name = user_data.full_name
        db_user.password_hash = hashed_password
        db_user.employee_id = user_data.employee_id
        db_user.default_organization_id = user_data.default_organization_id

        self.password_service.add_password_to_history(db_user, hashed_password)

        self.db.add(db_user)
        await self.db.commit()
        await self.db.refresh(db_user)

        await self._assign_primary_role(
            user_id=str(db_user.id),
            role_id=user_data.role_id,
            assigned_by=assigned_by,
        )

        return db_user

    async def update_user(
        self, user_id: str, user_data: UserUpdate, assigned_by: str | None = None
    ) -> User | None:
        user = await self.get_user_by_id(user_id)
        if not user:
            return None

        if user_data.email and user_data.email != user.email:
            existing_user = await self.get_user_by_email(user_data.email)
            if existing_user:
                raise BusinessLogicError("邮箱已被其他用户使用")

        username = getattr(user_data, "username", None)
        if username and username != user.username:
            existing_user = await self.get_user_by_username(username)
            if existing_user:
                raise BusinessLogicError("用户名已被其他用户使用")

        update_data: dict[str, Any] = user_data.model_dump(exclude_unset=True)
        role_id = update_data.pop("role_id", None)
        for field, value in update_data.items():
            setattr(user, field, value)

        user.updated_at = datetime.now()
        await self.db.commit()
        await self.db.refresh(user)

        if role_id is not None:
            # Replace active roles with the provided primary role
            assignments = await self.rbac_service.get_user_roles(user_id)
            for role in assignments:
                await self.rbac_service.revoke_role_from_user(
                    user_id, str(role.id), revoked_by=assigned_by or user_id
                )
            await self._assign_primary_role(
                user_id=user_id, role_id=role_id, assigned_by=assigned_by
            )

        return user

    async def deactivate_user(self, user_id: str) -> bool:
        user = await self.get_user_by_id(user_id)
        if not user:
            return False

        user.is_active = False
        user.updated_at = datetime.now()

        await self.session_service.revoke_all_user_sessions(user_id)

        await self.db.commit()
        return True

    async def activate_user(self, user_id: str) -> bool:
        user = await self.get_user_by_id(user_id)
        if not user:
            return False

        user.is_active = True
        user.is_locked = False
        user.locked_until = None
        user.failed_login_attempts = 0
        user.updated_at = datetime.now()

        await self.db.commit()
        return True

    async def unlock_user(self, user_id: str) -> bool:
        user = await self.get_user_by_id(user_id)
        if not user:
            return False

        user.is_locked = False
        user.locked_until = None
        user.failed_login_attempts = 0
        user.updated_at = datetime.now()

        await self.db.commit()
        return True

    async def get_statistics(self) -> dict[str, Any]:
        total_users = int(
            (await self.db.execute(select(func.count(User.id)))).scalar() or 0
        )
        active_users = int(
            (
                await self.db.execute(
                    select(func.count(User.id)).where(User.is_active.is_(True))
                )
            ).scalar()
            or 0
        )
        locked_users = int(
            (
                await self.db.execute(
                    select(func.count(User.id)).where(User.is_locked.is_(True))
                )
            ).scalar()
            or 0
        )
        inactive_users = int(
            (
                await self.db.execute(
                    select(func.count(User.id)).where(User.is_active.is_(False))
                )
            ).scalar()
            or 0
        )

        return {
            "total_users": total_users,
            "active_users": active_users,
            "locked_users": locked_users,
            "inactive_users": inactive_users,
            "online_users": 0,
        }

    async def change_password(
        self, user: User, current_password: str, new_password: str
    ) -> bool:
        if not self.password_service.verify_password(
            current_password, user.password_hash
        ):
            raise BusinessLogicError("当前密码不正确")

        if not self.password_service.validate_password_strength(new_password):
            raise BusinessLogicError("新密码不符合安全要求")

        if self.password_service.is_password_in_history(user, new_password):
            raise BusinessLogicError("新密码不能与最近使用过的密码相同")

        new_password_hash = self.password_service.get_password_hash(new_password)
        user.password_hash = new_password_hash

        self.password_service.add_password_to_history(user, new_password_hash)

        await self.db.commit()

        await self.session_service.revoke_all_user_sessions(user.id)

        return True
