"""
ProjectService 集成测试 (简化版)
只测试核心功能，避免复杂字段问题
"""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.crud.project import project_crud
from src.models.party import Party, PartyType
from src.models.project import Project
from src.schemas.project import ProjectCreate, ProjectUpdate
from src.services.project.service import ProjectService

pytestmark = pytest.mark.asyncio


@pytest.fixture
def project_service() -> ProjectService:
    """ProjectService实例"""
    return ProjectService()


class TestProjectBasic:
    """项目基础功能测试"""

    @pytest.fixture(autouse=True)
    async def setup(self, db_session: AsyncSession, project_service: ProjectService):
        self.db = db_session
        self.service = project_service
        manager_party = Party(
            party_type=PartyType.ORGANIZATION.value,
            name="Project Service Test Manager",
            code="PJT-SVC-MANAGER",
            external_ref="PJT-SVC-MANAGER",
            status="active",
        )
        self.db.add(manager_party)
        await self.db.flush()
        self.manager_party_id = manager_party.id

    async def test_create_and_get_project(self):
        """测试创建和获取项目"""
        # 创建项目
        project_data = ProjectCreate(
            project_name="测试项目",
            project_code="PRJ-TEST01-240001",
            status="planning",
            manager_party_id=self.manager_party_id,
        )
        project = await self.service.create_project(self.db, obj_in=project_data)

        assert project.id is not None
        assert project.project_name == "测试项目"
        assert project.project_code == "PRJ-TEST01-240001"

        # 获取项目
        retrieved = await project_crud.get(self.db, project.id)
        assert retrieved is not None
        assert retrieved.project_name == "测试项目"

    async def test_update_project(self):
        """测试更新项目"""
        # 先创建项目
        project = await self.service.create_project(
            self.db,
            obj_in=ProjectCreate(
                project_name="原始项目",
                project_code="PRJ-TEST02-240002",
                status="planning",
                manager_party_id=self.manager_party_id,
            ),
        )

        # 更新项目
        update_data = ProjectUpdate(project_name="更新后的项目", status="active")
        updated = await self.service.update_project(
            self.db, project_id=project.id, obj_in=update_data
        )

        assert updated.project_name == "更新后的项目"
        assert updated.status == "active"

    async def test_toggle_status(self):
        """测试切换状态"""
        project = await self.service.create_project(
            self.db,
            obj_in=ProjectCreate(
                project_name="状态测试项目",
                project_code="PRJ-TEST03-240003",
                status="planning",
                manager_party_id=self.manager_party_id,
            ),
        )

        # 从规划中切换到暂停
        toggled = await self.service.toggle_status(self.db, project_id=project.id)
        assert toggled.status == "paused"

    async def test_delete_project(self):
        """测试删除项目"""
        project = await self.service.create_project(
            self.db,
            obj_in=ProjectCreate(
                project_name="待删除项目",
                project_code="PRJ-TEST04-240004",
                status="planning",
                manager_party_id=self.manager_party_id,
            ),
        )
        project_id = project.id

        # 删除项目
        await self.service.delete_project(self.db, project_id=project_id)

        # 验证已删除
        result = await self.db.execute(select(Project).where(Project.id == project_id))
        deleted = result.scalars().first()
        assert deleted is None
