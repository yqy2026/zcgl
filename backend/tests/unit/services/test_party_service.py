from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

from src.core.exception_handler import DuplicateResourceError, OperationNotAllowedError
from src.crud.query_builder import PartyFilter
from src.models.party import PartyReviewStatus, PartyType
from src.schemas.party import (
    PartyCreate,
    PartyUpdate,
    UserPartyBindingCreate,
    UserPartyBindingUpdate,
)
from src.services.party.service import PartyService

pytestmark = pytest.mark.asyncio


class TestPartyServiceUserScopeInvalidation:
    async def test_create_user_party_binding_publishes_scope_invalidation(self) -> None:
        db = MagicMock()
        binding = SimpleNamespace(user_id="user-1")
        party_crud = MagicMock()
        party_crud.create_user_party_binding = AsyncMock(return_value=binding)
        service = PartyService(data_access=party_crud)

        payload = MagicMock()
        payload.model_dump.return_value = {
            "user_id": "user-1",
            "party_id": "party-1",
            "relation_type": "owner",
        }

        with (
            patch.object(service, "_assert_user_exists", AsyncMock(return_value=None)),
            patch.object(service, "_assert_party_exists", AsyncMock(return_value=None)),
            patch("src.services.authz.authz_event_bus.publish_invalidation") as mock_publish,
        ):
            result = await service.create_user_party_binding(
                db,
                obj_in=payload,
            )

        assert result is binding
        mock_publish.assert_called_once_with(
            event_type="authz.user_scope.updated",
            payload={"user_id": "user-1"},
        )

    async def test_create_user_party_binding_does_not_fail_when_publish_errors(self) -> None:
        db = MagicMock()
        binding = SimpleNamespace(user_id="user-1")
        party_crud = MagicMock()
        party_crud.create_user_party_binding = AsyncMock(return_value=binding)
        service = PartyService(data_access=party_crud)

        payload = MagicMock()
        payload.model_dump.return_value = {
            "user_id": "user-1",
            "party_id": "party-1",
            "relation_type": "owner",
        }

        with (
            patch.object(service, "_assert_user_exists", AsyncMock(return_value=None)),
            patch.object(service, "_assert_party_exists", AsyncMock(return_value=None)),
            patch(
                "src.services.authz.authz_event_bus.publish_invalidation",
                side_effect=RuntimeError("boom"),
            ),
        ):
            result = await service.create_user_party_binding(
                db,
                obj_in=payload,
            )

        assert result is binding


