"""
Project CRUD tenant-scope integration tests with real database rows.
"""

import uuid

import pytest
from sqlalchemy.orm import Session

from src.crud.project import project_crud
from src.crud.query_builder import PartyFilter
from src.models.organization import Organization
from src.models.project import Project
from tests.integration.conftest import AsyncSessionAdapter


def _build_code(prefix: str) -> str:
    return f"PJ{prefix}{uuid.uuid4().int % 10000:04d}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_project_get_multi_respects_tenant_filter(db_session: Session):
    """真实数据验证 party_filter 只返回目标组织项目。"""
    project_crud.clear_cache()
    async_db = AsyncSessionAdapter(db_session)

    org_a = Organization(
        name=f"Tenant Scope Org A-{uuid.uuid4().hex[:6]}",
        code=f"TEN-A-{uuid.uuid4().hex[:6]}",
        level=1,
        type="department",
        status="active",
    )
    org_b = Organization(
        name=f"Tenant Scope Org B-{uuid.uuid4().hex[:6]}",
        code=f"TEN-B-{uuid.uuid4().hex[:6]}",
        level=1,
        type="department",
        status="active",
    )
    db_session.add_all([org_a, org_b])
    db_session.flush()

    project_a = Project(
        name=f"Tenant Scoped Project A-{uuid.uuid4().hex[:6]}",
        code=_build_code("26"),
        organization_id=org_a.id,
        project_status="active",
    )
    project_b = Project(
        name=f"Tenant Scoped Project B-{uuid.uuid4().hex[:6]}",
        code=_build_code("27"),
        organization_id=org_b.id,
        project_status="active",
    )
    db_session.add_all([project_a, project_b])
    db_session.flush()

    org_a_projects = await project_crud.get_multi(
        async_db,
        skip=0,
        limit=50,
        party_filter=PartyFilter(party_ids=[org_a.id]),
    )
    org_a_ids = {project.id for project in org_a_projects}
    assert project_a.id in org_a_ids
    assert project_b.id not in org_a_ids

    org_b_projects = await project_crud.get_multi(
        async_db,
        skip=0,
        limit=50,
        party_filter=PartyFilter(party_ids=[org_b.id]),
    )
    org_b_ids = {project.id for project in org_b_projects}
    assert project_b.id in org_b_ids
    assert project_a.id not in org_b_ids


@pytest.mark.integration
@pytest.mark.asyncio
async def test_project_get_multi_fail_closed_when_tenant_filter_empty(
    db_session: Session,
):
    """真实数据验证空组织列表时 fail-closed。"""
    project_crud.clear_cache()
    async_db = AsyncSessionAdapter(db_session)

    projects = await project_crud.get_multi(
        async_db,
        skip=0,
        limit=20,
        party_filter=PartyFilter(party_ids=[]),
    )
    assert projects == []
