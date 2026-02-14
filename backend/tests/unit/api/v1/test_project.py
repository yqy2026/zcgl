"""
项目管理API测试

Test coverage for Project API endpoints:
- CRUD operations (Create, Read, Update, Delete)
- Search and filtering
- Pagination
- Dropdown options
- Error handling
- Authentication and authorization
"""

import pytest
from fastapi import status
from sqlalchemy.orm import Session

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def test_organization(db_session: Session):
    """创建测试组织数据"""
    from src.models.organization import Organization

    organization = Organization(
        id="org-unit-test-001",
        name="Unit Test Organization",
        code="ORG-UNIT-TEST-001",
        level=1,
        type="company",
        status="active",
    )
    db_session.add(organization)
    db_session.flush()
    db_session.refresh(organization)
    return organization


@pytest.fixture
def project_data(db_session: Session, test_organization):
    """创建测试项目数据"""
    from src.models.project import Project

    project = Project(
        name="Test Project",
        code="PJ2509001",
        city="Beijing",
        district="Chaoyang",
        address="Test Address 123",
        project_type="commercial",
        project_status="planning",
        ownership_entity="owner-001",
        organization_id=test_organization.id,
    )
    db_session.add(project)
    db_session.flush()
    db_session.refresh(project)
    yield project
    # Cleanup
    existing_project = db_session.query(Project).filter(Project.id == project.id).one_or_none()
    if existing_project is not None:
        db_session.delete(existing_project)
        db_session.flush()


@pytest.fixture
def admin_user_headers(client, admin_user, test_organization, monkeypatch):
    """管理员用户认证头"""
    from src.api.v1.assets import project as project_module
    from src.main import app
    from src.services.organization_permission_service import (
        OrganizationPermissionService,
    )

    def mock_get_current_user():
        return admin_user

    async def mock_get_user_accessible_organizations(self, user_id: str):
        return [test_organization.id]

    admin_user.default_organization_id = test_organization.id
    monkeypatch.setattr(
        OrganizationPermissionService,
        "get_user_accessible_organizations",
        mock_get_user_accessible_organizations,
    )

    app.dependency_overrides[project_module.get_current_active_user] = (
        mock_get_current_user
    )
    yield {}
    app.dependency_overrides.pop(project_module.get_current_active_user, None)


# ============================================================================
# Create Project Tests
# ============================================================================