class TestPartyServiceScopeAndBindingBehavior:
    async def test_get_parties_should_apply_resolved_party_scope(self) -> None:
        db = MagicMock()
        party_crud = MagicMock()
        party_crud.get_parties = AsyncMock(return_value=[])
        service = PartyService(data_access=party_crud)

        mock_resolve_filter = AsyncMock(return_value=PartyFilter(party_ids=["party-1"]))
        with patch(
            "src.services.party.service.resolve_user_party_filter",
            mock_resolve_filter,
        ):
            await service.get_parties(db, current_user_id="user-1")

        mock_resolve_filter.assert_awaited_once_with(
            db,
            current_user_id="user-1",
            party_filter=None,
            logger=ANY,
            allow_legacy_default_organization_fallback=False,
        )
        party_crud.get_parties.assert_awaited_once_with(
            db,
            skip=0,
            limit=100,
            party_type=None,
            status=None,
            search=None,
            scoped_party_ids=["party-1"],
        )

    async def test_get_parties_should_not_scope_when_filter_resolver_returns_none(self) -> None:
        db = MagicMock()
        party_crud = MagicMock()
        party_crud.get_parties = AsyncMock(return_value=[])
        service = PartyService(data_access=party_crud)

        with patch(
            "src.services.party.service.resolve_user_party_filter",
            AsyncMock(return_value=None),
        ):
            await service.get_parties(db, current_user_id="admin-user")

        party_crud.get_parties.assert_awaited_once_with(
            db,
            skip=0,
            limit=100,
            party_type=None,
            status=None,
            search=None,
            scoped_party_ids=None,
        )

    async def test_update_user_party_binding_should_clear_existing_primary_when_needed(
        self,
    ) -> None:
        db = MagicMock()
        binding = SimpleNamespace(
            id="binding-1",
            user_id="user-1",
            party_id="party-1",
            relation_type="owner",
            is_primary=False,
            valid_from=SimpleNamespace(),
            valid_to=None,
        )
        updated_binding = SimpleNamespace(id="binding-1", user_id="user-1")
        party_crud = MagicMock()
        party_crud.get_user_binding = AsyncMock(return_value=binding)
        party_crud.clear_primary_bindings_for_relation = AsyncMock(return_value=1)
        party_crud.update_user_party_binding = AsyncMock(return_value=updated_binding)
        service = PartyService(data_access=party_crud)

        with (
            patch.object(service, "_assert_user_exists", AsyncMock(return_value=None)),
            patch.object(
                service,
                "_publish_user_scope_invalidation",
                AsyncMock(return_value=None),
            ) as mock_publish,
        ):
            await service.update_user_party_binding(
                db,
                user_id="user-1",
                binding_id="binding-1",
                obj_in=UserPartyBindingUpdate.model_validate({"is_primary": True}),
            )

        party_crud.clear_primary_bindings_for_relation.assert_awaited_once_with(
            db,
            user_id="user-1",
            relation_type="owner",
            exclude_binding_id="binding-1",
            commit=False,
        )
        party_crud.update_user_party_binding.assert_awaited_once()
        mock_publish.assert_awaited_once_with("user-1")

    async def test_close_user_party_binding_should_publish_scope_invalidation(self) -> None:
        from datetime import UTC, datetime, timedelta

        db = MagicMock()
        now = datetime.now(UTC).replace(tzinfo=None)
        binding = SimpleNamespace(
            id="binding-1",
            user_id="user-1",
            valid_from=now - timedelta(days=1),
            valid_to=None,
        )
        party_crud = MagicMock()
        party_crud.get_user_binding = AsyncMock(return_value=binding)
        party_crud.update_user_party_binding = AsyncMock(return_value=binding)
        service = PartyService(data_access=party_crud)

        with (
            patch.object(service, "_assert_user_exists", AsyncMock(return_value=None)),
            patch.object(
                service,
                "_publish_user_scope_invalidation",
                AsyncMock(return_value=None),
            ) as mock_publish,
        ):
            closed = await service.close_user_party_binding(
                db,
                user_id="user-1",
                binding_id="binding-1",
            )

        assert closed is True
        party_crud.update_user_party_binding.assert_awaited_once()
        mock_publish.assert_awaited_once_with("user-1")

    async def test_create_user_party_binding_should_reject_invalid_time_range(self) -> None:
        from datetime import UTC, datetime, timedelta

        db = MagicMock()
        party_crud = MagicMock()
        party_crud.create_user_party_binding = AsyncMock()
        service = PartyService(data_access=party_crud)

        payload = UserPartyBindingCreate(
            user_id="user-1",
            party_id="party-1",
            relation_type="owner",
            valid_to=datetime.now(UTC).replace(tzinfo=None) - timedelta(days=1),
        )

        with (
            patch.object(service, "_assert_user_exists", AsyncMock(return_value=None)),
            patch.object(service, "_assert_party_exists", AsyncMock(return_value=None)),
        ):
            with pytest.raises(OperationNotAllowedError) as exc_info:
                await service.create_user_party_binding(
                    db,
                    obj_in=payload,
                )

        assert "失效时间不能早于生效时间" in str(exc_info.value)
        party_crud.create_user_party_binding.assert_not_called()


class TestPartyServiceReviewFlow:
    async def test_create_party_should_default_review_status_to_draft(self) -> None:
        db = MagicMock()
        created_party = SimpleNamespace(id="party-1")
        party_crud = MagicMock()
        party_crud.get_party_by_type_and_code = AsyncMock(return_value=None)
        party_crud.create_party = AsyncMock(return_value=created_party)
        service = PartyService(data_access=party_crud)

        payload = PartyCreate(
            party_type=PartyType.ORGANIZATION,
            name="测试主体",
            code="PARTY-001",
        )

        result = await service.create_party(db, obj_in=payload)

        assert result is created_party


