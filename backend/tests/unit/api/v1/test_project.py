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
def project_data(db: Session):
    """创建测试项目数据"""
    from src.schemas.project import ProjectCreate
    from src.crud.project import project_crud

    project = project_crud.create(
        db,
        obj_in=ProjectCreate(
            name="Test Project",
            code="TEST-001",
            city="Beijing",
            district="Chaoyang",
            address="Test Address 123",
            total_area=10000.0,
            build_area=8000.0,
            project_type="commercial",
            project_status="planning",
            ownership_id="owner-001"
        )
    )
    yield project
    # Cleanup
    try:
        project_crud.remove(db, id=project.id)
    except:
        pass


@pytest.fixture
def admin_user_headers(client, admin_user):
    """管理员用户认证头"""
    response = client.post(
        "/api/v1/auth/login",
        data={"username": admin_user.username, "password": "admin123"}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ============================================================================
# Create Project Tests
# ============================================================================

class TestCreateProject:
    """测试创建项目API"""

    def test_create_project_success(self, client, admin_user_headers):
        """测试成功创建项目"""
        project_data = {
            "name": "New Test Project",
            "code": "NEW-001",
            "city": "Shanghai",
            "district": "Pudong",
            "address": "Shanghai Test Address",
            "total_area": 15000.0,
            "build_area": 12000.0,
            "project_type": "office",
            "project_status": "active",
            "ownership_id": "owner-002"
        }

        response = client.post(
            "/api/v1/project/",
            json=project_data,
            headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "New Test Project"
        assert data["code"] == "NEW-001"
        assert "id" in data

    def test_create_project_unauthorized(self, client):
        """测试未授权创建项目"""
        project_data = {
            "name": "Unauthorized Project",
            "code": "UNAUTH-001"
        }

        response = client.post(
            "/api/v1/project/",
            json=project_data
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_project_duplicate_code(self, client, admin_user_headers, project_data):
        """测试创建重复代码的项目"""
        duplicate_data = {
            "name": "Duplicate Project",
            "code": project_data.code,  # 重复代码
            "city": "Beijing"
        }

        response = client.post(
            "/api/v1/project/",
            json=duplicate_data,
            headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_project_invalid_data(self, client, admin_user_headers):
        """测试创建项目时数据验证失败"""
        invalid_data = {
            "name": "",  # 空名称
            "code": "INV-001",
            "total_area": -100.0  # 负面积
        }

        response = client.post(
            "/api/v1/project/",
            json=invalid_data,
            headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ============================================================================
# List Projects Tests
# ============================================================================

class TestListProjects:
    """测试获取项目列表API"""

    def test_list_projects_default(self, client, admin_user_headers, project_data):
        """测试获取项目列表（默认参数）"""
        response = client.get(
            "/api/v1/project/",
            headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data

    def test_list_projects_with_pagination(self, client, admin_user_headers):
        """测试分页功能"""
        response = client.get(
            "/api/v1/project/?page=1&page_size=10",
            headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 10

    def test_list_projects_with_keyword_search(self, client, admin_user_headers, project_data):
        """测试关键词搜索"""
        response = client.get(
            f"/api/v1/project/?keyword={project_data.name}",
            headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # 验证搜索结果包含测试项目
        assert any(item["name"] == project_data.name for item in data["items"])

    def test_list_projects_unauthorized(self, client):
        """测试未授权访问"""
        response = client.get("/api/v1/project/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ============================================================================
# Get Project by ID Tests
# ============================================================================

class TestGetProject:
    """测试获取单个项目API"""

    def test_get_project_success(self, client, admin_user_headers, project_data):
        """测试成功获取项目"""
        response = client.get(
            f"/api/v1/project/{project_data.id}",
            headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == project_data.id
        assert data["name"] == project_data.name

    def test_get_project_not_found(self, client, admin_user_headers):
        """测试获取不存在的项目"""
        response = client.get(
            "/api/v1/project/non-existent-id",
            headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


# ============================================================================
# Update Project Tests
# ============================================================================

class TestUpdateProject:
    """测试更新项目API"""

    def test_update_project_success(self, client, admin_user_headers, project_data):
        """测试成功更新项目"""
        update_data = {
            "name": "Updated Project Name",
            "total_area": 20000.0
        }

        response = client.put(
            f"/api/v1/project/{project_data.id}",
            json=update_data,
            headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Project Name"
        assert data["total_area"] == 20000.0

    def test_update_project_not_found(self, client, admin_user_headers):
        """测试更新不存在的项目"""
        update_data = {"name": "Updated Name"}

        response = client.put(
            "/api/v1/project/non-existent-id",
            json=update_data,
            headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


# ============================================================================
# Search Projects Tests
# ============================================================================

class TestSearchProjects:
    """测试搜索项目API"""

    def test_search_projects_by_keyword(self, client, admin_user_headers, project_data):
        """测试关键词搜索"""
        search_params = {
            "keyword": project_data.name,
            "page": 1,
            "page_size": 10
        }

        response = client.post(
            "/api/v1/project/search",
            json=search_params,
            headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data

    def test_search_projects_empty_result(self, client, admin_user_headers):
        """测试搜索无结果"""
        search_params = {
            "keyword": "NonExistentProjectNameXYZ",
            "page": 1,
            "page_size": 10
        }

        response = client.post(
            "/api/v1/project/search",
            json=search_params,
            headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 0

    def test_list_projects_with_city_filter(self, client, admin_user_headers, project_data):
        """测试按城市筛选"""
        response = client.get(
            f"/api/v1/project/?city={project_data.city}",
            headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # 验证结果包含该城市的项目
        assert all(item.get("city") == project_data.city for item in data["items"])

    def test_list_projects_with_type_filter(self, client, admin_user_headers):
        """测试按项目类型筛选"""
        response = client.get(
            "/api/v1/project/?project_type=commercial",
            headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # 验证结果包含该类型的项目
        assert all(item.get("project_type") == "commercial" for item in data["items"])

    def test_list_projects_with_status_filter(self, client, admin_user_headers):
        """测试按项目状态筛选"""
        response = client.get(
            "/api/v1/project/?project_status=planning",
            headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # 验证结果包含该状态的项目
        assert all(item.get("project_status") == "planning" for item in data["items"])

    def test_list_projects_sort_by_area(self, client, admin_user_headers):
        """测试按面积排序"""
        response = client.get(
            "/api/v1/project/?sort_by=total_area&sort_order=desc",
            headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # 验证结果按总面积降序排列
        areas = [item.get("total_area", 0) for item in data["items"]]
        assert areas == sorted(areas, reverse=True)

    def test_create_project_with_minimal_data(self, client, admin_user_headers):
        """测试使用最小数据创建项目"""
        minimal_data = {
            "name": "Minimal Project",
            "code": "MIN-001",
            "city": "Shenzhen"
        }

        response = client.post(
            "/api/v1/project/",
            json=minimal_data,
            headers=admin_user_headers
        )

        # 应该成功或返回422（如果缺少必填字段）
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_422_UNPROCESSABLE_ENTITY]

    def test_update_project_partial_fields(self, client, admin_user_headers, project_data):
        """测试部分字段更新"""
        partial_update = {
            "district": "Updated District"
        }

        response = client.put(
            f"/api/v1/project/{project_data.id}",
            json=partial_update,
            headers=admin_user_headers
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
            "/api/v1/project/?page=9999&page_size=10",
            headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # 应该返回空结果或最后一页
        assert "items" in data

    def test_create_project_with_unicode(self, client, admin_user_headers):
        """测试创建包含Unicode字符的项目"""
        unicode_data = {
            "name": "测试项目名称",
            "code": "UNI-001",
            "city": "北京",
            "district": "朝阳区",
            "address": "北京市朝阳区测试地址123号"
        }

        response = client.post(
            "/api/v1/project/",
            json=unicode_data,
            headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "测试项目名称"
        assert data["city"] == "北京"

    def test_update_project_with_invalid_area(self, client, admin_user_headers, project_data):
        """测试使用无效面积更新项目"""
        invalid_update = {
            "total_area": -100.0  # 负面积
        }

        response = client.put(
            f"/api/v1/project/{project_data.id}",
            json=invalid_update,
            headers=admin_user_headers
        )

        # 应该拒绝或返回验证错误
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY]

    def test_delete_project_success(self, client, admin_user_headers, db: Session):
        """测试成功删除项目"""
        from src.schemas.project import ProjectCreate
        from src.crud.project import project_crud

        # 创建一个待删除的项目
        project = project_crud.create(
            db,
            obj_in=ProjectCreate(
                name="To Be Deleted",
                code="DEL-001",
                city="Test City"
            )
        )

        response = client.delete(
            f"/api/v1/project/{project.id}",
            headers=admin_user_headers
        )

        # 验证删除成功
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_204_NO_CONTENT]

        # 验证项目已被删除
        get_response = client.get(
            f"/api/v1/project/{project.id}",
            headers=admin_user_headers
        )
        assert get_response.status_code == status.HTTP_404_NOT_FOUND
