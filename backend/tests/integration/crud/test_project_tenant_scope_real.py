"""
Project CRUD tenant-scope integration tests with real database rows.
"""

import uuid

import pytest
from sqlalchemy.orm import Session

from src.crud.project import project_crud
from src.crud.query_builder import PartyFilter
from src.models.organization import Organization
from src.models.party import Party, PartyType
from src.models.project import Project
from tests.integration.conftest import AsyncSessionAdapter


def _build_code(prefix: str) -> str:
    serial = f"{uuid.uuid4().int % 1000000:06d}"
    return f"PRJ-{prefix.upper()}-{serial}"


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

    party_a = Party(
        party_type=PartyType.ORGANIZATION.value,
        name=f"Tenant Scope Party A-{uuid.uuid4().hex[:6]}",
        code=f"TEN-PARTY-A-{uuid.uuid4().hex[:6]}",
        external_ref=org_a.id,
        status="active",
    )
    party_b = Party(
        party_type=PartyType.ORGANIZATION.value,
        name=f"Tenant Scope Party B-{uuid.uuid4().hex[:6]}",
        code=f"TEN-PARTY-B-{uuid.uuid4().hex[:6]}",
        external_ref=org_b.id,
        status="active",
    )
    db_session.add_all([party_a, party_b])
    db_session.flush()

    project_a = Project(
        project_name=f"Tenant Scoped Project A-{uuid.uuid4().hex[:6]}",
        project_code=_build_code("TENA01"),
        manager_party_id=party_a.id,
        status="active",
    )
    project_b = Project(
        project_name=f"Tenant Scoped Project B-{uuid.uuid4().hex[:6]}",
        project_code=_build_code("TENB01"),
        manager_party_id=party_b.id,
        status="active",
    )
    db_session.add_all([project_a, project_b])
    db_session.flush()

    org_a_projects = await project_crud.get_multi(
        async_db,
        skip=0,
        limit=50,
        party_filter=PartyFilter(party_ids=[party_a.id]),
    )
    org_a_ids = {project.id for project in org_a_projects}
    assert project_a.id in org_a_ids
    assert project_b.id not in org_a_ids

    org_b_projects = await project_crud.get_multi(
        async_db,
        skip=0,
        limit=50,
        party_filter=PartyFilter(party_ids=[party_b.id]),
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