class TestCreateProject:
    """测试创建项目API"""

    def test_create_project_success(self, client, admin_user_headers):
        """测试成功创建项目"""
        project_data = {
            "name": "New Test Project",
            "code": "PJ2509002",
            "city": "Shanghai",
            "district": "Pudong",
            "address": "Shanghai Test Address",
            "total_area": 15000.0,
            "build_area": 12000.0,
            "project_type": "office",
            "project_status": "active",
            "ownership_id": "owner-002",
        }

        response = client.post(
            "/api/v1/projects/", json=project_data, headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "New Test Project"
        assert data["code"] == "PJ2509002"
        assert "id" in data

    def test_create_project_unauthorized(self, unauthenticated_client):
        """测试未授权创建项目"""
        project_data = {"name": "Unauthorized Project", "code": "PJ2509003"}

        response = unauthenticated_client.post("/api/v1/projects/", json=project_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_project_duplicate_code(
        self, client, admin_user_headers, project_data
    ):
        """测试创建重复代码的项目"""
        duplicate_data = {
            "name": "Duplicate Project",
            "code": project_data.code,  # 重复代码
            "city": "Beijing",
        }

        response = client.post(
            "/api/v1/projects/", json=duplicate_data, headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_409_CONFLICT

    def test_create_project_invalid_data(self, client, admin_user_headers):
        """测试创建项目时数据验证失败"""
        invalid_data = {
            "name": "",  # 空名称
            "code": "PJ2509004",
            "total_area": -100.0,  # 负面积
        }

        response = client.post(
            "/api/v1/projects/", json=invalid_data, headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


# ============================================================================
# List Projects Tests
# ============================================================================


class TestListProjects:
    """测试获取项目列表API"""

    def test_list_projects_default(self, client, admin_user_headers, project_data):
        """测试获取项目列表（默认参数）"""
        response = client.get("/api/v1/projects/", headers=admin_user_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        payload = data["data"]
        assert "items" in payload
        assert "pagination" in payload

    def test_list_projects_with_pagination(self, client, admin_user_headers):
        """测试分页功能"""
        response = client.get(
            "/api/v1/projects/?page=1&page_size=10", headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        pagination = data["data"]["pagination"]
        assert pagination["page"] == 1
        assert pagination["page_size"] == 10

    def test_list_projects_with_keyword_search(
        self, client, admin_user_headers, project_data
    ):
        """测试关键词搜索"""
        response = client.get(
            f"/api/v1/projects/?keyword={project_data.name}", headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        items = data["data"]["items"]
        # 验证搜索结果包含测试项目
        assert any(item["name"] == project_data.name for item in items)

    def test_list_projects_unauthorized(self, unauthenticated_client):
        """测试未授权访问"""
        response = unauthenticated_client.get("/api/v1/projects/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ============================================================================
# Get Project by ID Tests
# ============================================================================


class TestGetProject:
    """测试获取单个项目API"""

    def test_get_project_success(self, client, admin_user_headers, project_data):
        """测试成功获取项目"""
        response = client.get(
            f"/api/v1/projects/{project_data.id}", headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == project_data.id
        assert data["name"] == project_data.name

    def test_get_project_not_found(self, client, admin_user_headers):
        """测试获取不存在的项目"""
        response = client.get(
            "/api/v1/projects/non-existent-id", headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


# ============================================================================
# Update Project Tests
# ============================================================================


class TestUpdateProject:
    """测试更新项目API"""

    def test_update_project_success(self, client, admin_user_headers, project_data):
        """测试成功更新项目"""
        update_data = {"name": "Updated Project Name", "total_area": 20000.0}

        response = client.put(
            f"/api/v1/projects/{project_data.id}",
            json=update_data,
            headers=admin_user_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Project Name"

    def test_update_project_not_found(self, client, admin_user_headers):
        """测试更新不存在的项目"""
        update_data = {"name": "Updated Name"}

        response = client.put(
            "/api/v1/projects/non-existent-id",
            json=update_data,
            headers=admin_user_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


# ============================================================================
# Search Projects Tests
# ============================================================================


class TestSearchProjects:
    """测试搜索项目API"""

    def test_search_projects_by_keyword(self, client, admin_user_headers, project_data):
        """测试关键词搜索"""
        search_params = {"keyword": project_data.name, "page": 1, "page_size": 10}

        response = client.post(
            "/api/v1/projects/search", json=search_params, headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data["data"]

    def test_search_projects_empty_result(self, client, admin_user_headers):
        """测试搜索无结果"""
        search_params = {
            "keyword": "NonExistentProjectNameXYZ",
            "page": 1,
            "page_size": 10,
        }

        response = client.post(
            "/api/v1/projects/search", json=search_params, headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        items = response.json()["data"]["items"]
        assert len(items) == 0

    def test_list_projects_with_city_filter(
        self, client, admin_user_headers, project_data
    ):
        """测试按城市筛选"""
        response = client.get(
            f"/api/v1/projects/?city={project_data.city}", headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        items = response.json()["data"]["items"]
        assert any(item.get("city") == project_data.city for item in items)

    def test_list_projects_with_type_filter(
        self, client, admin_user_headers, project_data
    ):
        """测试按项目类型筛选"""
        response = client.get(
            "/api/v1/projects/?project_type=commercial", headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        items = response.json()["data"]["items"]
        assert any(item.get("project_type") == "commercial" for item in items)

    def test_list_projects_with_status_filter(self, client, admin_user_headers):
        """测试按项目状态筛选"""
        response = client.get(
            "/api/v1/projects/?project_status=planning", headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        # 验证结果包含该状态的项目
        assert all(item.get("project_status") == "planning" for item in data["items"])

    def test_list_projects_sort_by_area(self, client, admin_user_headers):
        """测试按面积排序"""
        response = client.get(
            "/api/v1/projects/?sort_by=total_area&sort_order=desc",
            headers=admin_user_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        assert "items" in data

    def test_create_project_with_minimal_data(self, client, admin_user_headers):
        """测试使用最小数据创建项目"""
        minimal_data = {
            "name": "Minimal Project",
            "code": "PJ2509005",
            "city": "Shenzhen",
        }

        response = client.post(
            "/api/v1/projects/", json=minimal_data, headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK

    def test_update_project_partial_fields(
        self, client, admin_user_headers, project_data
    ):
        """测试部分字段更新"""
        partial_update = {"district": "Updated District"}

        response = client.put(
            f"/api/v1/projects/{project_data.id}",
            json=partial_update,
            headers=admin_user_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["district"] == "Updated District"
        # 验证其他字段未被修改
        assert data["name"] == project_data.name

    def test_list_projects_pagination_bounds(self, client, admin_user_headers):
        """测试分页边界情况"""
        # 测试过大的页码
        response = client.get(
            "/api/v1/projects/?page=9999&page_size=10", headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        # 应该返回空结果或最后一页
        assert "items" in data

    def test_create_project_with_unicode(self, client, admin_user_headers):
        """测试创建包含Unicode字符的项目"""
        unicode_data = {
            "name": "测试项目名称",
            "code": "PJ2509006",
            "city": "北京",
            "district": "朝阳区",
            "address": "北京市朝阳区测试地址123号",
        }

        response = client.post(
            "/api/v1/projects/", json=unicode_data, headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "测试项目名称"
        assert data["city"] == "北京"

    def test_update_project_with_invalid_code(
        self, client, admin_user_headers, project_data
    ):
        """测试使用无效编码更新项目"""
        invalid_update = {"code": "BAD-001"}

        response = client.put(
            f"/api/v1/projects/{project_data.id}",
            json=invalid_update,
            headers=admin_user_headers,
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_delete_project_success(
        self, client, admin_user_headers, db_session: Session, test_organization
    ):
        """测试成功删除项目"""
        from src.models.project import Project

        # 创建一个待删除的项目
        project = Project(
            name="To Be Deleted",
            code="PJ2509007",
            city="Test City",
            organization_id=test_organization.id,
        )
        db_session.add(project)
        db_session.flush()
        db_session.refresh(project)

        response = client.delete(
            f"/api/v1/projects/{project.id}", headers=admin_user_headers
        )

        # 验证删除成功
        assert response.status_code == status.HTTP_200_OK

        # 验证项目已被删除
        get_response = client.get(
            f"/api/v1/projects/{project.id}", headers=admin_user_headers
        )
        assert get_response.status_code == status.HTTP_404_NOT_FOUND