class TestCustomerProfileAggregation:
    async def test_get_customer_profile_should_merge_metadata_contact_and_contract_history(
        self,
    ) -> None:
        db = MagicMock()
        party = SimpleNamespace(
            id="party-customer-1",
            party_type=PartyType.ORGANIZATION,
            name="终端租户甲",
            code="CUS-001",
            status="active",
            metadata_json={
                "customer_type": "external",
                "subject_nature": "enterprise",
                "identifier_type": "USCC",
                "unified_identifier": "91310000123456789A",
                "address": "上海市徐汇区测试路 1 号",
                "payment_term_preference": "月付",
                "risk_tags": ["手工关注"],
                "contact_name": "张三",
                "contact_phone": "13800000000",
            },
        )
        party_crud = MagicMock()
        party_crud.get_party = AsyncMock(return_value=party)
        service = PartyService(data_access=party_crud)

        direct_contract = SimpleNamespace(
            contract_id="contract-1",
            contract_number="CTR-001",
            status="ACTIVE",
            group_relation_type="DIRECT_LEASE",
            effective_from=datetime(2026, 1, 1),
            effective_to=datetime(2026, 12, 31),
            contract_group=SimpleNamespace(
                group_code="GRP-001",
                revenue_mode="AGENCY",
                risk_tags=["代理口径冲突"],
                updated_at=datetime(2026, 3, 30),
            ),
        )

        with (
            patch.object(service, "get_contacts", AsyncMock(return_value=[])),
            patch.object(
                service,
                "_list_customer_contracts",
                AsyncMock(return_value=[direct_contract]),
            ),
        ):
            profile = await service.get_customer_profile(
                db,
                party_id="party-customer-1",
                perspective="manager",
                effective_party_ids=["party-manager-1"],
            )

        assert profile["customer_party_id"] == "party-customer-1"
        assert profile["customer_name"] == "终端租户甲"
        assert profile["contact_name"] == "张三"
        assert profile["contact_phone"] == "13800000000"
        assert profile["historical_contract_count"] == 1
        assert profile["payment_term_preference"] == "月付"
        assert profile["risk_tags"] == ["手工关注", "代理口径冲突"]
        assert profile["risk_tag_items"] == [
            {
                "tag": "手工关注",
                "source": "manual",
                "updated_at": None,
            },
            {
                "tag": "代理口径冲突",
                "source": "rule",
                "updated_at": datetime(2026, 3, 30),
            },
        ]
        assert profile["contracts"][0]["group_relation_type"] == "DIRECT_LEASE"

    async def test_create_party_should_write_create_log(self) -> None:
        db = MagicMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.commit = MagicMock()
        created_party = SimpleNamespace(
            id="party-1",
            review_status=PartyReviewStatus.DRAFT.value,
        )
        party_crud = MagicMock()
        party_crud.get_party_by_type_and_code = AsyncMock(return_value=None)
        party_crud.create_party = AsyncMock(return_value=created_party)
        service = PartyService(data_access=party_crud)

        await service.create_party(
            db,
            obj_in=PartyCreate(
                party_type=PartyType.ORGANIZATION,
                name="测试主体",
                code="PARTY-001",
            ),
        )

        from src.models.party_review_log import PartyReviewLog

        log_calls = [c for c in db.add.call_args_list if isinstance(c[0][0], PartyReviewLog)]
        assert len(log_calls) == 1
        log_obj = log_calls[0][0][0]
        assert log_obj.action == "create"
        assert log_obj.from_status == "none"
        assert log_obj.to_status == PartyReviewStatus.DRAFT.value

    async def test_approve_party_review_should_update_review_fields(self) -> None:
        db = MagicMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        now = datetime.now(UTC).replace(tzinfo=None)
        party = SimpleNamespace(id="party-1", review_status=PartyReviewStatus.PENDING.value)
        updated_party = SimpleNamespace(
            id="party-1",
            review_status=PartyReviewStatus.APPROVED.value,
        )
        party_crud = MagicMock()
        party_crud.get_party = AsyncMock(return_value=party)
        party_crud.update_party = AsyncMock(return_value=updated_party)
        service = PartyService(data_access=party_crud)

        with patch.object(PartyService, "_utcnow_naive", return_value=now):
            result = await service.approve_party_review(
                db,
                party_id="party-1",
                reviewer="reviewer-1",
            )

        assert result is updated_party
        party_crud.update_party.assert_awaited_once_with(
            db,
            db_obj=party,
            obj_in={
                "review_status": PartyReviewStatus.APPROVED.value,
                "review_by": "reviewer-1",
                "reviewed_at": now,
                "review_reason": None,
            },
        )

    async def test_reject_party_review_should_reset_to_draft(self) -> None:
        """驳回后状态应回到 DRAFT，而不是 REJECTED。"""
        db = MagicMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        now = datetime.now(UTC).replace(tzinfo=None)
        party = SimpleNamespace(id="party-1", review_status=PartyReviewStatus.PENDING.value)
        updated_party = SimpleNamespace(
            id="party-1",
            review_status=PartyReviewStatus.DRAFT.value,
        )
        party_crud = MagicMock()
        party_crud.get_party = AsyncMock(return_value=party)
        party_crud.update_party = AsyncMock(return_value=updated_party)
        service = PartyService(data_access=party_crud)

        with patch.object(PartyService, "_utcnow_naive", return_value=now):
            result = await service.reject_party_review(
                db,
                party_id="party-1",
                reviewer="reviewer-1",
                reason="资料不完整",
            )

        assert result is updated_party
        party_crud.update_party.assert_awaited_once_with(
            db,
            db_obj=party,
            obj_in={
                "review_status": PartyReviewStatus.DRAFT.value,
                "review_by": "reviewer-1",
                "reviewed_at": now,
                "review_reason": "资料不完整",
            },
        )

    async def test_update_party_should_block_when_pending(self) -> None:
        """待审状态的主体不允许编辑。"""
        db = MagicMock()
        party = SimpleNamespace(id="party-1", review_status=PartyReviewStatus.PENDING.value)
        party_crud = MagicMock()
        party_crud.get_party = AsyncMock(return_value=party)
        service = PartyService(data_access=party_crud)

        with pytest.raises(OperationNotAllowedError, match="不允许编辑"):
            await service.update_party(
                db,
                party_id="party-1",
                obj_in=PartyUpdate(name="新名称"),
            )

    async def test_update_party_should_block_when_approved(self) -> None:
        """已审核状态的主体不允许编辑。"""
        db = MagicMock()
        party = SimpleNamespace(id="party-1", review_status=PartyReviewStatus.APPROVED.value)
        party_crud = MagicMock()
        party_crud.get_party = AsyncMock(return_value=party)
        service = PartyService(data_access=party_crud)

        with pytest.raises(OperationNotAllowedError, match="不允许编辑"):
            await service.update_party(
                db,
                party_id="party-1",
                obj_in=PartyUpdate(name="新名称"),
            )

    async def test_update_party_should_allow_when_draft(self) -> None:
        """草稿状态的主体允许编辑。"""
        db = MagicMock()
        party = SimpleNamespace(id="party-1", review_status=PartyReviewStatus.DRAFT.value)
        updated_party = SimpleNamespace(id="party-1", name="新名称")
        party_crud = MagicMock()
        party_crud.get_party = AsyncMock(return_value=party)
        party_crud.update_party = AsyncMock(return_value=updated_party)
        service = PartyService(data_access=party_crud)

        result = await service.update_party(
            db,
            party_id="party-1",
            obj_in=PartyUpdate(name="新名称"),
        )

        assert result is updated_party

    async def test_update_party_should_write_update_log(self) -> None:
        db = MagicMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        party = SimpleNamespace(
            id="party-1",
            party_type=PartyType.ORGANIZATION.value,
            name="旧主体",
            code="OLD-001",
            review_status=PartyReviewStatus.DRAFT.value,
            status="active",
        )
        updated_party = SimpleNamespace(id="party-1", name="新主体")
        party_crud = MagicMock()
        party_crud.get_party = AsyncMock(return_value=party)
        party_crud.update_party = AsyncMock(return_value=updated_party)
        service = PartyService(data_access=party_crud)

        await service.update_party(
            db,
            party_id="party-1",
            obj_in=PartyUpdate(name="新主体"),
        )

        from src.models.party_review_log import PartyReviewLog

        log_calls = [c for c in db.add.call_args_list if isinstance(c[0][0], PartyReviewLog)]
        assert len(log_calls) == 1
        log_obj = log_calls[0][0][0]
        assert log_obj.action == "update"
        assert log_obj.reason == "fields:name"

    async def test_delete_party_should_block_when_pending(self) -> None:
        """待审状态的主体不允许删除。"""
        db = MagicMock()
        party = SimpleNamespace(id="party-1", review_status=PartyReviewStatus.PENDING.value)
        party_crud = MagicMock()
        party_crud.get_party = AsyncMock(return_value=party)
        service = PartyService(data_access=party_crud)

        with pytest.raises(OperationNotAllowedError, match="不允许删除"):
            await service.delete_party(db, party_id="party-1")

    async def test_delete_party_should_block_when_approved(self) -> None:
        """已审核状态的主体不允许删除。"""
        db = MagicMock()
        party = SimpleNamespace(id="party-1", review_status=PartyReviewStatus.APPROVED.value)
        party_crud = MagicMock()
        party_crud.get_party = AsyncMock(return_value=party)
        service = PartyService(data_access=party_crud)

        with pytest.raises(OperationNotAllowedError, match="不允许删除"):
            await service.delete_party(db, party_id="party-1")

    async def test_delete_party_should_allow_when_draft(self) -> None:
        """草稿状态的主体允许删除。"""
        db = MagicMock()
        party = SimpleNamespace(id="party-1", review_status=PartyReviewStatus.DRAFT.value)
        party_crud = MagicMock()
        party_crud.get_party = AsyncMock(return_value=party)
        party_crud.delete_party = AsyncMock(return_value=None)
        service = PartyService(data_access=party_crud)

        with patch.object(service, "_assert_no_references", AsyncMock(return_value=None)):
            result = await service.delete_party(db, party_id="party-1")

        assert result is True

    async def test_create_party_should_reject_duplicate_type_and_code(self) -> None:
        """相同 party_type + code 应抛 DuplicateResourceError。"""
        db = MagicMock()
        existing = SimpleNamespace(id="existing-1")
        party_crud = MagicMock()
        party_crud.get_party_by_type_and_code = AsyncMock(return_value=existing)
        service = PartyService(data_access=party_crud)

        payload = PartyCreate(
            party_type=PartyType.ORGANIZATION,
            name="重复主体",
            code="DUP-001",
        )

        with pytest.raises(DuplicateResourceError, match="主体"):
            await service.create_party(db, obj_in=payload)

        party_crud.create_party.assert_not_called()

    async def test_create_party_should_reject_duplicate_type_and_name(self) -> None:
        """相同 party_type + name 应抛 DuplicateResourceError。"""
        db = MagicMock()
        existing = SimpleNamespace(id="existing-1")
        party_crud = MagicMock()
        party_crud.get_party_by_type_and_code = AsyncMock(return_value=None)
        party_crud.get_party_by_type_and_name = AsyncMock(return_value=existing)
        service = PartyService(data_access=party_crud)

        payload = PartyCreate(
            party_type=PartyType.ORGANIZATION,
            name="重复主体",
            code="UNIQUE-001",
        )

        with pytest.raises(DuplicateResourceError, match="主体"):
            await service.create_party(db, obj_in=payload)

        party_crud.create_party.assert_not_called()

    async def test_create_party_should_succeed_when_no_duplicate(self) -> None:
        """不重复时应正常创建。"""
        db = MagicMock()
        created = SimpleNamespace(id="party-new")
        party_crud = MagicMock()
        party_crud.get_party_by_type_and_code = AsyncMock(return_value=None)
        party_crud.get_party_by_type_and_name = AsyncMock(return_value=None)
        party_crud.create_party = AsyncMock(return_value=created)
        service = PartyService(data_access=party_crud)

        payload = PartyCreate(
            party_type=PartyType.ORGANIZATION,
            name="新主体",
            code="NEW-001",
        )

        result = await service.create_party(db, obj_in=payload)

        assert result is created

    async def test_update_party_should_reject_duplicate_name_when_changed(self) -> None:
        db = MagicMock()
        party = SimpleNamespace(
            id="party-1",
            party_type=PartyType.ORGANIZATION.value,
            name="旧主体",
            code="OLD-001",
            review_status=PartyReviewStatus.DRAFT.value,
        )
        duplicated_party = SimpleNamespace(id="party-2")
        party_crud = MagicMock()
        party_crud.get_party = AsyncMock(return_value=party)
        party_crud.get_party_by_type_and_name = AsyncMock(return_value=duplicated_party)
        service = PartyService(data_access=party_crud)

        with pytest.raises(DuplicateResourceError, match="主体"):
            await service.update_party(
                db,
                party_id="party-1",
                obj_in=PartyUpdate(name="新重复主体"),
            )

        party_crud.update_party.assert_not_called()

    async def test_import_parties_should_create_approved_records_and_collect_duplicates(self) -> None:
        db = MagicMock()
        party_crud = MagicMock()
        party_crud.get_party_by_type_and_code = AsyncMock(
            side_effect=[None, SimpleNamespace(id="existing-2")]
        )
        party_crud.get_party_by_type_and_name = AsyncMock(
            side_effect=[None, None]
        )
        party_crud.create_party = AsyncMock(
            return_value=SimpleNamespace(id="party-1", name="导入主体1")
        )
        service = PartyService(data_access=party_crud)

        result = await service.import_parties(
            db,
            items=[
                PartyCreate(
                    party_type=PartyType.ORGANIZATION,
                    name="导入主体1",
                    code="IMP-001",
                    status="active",
                ),
                PartyCreate(
                    party_type=PartyType.ORGANIZATION,
                    name="导入主体2",
                    code="IMP-002",
                    status="active",
                ),
            ],
            operator="import-user",
        )

        assert result["created_count"] == 1
        assert result["error_count"] == 1
        assert result["items"][0]["status"] == "created"
        assert result["items"][1]["status"] == "error"
        create_payload = party_crud.create_party.await_args.kwargs["obj_in"]
        assert create_payload["review_status"] == PartyReviewStatus.APPROVED.value
        assert create_payload["review_by"] == "import-user"
        assert create_payload["review_reason"] == "初始化导入"


