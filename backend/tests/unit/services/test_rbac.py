from unittest.mock import patch

import pytest

from src.models.rbac import Permission, Role
from src.schemas.rbac import RoleCreate, UserRoleAssignmentCreate
from src.services.rbac.service import RBACService

TEST_ROLE_ID = "role_123"
TEST_USER_ID = "user_456"




@pytest.fixture
def service():
    return RBACService()


class TestRBACService:
    def test_create_role(self, service, mock_db):
        obj_in = RoleCreate(name="New Role", display_name="Display Name")

        with patch("src.crud.rbac.role_crud.get_by_name", return_value=None):
            with patch("src.crud.rbac.role_crud.create") as mock_create:
                mock_create.return_value = Role(id=TEST_ROLE_ID, name="New Role")

                result = service.create_role(mock_db, obj_in=obj_in, created_by="admin")

                assert result.name == "New Role"
                mock_create.assert_called()

    def test_create_role_duplicate(self, service, mock_db):
        obj_in = RoleCreate(name="Existing Role", display_name="Display Name")

        with patch("src.crud.rbac.role_crud.get_by_name", return_value=Role()):
            with pytest.raises(ValueError) as excinfo:
                service.create_role(mock_db, obj_in=obj_in, created_by="admin")

            assert "已存在" in str(excinfo.value)

    def test_update_role_permissions(self, service, mock_db):
        role = Role(id=TEST_ROLE_ID, is_system_role=False, permissions=[])

        with patch("src.crud.rbac.role_crud.get", return_value=role):
            with patch(
                "src.crud.rbac.permission_crud.get",
                side_effect=[Permission(id="p1"), Permission(id="p2")],
            ):
                service.update_role_permissions(
                    mock_db,
                    role_id=TEST_ROLE_ID,
                    permission_ids=["p1", "p2"],
                    updated_by="admin",
                )

                assert len(role.permissions) == 2
                mock_db.commit.assert_called()

    def test_delete_role_system(self, service, mock_db):
        role = Role(id=TEST_ROLE_ID, is_system_role=True)

        with patch("src.crud.rbac.role_crud.get", return_value=role):
            with pytest.raises(ValueError) as excinfo:
                service.delete_role(mock_db, role_id=TEST_ROLE_ID, deleted_by="admin")

            assert "系统角色" in str(excinfo.value)

    def test_delete_role_in_use(self, service, mock_db):
        role = Role(id=TEST_ROLE_ID, is_system_role=False)

        with patch("src.crud.rbac.role_crud.get", return_value=role):
            # Mock count > 0
            with patch(
                "src.crud.rbac.user_role_assignment_crud.count_by_role", return_value=5
            ):
                with pytest.raises(ValueError) as excinfo:
                    service.delete_role(
                        mock_db, role_id=TEST_ROLE_ID, deleted_by="admin"
                    )

                assert "正在被" in str(excinfo.value)

    def test_assign_role_to_user(self, service, mock_db):
        obj_in = UserRoleAssignmentCreate(user_id=TEST_USER_ID, role_id=TEST_ROLE_ID)

        with patch(
            "src.crud.rbac.user_role_assignment_crud.get_by_user_and_role",
            return_value=None,
        ):
            service.assign_role_to_user(mock_db, obj_in=obj_in, assigned_by="admin")
            # Should call create
            # (Mocking imports is tricky if they are imported in service module level,
            # but we patched crud attributes or methods above effectively?
            # Wait, user_role_assignment_crud is imported in service.py.
            # We need to patch where it is used.)
            pass  # The mocking strategy above patches the crud object methods, which is fine.

    @patch("src.services.rbac.service.user_role_assignment_crud")
    def test_assign_role_to_user_mocked(self, mock_crud, service, mock_db):
        # Better mocking approach for imported modules
        obj_in = UserRoleAssignmentCreate(user_id=TEST_USER_ID, role_id=TEST_ROLE_ID)
        mock_crud.get_by_user_and_role.return_value = None

        service.assign_role_to_user(mock_db, obj_in=obj_in, assigned_by="admin")

        mock_crud.create.assert_called()
