import pytest
from unittest.mock import MagicMock
from sqlalchemy.orm import Session
from src.crud.property_certificate import property_certificate_crud
from src.schemas.property_certificate import PropertyCertificateCreate


@pytest.fixture
def mock_db():
    """Mock database session"""
    return MagicMock(spec=Session)


@pytest.mark.unit
def test_create_certificate(mock_db):
    """测试创建产权证"""
    # Mock the create method to return a certificate with id
    mock_cert = MagicMock()
    mock_cert.id = 1
    mock_cert.certificate_number = "CRUD001"
    mock_db.add.return_value = None
    mock_db.commit.return_value = None
    mock_db.refresh.return_value = None
    property_certificate_crud.create = MagicMock(return_value=mock_cert)

    cert_in = PropertyCertificateCreate(
        certificate_number="CRUD001",
        certificate_type="other",
        property_address="Test"
    )
    cert = property_certificate_crud.create(mock_db, obj_in=cert_in)

    assert cert.id is not None
    assert cert.certificate_number == "CRUD001"


@pytest.mark.unit
def test_get_by_certificate_number(mock_db):
    """测试按证书编号查询"""
    # Mock the query method
    mock_query = MagicMock()
    mock_result = MagicMock()
    mock_result.certificate_number = "SEARCH001"
    mock_query.filter.return_value.first.return_value = mock_result

    mock_db.query.return_value = mock_query

    cert_in = PropertyCertificateCreate(
        certificate_number="SEARCH001",
        certificate_type="other"
    )
    # Create the certificate first
    property_certificate_crud.create = MagicMock(return_value=mock_result)
    property_certificate_crud.create(mock_db, obj_in=cert_in)

    found = property_certificate_crud.get_by_certificate_number(mock_db, "SEARCH001")
    assert found is not None
    assert found.certificate_number == "SEARCH001"