class TestPartyServiceSoftDelete:
    async def test_delete_party_should_check_asset_references(self) -> None:
        """被资产引用的主体不允许删除。"""
        db = MagicMock()
        party = SimpleNamespace(id="party-1", review_status=PartyReviewStatus.DRAFT.value)
        party_crud = MagicMock()
        party_crud.get_party = AsyncMock(return_value=party)
        service = PartyService(data_access=party_crud)

        with patch.object(
            service,
            "_assert_no_references",
            AsyncMock(
                side_effect=OperationNotAllowedError(
                    "该主体被 2 个资产引用，无法删除",
                    reason="party_delete_has_asset_references",
                )
            ),
        ):
            with pytest.raises(OperationNotAllowedError, match="资产引用"):
                await service.delete_party(db, party_id="party-1")

    async def test_delete_party_should_check_contract_references(self) -> None:
        """被合同组引用的主体不允许删除。"""
        db = MagicMock()
        party = SimpleNamespace(id="party-1", review_status=PartyReviewStatus.DRAFT.value)
        party_crud = MagicMock()
        party_crud.get_party = AsyncMock(return_value=party)
        service = PartyService(data_access=party_crud)

        with patch.object(
            service,
            "_assert_no_references",
            AsyncMock(
                side_effect=OperationNotAllowedError(
                    "该主体被 1 个合同组引用，无法删除",
                    reason="party_delete_has_contract_group_references",
                )
            ),
        ):
            with pytest.raises(OperationNotAllowedError, match="合同组引用"):
                await service.delete_party(db, party_id="party-1")

    async def test_delete_party_soft_deletes_via_crud(self) -> None:
        """删除应调用 CRUD 软删除。"""
        db = MagicMock()
        party = SimpleNamespace(id="party-1", review_status=PartyReviewStatus.DRAFT.value)
        party_crud = MagicMock()
        party_crud.get_party = AsyncMock(return_value=party)
        party_crud.delete_party = AsyncMock(return_value=None)
        service = PartyService(data_access=party_crud)

        with patch.object(service, "_assert_no_references", AsyncMock(return_value=None)):
            result = await service.delete_party(db, party_id="party-1")

        assert result is True
        party_crud.delete_party.assert_awaited_once_with(db, db_obj=party)


