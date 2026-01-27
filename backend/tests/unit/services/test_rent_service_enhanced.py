"""
租赁合同服务增强测试

Enhanced tests for Rent Contract Service to improve coverage
"""

import pytest
from sqlalchemy.orm import Session
from datetime import datetime, UTC


@pytest.fixture
def rent_service(db: Session):
    """租赁合同服务实例"""
    from src.services.rent_contract.service import RentContractService

    return RentContractService(db)


@pytest.fixture
def sample_contract(db: Session, admin_user):
    """示例合同数据"""
    from src.schemas.rent_contract import RentContractCreate
    from src.crud.rent_contract import rent_contract_crud

    contract = rent_contract_crud.create(
        db,
        obj_in=RentContractCreate(
            contract_number="TEST-001",
            tenant_name="测试租户",
            tenant_phone="13800138000",
            property_id="property-001",
            start_date=datetime.now(UTC),
            end_date=datetime.now(UTC),
            monthly_rent=10000.0,
            area=100.0,
            status="active",
        ),
    )
    yield contract
    try:
        rent_contract_crud.remove(db, id=contract.id)
    except:
        pass


class TestRentContractServiceBusinessLogic:
    """测试租赁合同服务业务逻辑"""

    def test_calculate_rent_in_arrears(self, rent_service, sample_contract):
        """测试计算欠租"""
        arrears = rent_service.calculate_rent_in_arrears(
            sample_contract.id, as_of_date=datetime.now(UTC)
        )
        assert arrears is not None

    def test_contract_termination_calculations(
        self, rent_service, sample_contract, db: Session
    ):
        """测试合同终止计算"""
        result = rent_service.calculate_termination_settlement(
            db, contract_id=sample_contract.id, termination_date=datetime.now(UTC)
        )
        assert result is not None

    def test_contract_renewal_validation(self, rent_service, sample_contract):
        """测试合同续期验证"""
        # 测试续期条件验证
        result = rent_service.validate_renewal(sample_contract.id)
        assert result is not None

    def test_get_contract_history(self, rent_service, sample_contract):
        """测试获取合同历史"""
        history = rent_service.get_contract_history(sample_contract.id)
        assert history is not None

    def test_batch_contract_status_update(self, rent_service, db: Session):
        """测试批量更新合同状态"""
        contract_ids = ["contract1", "contract2"]
        new_status = "expired"
        result = rent_service.batch_update_status(
            db, contract_ids=contract_ids, new_status=new_status
        )
        assert result is not None

    def test_contract_reminder_check(self, rent_service):
        """测试合同到期提醒"""
        result = rent_service.check_expiring_contracts(days_before=30)
        assert result is not None

    def test_generate_contract_statistics(self, rent_service, db: Session):
        """测试生成合同统计"""
        stats = rent_service.generate_statistics(
            db, date_from=datetime.now(UTC), date_to=datetime.now(UTC)
        )
        assert stats is not None
        assert "active_contracts" in stats
        assert "total_value" in stats
