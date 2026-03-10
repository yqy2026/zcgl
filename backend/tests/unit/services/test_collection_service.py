"""
催缴管理功能单元测试
"""

from datetime import date, timedelta
from decimal import Decimal


class TestCollectionEnums:
    """测试催缴相关枚举"""

    def test_collection_method_enum(self):
        """TC-COL-001: 催缴方式枚举正确"""
        from src.models.collection import CollectionMethod

        assert CollectionMethod.PHONE.value == "phone"
        assert CollectionMethod.SMS.value == "sms"
        assert CollectionMethod.EMAIL.value == "email"
        assert CollectionMethod.WECOM.value == "wecom"
        assert CollectionMethod.VISIT.value == "visit"
        assert CollectionMethod.LETTER.value == "letter"
        assert CollectionMethod.OTHER.value == "other"

    def test_collection_status_enum(self):
        """TC-COL-002: 催缴状态枚举正确"""
        from src.models.collection import CollectionStatus

        assert CollectionStatus.PENDING.value == "pending"
        assert CollectionStatus.IN_PROGRESS.value == "in_progress"
        assert CollectionStatus.SUCCESS.value == "success"
        assert CollectionStatus.FAILED.value == "failed"
        assert CollectionStatus.PARTIAL.value == "partial"


class TestCollectionSchemas:
    """测试催缴相关 Schema"""

    def test_collection_record_create_schema(self):
        """TC-COL-003: 创建催缴记录 Schema 验证"""
        from src.schemas.collection import (
            CollectionMethod,
            CollectionRecordCreate,
        )

        schema = CollectionRecordCreate(
            ledger_id="ledger_123",
            contract_id="contract_123",
            collection_method=CollectionMethod.PHONE,
            collection_date=date.today(),
            contacted_person="John Doe",
            contact_phone="13800138000",
        )

        assert schema.ledger_id == "ledger_123"
        assert schema.collection_method == CollectionMethod.PHONE
        assert schema.contacted_person == "John Doe"

    def test_collection_record_update_schema(self):
        """TC-COL-004: 更新催缴记录 Schema 验证"""
        from src.schemas.collection import (
            CollectionRecordUpdate,
            CollectionStatus,
        )

        schema = CollectionRecordUpdate(
            collection_status=CollectionStatus.SUCCESS,
            promised_amount=Decimal("10000.00"),
            promised_date=date.today() + timedelta(days=7),
        )

        assert schema.collection_status == CollectionStatus.SUCCESS
        assert schema.promised_amount == Decimal("10000.00")

    def test_collection_task_summary_schema(self):
        """TC-COL-005: 催缴任务汇总 Schema 验证"""
        from src.schemas.collection import CollectionTaskSummary

        summary = CollectionTaskSummary(
            total_overdue_count=5,
            total_overdue_amount=Decimal("50000.00"),
            pending_collection_count=3,
            this_month_collection_count=10,
            collection_success_rate=Decimal("80.5"),
        )

        assert summary.total_overdue_count == 5
        assert summary.total_overdue_amount == Decimal("50000.00")
        assert summary.collection_success_rate == Decimal("80.5")


class TestCollectionModelStructure:
    """测试催缴记录模型结构"""

    def test_collection_record_model_fields(self):
        """TC-COL-006: 验证模型字段存在"""
        from src.models.collection import CollectionRecord

        # 检查字段存在
        assert hasattr(CollectionRecord, "__tablename__")
        assert CollectionRecord.__tablename__ == "collection_records"

        # 检查列属性
        columns = [c.name for c in CollectionRecord.__table__.columns]
        expected_fields = [
            "id",
            "ledger_id",
            "contract_id",
            "collection_method",
            "collection_date",
            "collection_status",
            "contacted_person",
            "contact_phone",
            "promised_amount",
            "promised_date",
            "actual_payment_amount",
            "collection_notes",
            "next_follow_up_date",
            "operator",
            "operator_id",
            "created_at",
            "updated_at",
        ]

        for field in expected_fields:
            assert field in columns, f"Field {field} not found in CollectionRecord"

    def test_collection_record_relationships(self):
        """TC-COL-007: 验证关联关系"""
        from src.models.collection import CollectionRecord

        # 检查关联
        assert hasattr(CollectionRecord, "ledger")
        assert hasattr(CollectionRecord, "contract")

    def test_collection_record_foreign_keys_target_new_contract_tables(self):
        """TC-COL-008: 催缴记录应挂到新合同台账和新合同基表"""
        from src.models.collection import CollectionRecord

        ledger_fk = next(iter(CollectionRecord.__table__.c.ledger_id.foreign_keys))
        contract_fk = next(iter(CollectionRecord.__table__.c.contract_id.foreign_keys))

        assert ledger_fk.target_fullname == "contract_ledger_entries.entry_id"
        assert contract_fk.target_fullname == "contracts.contract_id"
