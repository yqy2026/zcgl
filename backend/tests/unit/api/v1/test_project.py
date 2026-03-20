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

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import status
from sqlalchemy.orm import Session

from src.core.exception_handler import ResourceNotFoundError

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
def test_org_party(db_session: Session, test_organization):
    """创建与组织映射的 Party 数据（Phase4 必需）。"""
    from sqlalchemy import select

    from src.models.party import Party, PartyType

    party_stmt = select(Party).where(
        Party.party_type == PartyType.ORGANIZATION.value,
        Party.external_ref == test_organization.id,
    )
    party = db_session.execute(party_stmt).scalar_one_or_none()
    if party is None:
        party = Party(
            party_type=PartyType.ORGANIZATION.value,
            name=f"Unit Test Party {test_organization.name}",
            code="PARTY-UNIT-TEST-001",
            external_ref=test_organization.id,
            status="active",
        )
        db_session.add(party)
        db_session.flush()
    db_session.refresh(party)
    return party


@pytest.fixture
def project_data(db_session: Session, test_organization, test_org_party):
    """创建测试项目数据"""
    from src.models.project import Project

    project = Project(
        project_name="Test Project",
        project_code="PRJ-TEST09-000001",
        status="planning",
        manager_party_id=test_org_party.id,
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
def admin_user_headers(client, admin_user, test_organization, test_org_party, monkeypatch):
    """管理员用户认证头"""
    from src.api.v1.assets import project as project_module
    from src.main import app
    from src.services.organization_permission_service import (
        OrganizationPermissionService,
    )
    from src.services.project.service import ProjectService

    def mock_get_current_user():
        return admin_user

    async def mock_get_user_accessible_organizations(self, user_id: str):
        return [test_organization.id]

    async def mock_resolve_party_filter(
        self,
        db,
        *,
        current_user_id=None,
        party_filter=None,
    ):
        return None

    admin_user.default_organization_id = test_organization.id
    monkeypatch.setattr(
        OrganizationPermissionService,
        "get_user_accessible_organizations",
        mock_get_user_accessible_organizations,
    )
    monkeypatch.setattr(
        ProjectService,
        "_resolve_party_filter",
        mock_resolve_party_filter,
    )
    monkeypatch.setattr(
        project_module.authz_service,
        "check_access",
        AsyncMock(
            return_value=MagicMock(
                allowed=True,
                reason_code="allow",
            )
        ),
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
            "project_name": "New Test Project",
            "status": "active",
        }

        response = client.post(
            "/api/v1/projects/", json=project_data, headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["project_name"] == "New Test Project"
        assert "id" in data

    def test_create_project_unauthorized(self, unauthenticated_client):
        """测试未授权创建项目"""
        project_data = {"project_name": "Unauthorized Project"}

        response = unauthenticated_client.post("/api/v1/projects/", json=project_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_project_duplicate_code(
        self, client, admin_user_headers, project_data
    ):
        """测试创建重复代码的项目"""
        duplicate_data = {
            "project_name": "Duplicate Project",
            "project_code": project_data.project_code,
        }

        response = client.post(
            "/api/v1/projects/", json=duplicate_data, headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_409_CONFLICT

    def test_create_project_invalid_data(self, client, admin_user_headers):
        """测试创建项目时数据验证失败"""
        invalid_data = {
            "project_name": "",
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
            f"/api/v1/projects/?keyword={project_data.project_name}", headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        items = data["data"]["items"]
        # 验证搜索结果包含测试项目
        assert any(item["project_name"] == project_data.project_name for item in items)

    def test_list_projects_unauthorized(self, unauthenticated_client):
        """测试未授权访问"""
        response = unauthenticated_client.get("/api/v1/projects/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_projects_passes_owner_party_id_filter(
        self,
        client,
        admin_user_headers,
        monkeypatch,
    ):
        """应将 owner_party_id 查询参数透传到服务层搜索参数。"""
        from src.api.v1.assets import project as project_module

        captured: dict[str, object] = {}

        async def mock_search_projects(
            *,
            db,
            search_params,
            current_user_id: str | None = None,
            party_filter=None,
        ):
            _ = db
            _ = current_user_id
            _ = party_filter
            captured["owner_party_id"] = getattr(search_params, "owner_party_id", None)
            return {
                "items": [],
                "total": 0,
                "page": search_params.page,
                "page_size": search_params.page_size,
                "pages": 0,
            }

        monkeypatch.setattr(
            project_module.project_service,
            "search_projects",
            mock_search_projects,
        )

        response = client.get(
            "/api/v1/projects/?owner_party_id=party-filter-001",
            headers=admin_user_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert captured["owner_party_id"] == "party-filter-001"

    def test_list_projects_owner_party_filter_should_limit_results(
        self,
        client,
        admin_user_headers,
        db_session: Session,
        test_org_party,
    ):
        """owner_party_id 应只返回匹配关系且为有效关系的项目。"""
        from src.models.ownership import Ownership
        from src.models.project import Project
        from src.models.project_relations import ProjectOwnershipRelation

        owner_match = Ownership(
            name="Filter Owner Match",
            code="OWN-FILTER-MATCH",
            is_active=True,
        )
        owner_other = Ownership(
            name="Filter Owner Other",
            code="OWN-FILTER-OTHER",
            is_active=True,
        )
        db_session.add_all([owner_match, owner_other])
        db_session.flush()

        project_match = Project(
            project_name="Owner Filter Match Project",
            project_code="PRJ-TEST09-900001",
            status="planning",
            manager_party_id=test_org_party.id,
        )
        project_other = Project(
            project_name="Owner Filter Other Project",
            project_code="PRJ-TEST09-900002",
            status="planning",
            manager_party_id=test_org_party.id,
        )
        db_session.add_all([project_match, project_other])
        db_session.flush()

        db_session.add_all(
            [
                ProjectOwnershipRelation(
                    project_id=project_match.id,
                    ownership_id=owner_match.id,
                    is_active=True,
                ),
                ProjectOwnershipRelation(
                    project_id=project_other.id,
                    ownership_id=owner_match.id,
                    is_active=False,
                ),
                ProjectOwnershipRelation(
                    project_id=project_other.id,
                    ownership_id=owner_other.id,
                    is_active=True,
                ),
            ]
        )
        db_session.flush()

        response = client.get(
            f"/api/v1/projects/?owner_party_id={owner_match.id}&page=1&page_size=100",
            headers=admin_user_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        items = response.json()["data"]["items"]
        returned_ids = {item["id"] for item in items}
        assert project_match.id in returned_ids
        assert project_other.id not in returned_ids

    def test_list_projects_owner_party_filter_should_support_party_id_mapping(
        self,
        client,
        admin_user_headers,
        db_session: Session,
        test_org_party,
    ):
        """owner_party_id 传 Party.id 时，应通过 external_ref 映射到 ownership_id 过滤。"""
        from uuid import uuid4

        from src.models.ownership import Ownership
        from src.models.party import Party, PartyType
        from src.models.project import Project
        from src.models.project_relations import ProjectOwnershipRelation

        suffix = uuid4().hex[:6].upper()
        ownership = Ownership(
            name="Mapped Ownership",
            code=f"OWN-MAPPED-{suffix}",
            is_active=True,
        )
        other_ownership = Ownership(
            name="Mapped Ownership Other",
            code=f"OWN-OTHER-{suffix}",
            is_active=True,
        )
        db_session.add_all([ownership, other_ownership])
        db_session.flush()
        ownership_serial_seed = ownership.id.replace("-", "")[-8:]
        project_serial = f"{int(ownership_serial_seed, 16) % 1_000_000:06d}"

        mapped_party = Party(
            id=f"party-map-{ownership.id}",
            party_type=PartyType.LEGAL_ENTITY.value,
            name=ownership.name,
            code=f"PARTY-{ownership.id}",
            external_ref=ownership.id,
            status="active",
        )
        db_session.add(mapped_party)
        db_session.flush()
        assert mapped_party.id != ownership.id

        mapped_project = Project(
            project_name="Mapped Party Project",
            project_code=f"PRJ-MAPPED01-{project_serial}",
            status="planning",
            manager_party_id=test_org_party.id,
        )
        other_project = Project(
            project_name="Mapped Party Other Project",
            project_code=f"PRJ-MAPPED02-{project_serial}",
            status="planning",
            manager_party_id=test_org_party.id,
        )
        db_session.add_all([mapped_project, other_project])
        db_session.flush()

        db_session.add(
            ProjectOwnershipRelation(
                project_id=mapped_project.id,
                ownership_id=ownership.id,
                is_active=True,
            )
        )
        db_session.add(
            ProjectOwnershipRelation(
                project_id=other_project.id,
                ownership_id=other_ownership.id,
                is_active=True,
            )
        )
        db_session.flush()

        response = client.get(
            f"/api/v1/projects/?owner_party_id={mapped_party.id}&page=1&page_size=100",
            headers=admin_user_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        items = response.json()["data"]["items"]
        returned_ids = {item["id"] for item in items}
        assert mapped_project.id in returned_ids
        assert other_project.id not in returned_ids

    def test_list_projects_owner_party_filter_should_work_with_status_filter(
        self,
        client,
        admin_user_headers,
        db_session: Session,
        test_org_party,
    ):
        """GET 列表 owner_party_id + status 组合筛选应取交集。"""
        from uuid import uuid4

        from src.models.ownership import Ownership
        from src.models.party import Party, PartyType
        from src.models.project import Project
        from src.models.project_relations import ProjectOwnershipRelation

        suffix = uuid4().hex[:6].upper()
        ownership = Ownership(
            name="List Combo Ownership",
            code=f"OWN-LCMB-{suffix}",
            is_active=True,
        )
        db_session.add(ownership)
        db_session.flush()

        mapped_party = Party(
            id=f"party-list-combo-{ownership.id}",
            party_type=PartyType.LEGAL_ENTITY.value,
            name=ownership.name,
            code=f"PARTY-LCMB-{ownership.id}",
            external_ref=ownership.id,
            status="active",
        )
        db_session.add(mapped_party)
        db_session.flush()

        serial_seed = ownership.id.replace("-", "")[-8:]
        project_serial = f"{int(serial_seed, 16) % 1_000_000:06d}"
        active_project = Project(
            project_name="List Combo Active Project",
            project_code=f"PRJ-LCMB01-{project_serial}",
            status="active",
            manager_party_id=test_org_party.id,
        )
        planning_project = Project(
            project_name="List Combo Planning Project",
            project_code=f"PRJ-LCMB02-{project_serial}",
            status="planning",
            manager_party_id=test_org_party.id,
        )
        db_session.add_all([active_project, planning_project])
        db_session.flush()

        db_session.add_all(
            [
                ProjectOwnershipRelation(
                    project_id=active_project.id,
                    ownership_id=ownership.id,
                    is_active=True,
                ),
                ProjectOwnershipRelation(
                    project_id=planning_project.id,
                    ownership_id=ownership.id,
                    is_active=True,
                ),
            ]
        )
        db_session.flush()

        response = client.get(
            f"/api/v1/projects/?owner_party_id={mapped_party.id}&status=active&page=1&page_size=100",
            headers=admin_user_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        items = response.json()["data"]["items"]
        returned_ids = {item["id"] for item in items}
        assert active_project.id in returned_ids
        assert planning_project.id not in returned_ids

    def test_list_projects_owner_party_filter_invalid_value_should_return_empty(
        self,
        client,
        admin_user_headers,
    ):
        """非法 owner_party_id 字符串应返回空列表，不应误放行。"""
        response = client.get(
            "/api/v1/projects/?owner_party_id=%25%25%25invalid%%%25&page=1&page_size=100",
            headers=admin_user_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        items = response.json()["data"]["items"]
        assert items == []

    def test_list_projects_owner_party_filter_pagination_should_be_consistent(
        self,
        client,
        admin_user_headers,
        db_session: Session,
        test_org_party,
    ):
        """owner_party_id 过滤下分页 total/page/items 应保持一致。"""
        from uuid import uuid4

        from src.models.ownership import Ownership
        from src.models.party import Party, PartyType
        from src.models.project import Project
        from src.models.project_relations import ProjectOwnershipRelation

        suffix = uuid4().hex[:6].upper()
        ownership = Ownership(
            name="List Page Ownership",
            code=f"OWN-LPG-{suffix}",
            is_active=True,
        )
        db_session.add(ownership)
        db_session.flush()

        mapped_party = Party(
            id=f"party-list-page-{ownership.id}",
            party_type=PartyType.LEGAL_ENTITY.value,
            name=ownership.name,
            code=f"PARTY-LPG-{ownership.id}",
            external_ref=ownership.id,
            status="active",
        )
        db_session.add(mapped_party)
        db_session.flush()

        created_project_ids: list[str] = []
        for index in range(12):
            project = Project(
                project_name=f"List Page Project {index}",
                project_code=f"PRJ-LPG{index:03d}-{index:06d}",
                status="active",
                manager_party_id=test_org_party.id,
            )
            db_session.add(project)
            db_session.flush()
            created_project_ids.append(project.id)
            db_session.add(
                ProjectOwnershipRelation(
                    project_id=project.id,
                    ownership_id=ownership.id,
                    is_active=True,
                )
            )
        db_session.flush()

        response = client.get(
            f"/api/v1/projects/?owner_party_id={mapped_party.id}&page=2&page_size=5",
            headers=admin_user_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()["data"]
        items = payload["items"]
        pagination = payload["pagination"]

        returned_ids = {item["id"] for item in items}
        assert pagination["total"] == 12
        assert pagination["page"] == 2
        assert pagination["page_size"] == 5
        assert len(items) == 5
        assert returned_ids.issubset(set(created_project_ids))


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
        assert data["project_name"] == project_data.project_name

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
        update_data = {"project_name": "Updated Project Name"}

        response = client.put(
            f"/api/v1/projects/{project_data.id}",
            json=update_data,
            headers=admin_user_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["project_name"] == "Updated Project Name"

    def test_update_project_not_found(self, client, admin_user_headers):
        """测试更新不存在的项目"""
        update_data = {"project_name": "Updated Name"}

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
        search_params = {"keyword": project_data.project_name, "page": 1, "page_size": 10}

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

    def test_search_projects_owner_party_filter_should_support_party_id_mapping(
        self,
        client,
        admin_user_headers,
        db_session: Session,
        test_org_party,
    ):
        """POST /search 的 owner_party_id 也应支持 Party.external_ref -> ownership_id 映射。"""
        from uuid import uuid4

        from src.models.ownership import Ownership
        from src.models.party import Party, PartyType
        from src.models.project import Project
        from src.models.project_relations import ProjectOwnershipRelation

        suffix = uuid4().hex[:6].upper()
        ownership = Ownership(
            name="Search Mapped Ownership",
            code=f"OWN-SRCH-{suffix}",
            is_active=True,
        )
        other_ownership = Ownership(
            name="Search Mapped Ownership Other",
            code=f"OWN-SRCH-OTHER-{suffix}",
            is_active=True,
        )
        db_session.add_all([ownership, other_ownership])
        db_session.flush()

        ownership_serial_seed = ownership.id.replace("-", "")[-8:]
        project_serial = f"{int(ownership_serial_seed, 16) % 1_000_000:06d}"

        mapped_party = Party(
            id=f"party-search-map-{ownership.id}",
            party_type=PartyType.LEGAL_ENTITY.value,
            name=ownership.name,
            code=f"PARTY-SRCH-{ownership.id}",
            external_ref=ownership.id,
            status="active",
        )
        db_session.add(mapped_party)
        db_session.flush()
        assert mapped_party.id != ownership.id

        mapped_project = Project(
            project_name="Search Mapped Party Project",
            project_code=f"PRJ-SRCH01-{project_serial}",
            status="planning",
            manager_party_id=test_org_party.id,
        )
        other_project = Project(
            project_name="Search Mapped Party Other Project",
            project_code=f"PRJ-SRCH02-{project_serial}",
            status="planning",
            manager_party_id=test_org_party.id,
        )
        db_session.add_all([mapped_project, other_project])
        db_session.flush()

        db_session.add_all(
            [
                ProjectOwnershipRelation(
                    project_id=mapped_project.id,
                    ownership_id=ownership.id,
                    is_active=True,
                ),
                ProjectOwnershipRelation(
                    project_id=other_project.id,
                    ownership_id=other_ownership.id,
                    is_active=True,
                ),
            ]
        )
        db_session.flush()

        response = client.post(
            "/api/v1/projects/search",
            json={
                "owner_party_id": mapped_party.id,
                "page": 1,
                "page_size": 100,
            },
            headers=admin_user_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        items = response.json()["data"]["items"]
        returned_ids = {item["id"] for item in items}
        assert mapped_project.id in returned_ids
        assert other_project.id not in returned_ids

    def test_search_projects_owner_party_filter_blank_should_fail_closed(
        self,
        client,
        admin_user_headers,
    ):
        """owner_party_id 为空白字符串时应 fail-closed 返回空列表。"""
        response = client.post(
            "/api/v1/projects/search",
            json={
                "owner_party_id": "   ",
                "page": 1,
                "page_size": 100,
            },
            headers=admin_user_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        items = response.json()["data"]["items"]
        assert items == []

    def test_search_projects_owner_party_filter_without_mapping_should_return_empty(
        self,
        client,
        admin_user_headers,
    ):
        """owner_party_id 无直接命中且无 external_ref 映射时应返回空列表。"""
        response = client.post(
            "/api/v1/projects/search",
            json={
                "owner_party_id": "party-nonexistent-no-mapping",
                "page": 1,
                "page_size": 100,
            },
            headers=admin_user_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        items = response.json()["data"]["items"]
        assert items == []

    def test_search_projects_owner_party_filter_should_work_with_status_filter(
        self,
        client,
        admin_user_headers,
        db_session: Session,
        test_org_party,
    ):
        """owner_party_id + status 组合筛选应取交集。"""
        from uuid import uuid4

        from src.models.ownership import Ownership
        from src.models.party import Party, PartyType
        from src.models.project import Project
        from src.models.project_relations import ProjectOwnershipRelation

        suffix = uuid4().hex[:6].upper()
        ownership = Ownership(
            name="Search Combo Ownership",
            code=f"OWN-COMBO-{suffix}",
            is_active=True,
        )
        db_session.add(ownership)
        db_session.flush()

        serial_seed = ownership.id.replace("-", "")[-8:]
        project_serial = f"{int(serial_seed, 16) % 1_000_000:06d}"
        mapped_party = Party(
            id=f"party-combo-{ownership.id}",
            party_type=PartyType.LEGAL_ENTITY.value,
            name=ownership.name,
            code=f"PARTY-COMBO-{ownership.id}",
            external_ref=ownership.id,
            status="active",
        )
        db_session.add(mapped_party)
        db_session.flush()

        active_project = Project(
            project_name="Search Combo Active Project",
            project_code=f"PRJ-CMB01-{project_serial}",
            status="active",
            manager_party_id=test_org_party.id,
        )
        planning_project = Project(
            project_name="Search Combo Planning Project",
            project_code=f"PRJ-CMB02-{project_serial}",
            status="planning",
            manager_party_id=test_org_party.id,
        )
        db_session.add_all([active_project, planning_project])
        db_session.flush()

        db_session.add_all(
            [
                ProjectOwnershipRelation(
                    project_id=active_project.id,
                    ownership_id=ownership.id,
                    is_active=True,
                ),
                ProjectOwnershipRelation(
                    project_id=planning_project.id,
                    ownership_id=ownership.id,
                    is_active=True,
                ),
            ]
        )
        db_session.flush()

        response = client.post(
            "/api/v1/projects/search",
            json={
                "owner_party_id": mapped_party.id,
                "status": "active",
                "page": 1,
                "page_size": 100,
            },
            headers=admin_user_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        items = response.json()["data"]["items"]
        returned_ids = {item["id"] for item in items}
        assert active_project.id in returned_ids
        assert planning_project.id not in returned_ids

    def test_list_projects_with_city_filter(
        self, client, admin_user_headers, project_data
    ):
        """测试按状态筛选（原城市筛选测试 - city 字段已删除）"""
        response = client.get(
            "/api/v1/projects/?status=planning", headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        items = response.json()["data"]["items"]
        assert isinstance(items, list)

    def test_list_projects_with_type_filter(
        self, client, admin_user_headers, project_data
    ):
        """测试按关键词筛选（原类型筛选测试 - project_type 字段已删除）"""
        response = client.get(
            "/api/v1/projects/", headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        items = response.json()["data"]["items"]
        assert isinstance(items, list)

    def test_list_projects_with_status_filter(self, client, admin_user_headers):
        """测试按项目状态筛选"""
        response = client.get(
            "/api/v1/projects/?status=planning", headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        # 验证结果包含该状态的项目
        assert all(item.get("status") == "planning" for item in data["items"])

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
            "project_name": "Minimal Project",
        }

        response = client.post(
            "/api/v1/projects/", json=minimal_data, headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK

    def test_update_project_partial_fields(
        self, client, admin_user_headers, project_data
    ):
        """测试部分字段更新"""
        partial_update = {"project_name": "Updated Name"}

        response = client.put(
            f"/api/v1/projects/{project_data.id}",
            json=partial_update,
            headers=admin_user_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["project_name"] == "Updated Name"

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
            "project_name": "测试项目名称",
        }

        response = client.post(
            "/api/v1/projects/", json=unicode_data, headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["project_name"] == "测试项目名称"

    def test_update_project_with_invalid_code(
        self, client, admin_user_headers, project_data
    ):
        """测试使用无效编码更新项目"""
        invalid_update = {"project_code": "BAD-001"}

        response = client.put(
            f"/api/v1/projects/{project_data.id}",
            json=invalid_update,
            headers=admin_user_headers,
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_delete_project_success(
        self,
        client,
        admin_user_headers,
        db_session: Session,
        test_organization,
        test_org_party,
    ):
        """测试成功删除项目"""
        from src.models.project import Project

        # 创建一个待删除的项目
        project = Project(
            project_name="To Be Deleted",
            project_code="PRJ-TEST09-000007",
            manager_party_id=test_org_party.id,
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


class TestGetProjectActiveAssets:
    """测试项目有效关联资产端点。"""

    def test_get_project_assets_endpoint_returns_200(
        self,
        client,
        admin_user_headers,
        project_data,
        monkeypatch,
    ):
        """正常调用返回 200 + items/total/summary 结构。"""
        from src.api.v1.assets import project as project_module

        async def mock_get_project_active_assets(
            db,
            *,
            project_id: str,
            current_user_id: str | None = None,
            party_filter=None,
        ):
            assert project_id == project_data.id
            assert current_user_id is not None
            assets = [
                {
                    "id": "asset-1",
                    "asset_name": "Asset 1",
                    "asset_code": "AST-001",
                    "address": "测试地址1号",
                    "ownership_status": "已确权",
                    "property_nature": "经营性",
                    "usage_status": "出租",
                    "rentable_area": 100.0,
                    "rented_area": 80.0,
                    "data_status": "正常",
                    "review_status": "draft",
                    "created_at": "2026-03-01T00:00:00",
                    "updated_at": "2026-03-01T00:00:00",
                }
            ]
            summary = {
                "total_assets": 1,
                "total_rentable_area": 100.0,
                "total_rented_area": 80.0,
                "occupancy_rate": 80.0,
            }
            return assets, summary

        monkeypatch.setattr(
            project_module.project_service,
            "get_project_active_assets",
            mock_get_project_active_assets,
        )

        response = client.get(
            f"/api/v1/projects/{project_data.id}/assets",
            headers=admin_user_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert payload["success"] is True
        assert "data" in payload
        assert "items" in payload["data"]
        assert "total" in payload["data"]
        assert "summary" in payload["data"]
        assert payload["data"]["total"] == 1
        assert payload["data"]["summary"]["occupancy_rate"] == 80.0

    def test_get_project_assets_endpoint_not_found(
        self,
        client,
        admin_user_headers,
        monkeypatch,
    ):
        """项目不存在返回 404。"""
        from src.api.v1.assets import project as project_module

        async def mock_get_project_active_assets(
            db,
            *,
            project_id: str,
            current_user_id: str | None = None,
            party_filter=None,
        ):
            raise ResourceNotFoundError("项目", project_id)

        monkeypatch.setattr(
            project_module.project_service,
            "get_project_active_assets",
            mock_get_project_active_assets,
        )

        response = client.get(
            "/api/v1/projects/non-existent-id/assets",
            headers=admin_user_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestProjectStatistics:
    """测试项目统计端点。"""

    def test_get_project_statistics_returns_new_contract_fields(
        self,
        client,
        admin_user_headers,
        monkeypatch,
    ):
        """统计接口应返回 total_projects/active_projects 字段。"""
        from src.api.v1.assets import project as project_module

        async def mock_get_project_statistics(
            db,
            *,
            current_user_id: str | None = None,
            party_filter=None,
        ):
            assert current_user_id is not None
            return {
                "total_projects": 12,
                "active_projects": 7,
            }

        monkeypatch.setattr(
            project_module.project_service,
            "get_project_statistics",
            mock_get_project_statistics,
        )

        response = client.get(
            "/api/v1/projects/stats/overview",
            headers=admin_user_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert payload["total_projects"] == 12
        assert payload["active_projects"] == 7


class TestProjectDropdownOptions:
    """测试项目下拉选项端点。"""

    def test_get_project_dropdown_options_uses_status_filter(
        self,
        client,
        admin_user_headers,
        monkeypatch,
    ):
        """下拉选项接口应透传 status 参数并返回新契约字段。"""
        from src.api.v1.assets import project as project_module

        async def mock_get_project_dropdown_options(
            db,
            *,
            status: str | None = "active",
            current_user_id: str | None = None,
            party_filter=None,
        ):
            assert current_user_id is not None
            assert status == "paused"
            return [
                {
                    "id": "project-1",
                    "project_name": "暂停项目",
                    "project_code": "PRJ-TEST09-000011",
                }
            ]

        monkeypatch.setattr(
            project_module.project_service,
            "get_project_dropdown_options",
            mock_get_project_dropdown_options,
        )

        response = client.get(
            "/api/v1/projects/dropdown-options?status=paused",
            headers=admin_user_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert isinstance(payload, list)
        assert payload[0] == {
            "id": "project-1",
            "project_name": "暂停项目",
            "project_code": "PRJ-TEST09-000011",
        }
