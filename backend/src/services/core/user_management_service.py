from datetime import datetime
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...crud.rbac import role_crud
from ...exceptions import BusinessLogicError
from ...models.auth import User
from ...models.rbac import UserRoleAssignment
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

    @staticmethod
    def _apply_user_filters_stmt(
        stmt: Any,
        *,
        search: str | None = None,
        role_id: str | None = None,
        is_active: bool | None = None,
        organization_id: str | None = None,
    ) -> Any:
        if search:
            search_filter = or_(
                User.username.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
                User.full_name.ilike(f"%{search}%"),
            )
            stmt = stmt.where(search_filter)

        if role_id is not None:
            stmt = stmt.join(
                UserRoleAssignment,
                UserRoleAssignment.user_id == User.id,
            ).where(
                UserRoleAssignment.role_id == role_id,
                UserRoleAssignment.is_active,
                or_(
                    UserRoleAssignment.expires_at.is_(None),
                    UserRoleAssignment.expires_at > func.now(),
                ),
            )

        if is_active is not None:
            stmt = stmt.where(User.is_active == is_active)

        if organization_id is not None:
            stmt = stmt.where(User.default_organization_id == organization_id)

        return stmt

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

    async def get_users_with_filters(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
        role_id: str | None = None,
        is_active: bool | None = None,
        organization_id: str | None = None,
    ) -> tuple[list[User], int]:
        stmt = select(User)
        stmt = self._apply_user_filters_stmt(
            stmt,
            search=search,
            role_id=role_id,
            is_active=is_active,
            organization_id=organization_id,
        )

        count_stmt = select(func.count(func.distinct(User.id))).select_from(User)
        count_stmt = self._apply_user_filters_stmt(
            count_stmt,
            search=search,
            role_id=role_id,
            is_active=is_active,
            organization_id=organization_id,
        )

        total = int((await self.db.execute(count_stmt)).scalar() or 0)
        users = list(
            (
                await self.db.execute(stmt.distinct(User.id).offset(skip).limit(limit))
            )
            .scalars()
            .all()
        )
        return users, total

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
        db_user.phone = user_data.phone
        db_user.full_name = user_data.full_name
        db_user.password_hash = hashed_password
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
        user = await self.unlock_user_with_result(user_id)
        return user is not None

    async def lock_user(self, user_id: str) -> User | None:
        user = await self.get_user_by_id(user_id)
        if not user:
            return None

        user.is_locked = True
        user.updated_at = datetime.now()

        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def unlock_user_with_result(self, user_id: str) -> User | None:
        user = await self.get_user_by_id(user_id)
        if not user:
            return None

        user.is_locked = False
        user.locked_until = None
        user.failed_login_attempts = 0
        user.updated_at = datetime.now()

        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def admin_reset_password(
        self, *, user_id: str, new_password: str
    ) -> User | None:
        user = await self.get_user_by_id(user_id)
        if not user:
            return None

        user.password_hash = self.password_service.get_password_hash(new_password)
        user.updated_at = datetime.now()

        await self.db.commit()
        await self.db.refresh(user)
        return user

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