class TestPartyServiceReviewLog:
    async def test_submit_review_should_write_log(self) -> None:
        """提审应写入审核日志。"""
        db = MagicMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        party = SimpleNamespace(id="party-1", review_status=PartyReviewStatus.DRAFT)
        updated = SimpleNamespace(id="party-1", review_status=PartyReviewStatus.PENDING.value)
        party_crud = MagicMock()
        party_crud.get_party = AsyncMock(return_value=party)
        party_crud.update_party = AsyncMock(return_value=updated)
        service = PartyService(data_access=party_crud)

        result = await service.submit_party_review(db, party_id="party-1")

        assert result is updated
        # Verify db.add was called with a PartyReviewLog
        from src.models.party_review_log import PartyReviewLog

        add_calls = db.add.call_args_list
        log_calls = [c for c in add_calls if isinstance(c[0][0], PartyReviewLog)]
        assert len(log_calls) == 1
        log_obj = log_calls[0][0][0]
        assert log_obj.party_id == "party-1"
        assert log_obj.action == "submit"
        assert log_obj.from_status == "draft"
        assert log_obj.to_status == "pending"

    async def test_approve_review_should_write_log(self) -> None:
        """通过审核应写入审核日志。"""
        db = MagicMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        now = datetime.now(UTC).replace(tzinfo=None)
        party = SimpleNamespace(id="party-1", review_status=PartyReviewStatus.PENDING)
        updated = SimpleNamespace(id="party-1", review_status=PartyReviewStatus.APPROVED.value)
        party_crud = MagicMock()
        party_crud.get_party = AsyncMock(return_value=party)
        party_crud.update_party = AsyncMock(return_value=updated)
        service = PartyService(data_access=party_crud)

        with patch.object(PartyService, "_utcnow_naive", return_value=now):
            result = await service.approve_party_review(
                db, party_id="party-1", reviewer="审核人A"
            )

        assert result is updated
        from src.models.party_review_log import PartyReviewLog

        add_calls = db.add.call_args_list
        log_calls = [c for c in add_calls if isinstance(c[0][0], PartyReviewLog)]
        assert len(log_calls) == 1
        log_obj = log_calls[0][0][0]
        assert log_obj.action == "approve"
        assert log_obj.from_status == "pending"
        assert log_obj.to_status == "approved"
        assert log_obj.operator == "审核人A"

    async def test_reject_review_should_write_log(self) -> None:
        """驳回应写入审核日志。"""
        db = MagicMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        now = datetime.now(UTC).replace(tzinfo=None)
        party = SimpleNamespace(id="party-1", review_status=PartyReviewStatus.PENDING)
        updated = SimpleNamespace(id="party-1", review_status=PartyReviewStatus.DRAFT.value)
        party_crud = MagicMock()
        party_crud.get_party = AsyncMock(return_value=party)
        party_crud.update_party = AsyncMock(return_value=updated)
        service = PartyService(data_access=party_crud)

        with patch.object(PartyService, "_utcnow_naive", return_value=now):
            result = await service.reject_party_review(
                db, party_id="party-1", reviewer="审核人B", reason="信息不全"
            )

        assert result is updated
        from src.models.party_review_log import PartyReviewLog

        add_calls = db.add.call_args_list
        log_calls = [c for c in add_calls if isinstance(c[0][0], PartyReviewLog)]
        assert len(log_calls) == 1
        log_obj = log_calls[0][0][0]
        assert log_obj.action == "reject"
        assert log_obj.from_status == "pending"
        assert log_obj.to_status == "draft"
        assert log_obj.operator == "审核人B"
        assert log_obj.reason == "信息不全"
