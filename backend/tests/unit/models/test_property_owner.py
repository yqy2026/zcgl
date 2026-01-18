"""
Unit tests for PropertyOwner model
"""

import pytest

from src.models.organization import Organization
from src.models.property_certificate import OwnerType, PropertyOwner


@pytest.fixture
def test_organization(db_session):
    """Create a test organization for PropertyOwner tests"""
    org = Organization(
        name="Test Organization",
        code="TEST001",
        type="department",
        status="active",
        level=1
    )
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    return org


def test_create_property_owner(db_session):
    """测试创建权利人"""
    owner = PropertyOwner(
        owner_type=OwnerType.INDIVIDUAL,
        name="张三",
        id_type="身份证",
        id_number="110101199001011234"
    )
    db_session.add(owner)
    db_session.commit()

    assert owner.id is not None
    assert owner.name == "张三"
    assert owner.owner_type == OwnerType.INDIVIDUAL


def test_property_owner_organization_linkage(db_session, test_organization):
    """测试权利人关联组织"""
    owner = PropertyOwner(
        owner_type=OwnerType.ORGANIZATION,
        name="某公司",
        organization_id=test_organization.id
    )
    db_session.add(owner)
    db_session.commit()

    assert owner.organization_id == test_organization.id
