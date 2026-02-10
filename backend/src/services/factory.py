"""
Service Factory — 统一管理 Service 层的实例化与依赖注入

解决的问题：
1. Service 间依赖通过内部实例化导致的紧耦合
2. 同一请求中 Service 被重复实例化（如 SessionService ×3）
3. 难以为 Service 注入 Mock 对象进行单元测试

用法：
    # 在路由模块中
    from fastapi import Depends
    from ..services.factory import get_service_factory, ServiceFactory

    _get_factory = get_service_factory()

    @router.post("/login")
    async def login(factory: ServiceFactory = Depends(_get_factory)):
        auth_service = factory.authentication
        ...

    # 在测试中直接注入 Mock
    factory = ServiceFactory(db, password_service=mock_password_service)
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from .core.authentication_service import AsyncAuthenticationService
from .core.password_service import PasswordService
from .core.session_service import AsyncSessionService
from .core.user_management_service import AsyncUserManagementService
from .permission.rbac_service import RBACService

# 全局无状态服务单例
_password_service = PasswordService()


class ServiceFactory:
    """
    Service 工厂 — 管理 Service 实例化与依赖注入

    每个请求创建一个 ServiceFactory 实例（通过 FastAPI Depends），
    内部缓存确保同一请求中每个 Service 只实例化一次。

    支持通过构造函数注入自定义实例（用于测试）。
    """

    def __init__(
        self,
        db: AsyncSession,
        *,
        password_service: PasswordService | None = None,
        session_service: AsyncSessionService | None = None,
        rbac_service: RBACService | None = None,
        user_management_service: AsyncUserManagementService | None = None,
        authentication_service: AsyncAuthenticationService | None = None,
    ):
        self.db = db
        # 允许注入自定义实例（测试用），否则延迟创建
        self._password_service = password_service
        self._session_service = session_service
        self._rbac_service = rbac_service
        self._user_management_service = user_management_service
        self._authentication_service = authentication_service

    @property
    def password(self) -> PasswordService:
        """无状态服务，使用全局单例"""
        if self._password_service is None:
            self._password_service = _password_service
        return self._password_service

    @property
    def session(self) -> AsyncSessionService:
        """会话管理服务（每个 Factory 实例缓存一次）"""
        if self._session_service is None:
            self._session_service = AsyncSessionService(self.db)
        return self._session_service

    @property
    def rbac(self) -> RBACService:
        """RBAC 权限服务"""
        if self._rbac_service is None:
            self._rbac_service = RBACService(self.db)
        return self._rbac_service

    @property
    def user_management(self) -> AsyncUserManagementService:
        """用户管理服务（自动注入 password/session/rbac 依赖）"""
        if self._user_management_service is None:
            self._user_management_service = AsyncUserManagementService(
                self.db,
                password_service=self.password,
                session_service=self.session,
                rbac_service=self.rbac,
            )
        return self._user_management_service

    @property
    def authentication(self) -> AsyncAuthenticationService:
        """认证服务（自动注入 password/user/session 依赖）"""
        if self._authentication_service is None:
            self._authentication_service = AsyncAuthenticationService(
                self.db,
                password_service=self.password,
                user_service=self.user_management,
                session_service=self.session,
            )
        return self._authentication_service


# ============================================================================
# FastAPI 依赖函数
# ============================================================================


def get_service_factory():  # noqa: ANN201
    """
    创建可被 FastAPI Depends 使用的 ServiceFactory 依赖函数。

    使用延迟导入避免模块加载时触发数据库配置检查。
    返回值是一个 async 函数，可直接传入 Depends()。

    用法::

        from fastapi import Depends
        from ..services.factory import get_service_factory, ServiceFactory

        # 在路由模块顶部调用一次（此时延迟导入被触发）
        _get_factory = get_service_factory()

        @router.post("/login")
        async def login(
            factory: ServiceFactory = Depends(_get_factory),
        ):
            auth_service = factory.authentication
            user_service = factory.user_management

    测试用法::

        factory = ServiceFactory(mock_db, password_service=mock_pwd)
        auth_service = factory.authentication
    """
    from fastapi import Depends

    from ..database import get_async_db

    async def _factory(
        db: AsyncSession = Depends(get_async_db),
    ) -> ServiceFactory:
        return ServiceFactory(db)

    return _factory
