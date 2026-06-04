"""
催缴管理功能单元测试
"""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.exception_handler import ResourceNotFoundError
from src.schemas.collection import CollectionMethod, CollectionRecordCreate
from src.services.collection.service import CollectionService


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


class TestCollectionServiceBusinessBoundary:
    """催缴服务层应承载汇总口径、前置校验和操作人补全。"""

    @pytest.mark.asyncio
    async def test_summary_should_calculate_success_rate(self, monkeypatch):
        service = CollectionService()
        mock_crud = MagicMock()
        mock_crud.get_overdue_ledger_stats_async = AsyncMock(
            return_value=(3, Decimal("1200.00"))
        )
        mock_crud.count_by_statuses_async = AsyncMock(
            side_effect=[2, 1]
        )
        mock_crud.count_since_date_async = AsyncMock(return_value=4)
        mock_crud.count_total_async = AsyncMock(return_value=5)

        monkeypatch.setattr(
            "src.services.collection.service.collection_crud",
            mock_crud,
        )

        summary = await service.get_summary_async(db=MagicMock())

        assert summary.total_overdue_count == 3
        assert summary.total_overdue_amount == Decimal("1200.00")
        assert summary.pending_collection_count == 2
        assert summary.this_month_collection_count == 4
        assert summary.collection_success_rate == Decimal("20.0")

    @pytest.mark.asyncio
    async def test_create_should_fail_loud_when_ledger_missing(self, monkeypatch):
        service = CollectionService()
        service.get_ledger_by_id_async = AsyncMock(return_value=None)  # type: ignore[method-assign]
        mock_crud = MagicMock()
        mock_crud.create = AsyncMock()
        monkeypatch.setattr(
            "src.services.collection.service.collection_crud",
            mock_crud,
        )

        with pytest.raises(ResourceNotFoundError):
            await service.create_async(
                db=MagicMock(),
                obj_in=CollectionRecordCreate(
                    ledger_id="missing-ledger",
                    contract_id="contract-1",
                    collection_method=CollectionMethod.PHONE,
                    collection_date=date.today(),
                ),
                operator="tester",
                operator_id="user-1",
            )

        mock_crud.create.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_create_should_fill_operator_context_before_crud(self, monkeypatch):
        service = CollectionService()
        service.get_ledger_by_id_async = AsyncMock(return_value=MagicMock())  # type: ignore[method-assign]
        created_record = MagicMock()
        mock_crud = MagicMock()
        mock_crud.create = AsyncMock(return_value=created_record)
        monkeypatch.setattr(
            "src.services.collection.service.collection_crud",
            mock_crud,
        )

        result = await service.create_async(
            db=MagicMock(),
            obj_in=CollectionRecordCreate(
                ledger_id="ledger-1",
                contract_id="contract-1",
                collection_method=CollectionMethod.PHONE,
                collection_date=date.today(),
            ),
            operator="tester",
            operator_id="user-1",
        )

        assert result is created_record
        obj_in = mock_crud.create.await_args.kwargs["obj_in"]
        assert obj_in["operator"] == "tester"
        assert obj_in["operator_id"] == "user-1"
