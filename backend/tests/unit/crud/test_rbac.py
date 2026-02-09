"""
RBAC CRUD 操作单元测试（异步接口）。
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.crud.rbac import (
    CRUDPermission,
    CRUDRole,
    CRUDUserRoleAssignment,
    permission_crud,
    role_crud,
    user_role_assignment_crud,
)
from src.models.rbac import Permission, Role, UserRoleAssignment

pytestmark = pytest.mark.asyncio


def _mock_execute_result(
    *,
    first_value: object | None = None,
    all_values: list[object] | None = None,
    scalar_value: object | None = None,
    one_value: object | None = None,
) -> MagicMock:
    result = MagicMock()
    scalars_result = MagicMock()
    scalars_result.first.return_value = first_value
    scalars_result.all.return_value = [] if all_values is None else all_values
    result.scalars.return_value = scalars_result
    result.scalar.return_value = scalar_value
    result.all.return_value = [] if all_values is None else all_values
    if one_value is not None:
        result.one.return_value = one_value
    return result


class TestCRUDRole:
    @pytest.fixture
    def crud(self) -> CRUDRole:
        return CRUDRole(Role)

    @pytest.fixture
    def mock_role(self):
        role = MagicMock(spec=Role)
        role.id = "role_123"
        role.name = "admin"
        role.display_name = "管理员"
        role.category = "system"
        role.is_active = True
        role.level = 1
        role.is_system_role = True
        return role

    async def test_create_filters_permission_ids(self, crud: CRUDRole, mock_db: MagicMock):
        role_data = {
            "name": "test_role",
            "display_name": "测试角色",
            "permission_ids": ["perm_1", "perm_2"],
        }

        with patch("src.crud.base.CRUDBase.create", new=AsyncMock()) as mock_create:
            mock_create.return_value = MagicMock(spec=Role)
            await crud.create(mock_db, obj_in=role_data)

        mock_create.assert_awaited_once()
        assert "permission_ids" not in mock_create.call_args.kwargs["obj_in"]

    async def test_get_by_name_success(
        self, crud: CRUDRole, mock_db: MagicMock, mock_role
    ):
        mock_db.execute = AsyncMock(
            return_value=_mock_execute_result(first_value=mock_role)
        )

        result = await crud.get_by_name(mock_db, "admin")

        assert result == mock_role
        mock_db.execute.assert_awaited_once()

    async def test_get_by_name_not_found(self, crud: CRUDRole, mock_db: MagicMock):
        mock_db.execute = AsyncMock(return_value=_mock_execute_result(first_value=None))

        result = await crud.get_by_name(mock_db, "missing")

        assert result is None

    async def test_get_multi_with_filters(
        self, crud: CRUDRole, mock_db: MagicMock, mock_role
    ):
        mock_roles_result = _mock_execute_result(all_values=[mock_role])
        mock_count_result = _mock_execute_result(scalar_value=1)
        mock_db.execute = AsyncMock(side_effect=[mock_roles_result, mock_count_result])

        with (
            patch.object(crud.query_builder, "build_query", return_value=MagicMock()),
            patch.object(
                crud.query_builder,
                "build_count_query",
                return_value=MagicMock(),
            ),
        ):
            roles, total = await crud.get_multi_with_filters(
                mock_db,
                category="system",
                is_active=True,
                search="admin",
            )

        assert len(roles) == 1
        assert total == 1
        assert mock_db.execute.await_count == 2

    async def test_count_by_category(self, crud: CRUDRole, mock_db: MagicMock):
        mock_db.execute = AsyncMock(
            return_value=_mock_execute_result(
                all_values=[("system", 5), ("custom", 10), (None, 2)]
            )
        )

        result = await crud.count_by_category(mock_db)

        assert result["system"] == 5
        assert result["custom"] == 10
        assert None not in result

    async def test_count_by_flags(self, crud: CRUDRole, mock_db: MagicMock):
        mock_row = MagicMock(total=20, active=16, system=5, custom=15)
        mock_db.execute = AsyncMock(return_value=_mock_execute_result(one_value=mock_row))

        result = await crud.count_by_flags(mock_db)

        assert result == {"total": 20, "active": 16, "system": 5, "custom": 15}


class TestCRUDPermission:
    @pytest.fixture
    def crud(self) -> CRUDPermission:
        return CRUDPermission(Permission)

    @pytest.fixture
    def mock_permission(self):
        perm = MagicMock(spec=Permission)
        perm.id = "perm_123"
        perm.name = "asset:read"
        perm.display_name = "读取资产"
        perm.resource = "asset"
        perm.action = "read"
        perm.is_system_permission = True
        return perm

    async def test_get_by_name_success(
        self, crud: CRUDPermission, mock_db: MagicMock, mock_permission
    ):
        mock_db.execute = AsyncMock(
            return_value=_mock_execute_result(first_value=mock_permission)
        )

        result = await crud.get_by_name(mock_db, "asset:read")

        assert result == mock_permission

    async def test_get_multi_with_filters(
        self, crud: CRUDPermission, mock_db: MagicMock, mock_permission
    ):
        mock_db.execute = AsyncMock(
            return_value=_mock_execute_result(all_values=[mock_permission])
        )

        with patch.object(crud.query_builder, "build_query", return_value=MagicMock()):
            permissions = await crud.get_multi_with_filters(
                mock_db,
                resource="asset",
                action="read",
                is_system_permission=True,
            )

        assert len(permissions) == 1
        assert permissions[0] == mock_permission

    async def test_count_by_resource(self, crud: CRUDPermission, mock_db: MagicMock):
        mock_db.execute = AsyncMock(
            return_value=_mock_execute_result(
                all_values=[("asset", 10), ("user", 5), ("role", 3), (None, 2)]
            )
        )

        result = await crud.count_by_resource(mock_db)

        assert result["asset"] == 10
        assert result["user"] == 5
        assert result["role"] == 3
        assert None not in result


class TestCRUDUserRoleAssignment:
    @pytest.fixture
    def crud(self) -> CRUDUserRoleAssignment:
        return CRUDUserRoleAssignment(UserRoleAssignment)

    @pytest.fixture
    def mock_assignment(self):
        assignment = MagicMock(spec=UserRoleAssignment)
        assignment.id = "assignment_123"
        assignment.user_id = "user_123"
        assignment.role_id = "role_123"
        assignment.is_active = True
        assignment.expires_at = None
        return assignment

    async def test_get_by_user_and_role_success(
        self,
        crud: CRUDUserRoleAssignment,
        mock_db: MagicMock,
        mock_assignment,
    ):
        mock_db.execute = AsyncMock(
            return_value=_mock_execute_result(first_value=mock_assignment)
        )

        result = await crud.get_by_user_and_role(mock_db, "user_123", "role_123")

        assert result == mock_assignment

    async def test_get_by_user_and_role_not_found(
        self, crud: CRUDUserRoleAssignment, mock_db: MagicMock
    ):
        mock_db.execute = AsyncMock(return_value=_mock_execute_result(first_value=None))

        result = await crud.get_by_user_and_role(mock_db, "user_123", "role_456")

        assert result is None

    async def test_get_user_active_assignments(
        self,
        crud: CRUDUserRoleAssignment,
        mock_db: MagicMock,
        mock_assignment,
    ):
        mock_db.execute = AsyncMock(
            return_value=_mock_execute_result(all_values=[mock_assignment])
        )

        result = await crud.get_user_active_assignments(mock_db, "user_123")

        assert len(result) == 1
        assert result[0] == mock_assignment

    async def test_get_user_active_assignments_empty(
        self, crud: CRUDUserRoleAssignment, mock_db: MagicMock
    ):
        mock_db.execute = AsyncMock(return_value=_mock_execute_result(all_values=[]))

        result = await crud.get_user_active_assignments(mock_db, "user_without_roles")

        assert result == []

    async def test_count_by_role(self, crud: CRUDUserRoleAssignment, mock_db: MagicMock):
        mock_db.execute = AsyncMock(return_value=_mock_execute_result(scalar_value=10))

        result = await crud.count_by_role(mock_db, "role_123")

        assert result == 10


class TestGlobalInstances:
    def test_role_crud_instance_exists(self):
        assert role_crud is not None
        assert isinstance(role_crud, CRUDRole)

    def test_permission_crud_instance_exists(self):
        assert permission_crud is not None
        assert isinstance(permission_crud, CRUDPermission)

    def test_user_role_assignment_crud_instance_exists(self):
        assert user_role_assignment_crud is not None
        assert isinstance(user_role_assignment_crud, CRUDUserRoleAssignment)
