"""资产写入服务 — 创建、更新、删除、恢复、审核流转等写操作。

查询方法继承自 ``AssetQueryService``。
向后兼容: ``from src.services.asset.asset_service import AssetService`` 仍然可用。
"""

import logging
from contextlib import asynccontextmanager
from typing import Any, cast

from sqlalchemy import func, select
from sqlalchemy.orm.exc import StaleDataError

from ...constants.business_constants import DataStatusValues
from ...core.exception_handler import (
    DuplicateResourceError,
    ResourceNotFoundError,
    conflict,
    operation_not_allowed,
    validation_error,
)
from ...crud.asset_management_history import asset_management_history_crud
from ...crud.history import history_crud
from ...crud.party import party_crud  # noqa: F401
from ...models.asset import Asset, AssetReviewStatus
from ...models.asset_history import AssetHistory
from ...models.asset_review_log import AssetReviewLog
from ...models.associations import contract_assets
from ...models.auth import User
from ...models.contract_group import Contract, ContractLifecycleStatus
from ...schemas.asset import AssetCreate, AssetUpdate
from ...services.asset.asset_calculator import AssetCalculator
from ...services.enum_validation_service import get_enum_validation_service_async
from ...utils.str import normalize_optional_str
from ...utils.time import utcnow_naive
from .asset_query_service import (  # noqa: F401
    AssetQueryService,
    ownership,
    resolve_user_party_filter,
)
from .asset_validation import (  # noqa: F401
    _ADDRESS_SUB_FIELDS,
    _as_decimal,
    _compose_address,
    _normalize_bool_filter,
    build_filters,
    ensure_asset_not_linked,
    normalize_summary_period,
    resolve_owner_party_scope_by_ownership_id,
    resolve_ownership,
)

# Re-export party_crud so that `src.services.asset.asset_service.party_crud` works
# (used by tests that monkeypatch at module level).
# 子模块 re-export（向后兼容）

logger = logging.getLogger(__name__)

_EDIT_BLOCKED_REVIEW_STATUSES = frozenset(
    {AssetReviewStatus.PENDING.value, AssetReviewStatus.APPROVED.value}
)


class AssetService(AssetQueryService):
    """资产服务 — 继承 ``AssetQueryService`` 的查询能力, 增加写入 / 审核流转方法。"""

    # build_filters 保留为 static method 以兼容 AssetService.build_filters(...)
    @staticmethod
    def build_filters(  # type: ignore[override]
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        return build_filters(**kwargs)

    # --- 内部工具 ---

    @asynccontextmanager
    async def _transaction(self) -> Any:
        if self.db.in_transaction():
            try:
                yield
                await self.db.commit()
            except Exception:
                await self.db.rollback()
                raise
        else:
            async with self.db.begin():
                yield

    # 向后兼容: 保留 method 签名，委托给独立函数
    async def _resolve_ownership(
        self, data: dict[str, Any], *, current_asset: Asset | None = None
    ) -> dict[str, Any]:
        return await resolve_ownership(self.db, data, current_asset=current_asset)

    async def _ensure_asset_not_linked(self, asset_id: str) -> None:
        await ensure_asset_not_linked(self.db, asset_id, self.asset_crud)

    async def resolve_owner_party_scope_by_ownership_id_async(
        self, *, ownership_id: str
    ) -> str | None:
        return await resolve_owner_party_scope_by_ownership_id(
            self.db, ownership_id=ownership_id
        )

    # --- 审核流转内部工具 ---

    @staticmethod
    def _require_review_reason(action: str, reason: str) -> str:
        normalized_reason = reason.strip()
        if normalized_reason == "":
            raise validation_error(
                f"{action}原因不能为空", field_errors={"reason": "required"}
            )
        return normalized_reason

    @staticmethod
    def _ensure_allowed_review_status(
        asset: Asset, *, allowed_statuses: set[str], action: str
    ) -> None:
        if asset.review_status not in allowed_statuses:
            allowed_labels = ", ".join(sorted(allowed_statuses))
            raise operation_not_allowed(
                f"资产当前审核状态为 {asset.review_status}，"
                f"仅允许在 {allowed_labels} 状态执行{action}",
                reason="asset_invalid_review_status_transition",
            )

    async def _append_asset_review_log(
        self,
        *,
        asset_id: str,
        action: str,
        from_status: str,
        to_status: str,
        operator: str,
        reason: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        self.db.add(
            AssetReviewLog(
                asset_id=asset_id,
                action=action,
                from_status=from_status,
                to_status=to_status,
                operator=operator,
                reason=reason,
                context=context,
            )
        )

    async def _count_active_contracts_for_asset(self, asset_id: str) -> int:
        stmt = (
            select(func.count(Contract.contract_id))
            .select_from(Contract)
            .join(
                contract_assets, contract_assets.c.contract_id == Contract.contract_id
            )
            .where(
                contract_assets.c.asset_id == asset_id,
                Contract.data_status == "正常",
                Contract.status == ContractLifecycleStatus.ACTIVE,
            )
        )
        return int((await self.db.execute(stmt)).scalar_one())

    # --- 写入操作 — 创建 / 更新 / 删除 / 恢复 ---

    async def create_asset(
        self,
        asset_in: AssetCreate,
        current_user: User | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        session_id: str | None = None,
    ) -> Asset:
        operator = (
            getattr(current_user, "username", None)
            or getattr(current_user, "id", None)
            or "system"
        )
        default_org_id = getattr(current_user, "default_organization_id", None)
        organization_id = (
            str(default_org_id)
            if default_org_id is not None and str(default_org_id).strip() != ""
            else None
        )

        async with self._transaction():
            asset_crud = self.asset_crud
            validation_service = get_enum_validation_service_async(self.db)
            incoming_payload = asset_in.model_dump()
            is_valid, errors = await validation_service.validate_asset_data(
                incoming_payload
            )
            if not is_valid:
                raise validation_error(
                    f"枚举值验证失败: {'; '.join(errors)}", field_errors=errors
                )

            existing_asset = await asset_crud.get_by_name_async(
                db=self.db, asset_name=asset_in.asset_name
            )
            if existing_asset:
                raise DuplicateResourceError("Asset", "asset_name", asset_in.asset_name)

            asset_data = asset_in.model_dump()
            asset_data = await self._resolve_ownership(asset_data)
            calculated_fields = AssetCalculator.auto_calculate_fields(asset_data)
            final_data = {**asset_data, **calculated_fields}

            composed_address = _compose_address(final_data)
            if composed_address is not None:
                final_data["address"] = composed_address
            else:
                raise validation_error(
                    "地址信息不完整：请提供 address_detail 以生成地址",
                    field_errors={"address_detail": "required_for_address_composition"},
                )

            area_errors = AssetCalculator.validate_area_consistency(final_data)
            if area_errors:
                raise validation_error(
                    f"数据验证失败: {'; '.join(area_errors)}", field_errors=area_errors
                )

            calculated_asset_in = AssetCreate(**final_data)
            return cast(
                Asset,
                await asset_crud.create_with_history_async(
                    db=self.db,
                    obj_in=calculated_asset_in,
                    commit=False,
                    operator=str(operator) if operator is not None else None,
                    organization_id=organization_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    session_id=session_id,
                ),
            )

    async def update_asset(
        self,
        asset_id: str,
        asset_in: AssetUpdate,
        current_user: User | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        session_id: str | None = None,
    ) -> Asset:
        operator = (
            getattr(current_user, "username", None)
            or getattr(current_user, "id", None)
            or "system"
        )
        try:
            async with self._transaction():
                asset_crud = self.asset_crud
                user_id = getattr(current_user, "id", None)
                asset = await self.get_asset(
                    asset_id,
                    use_cache=False,
                    current_user_id=str(user_id) if user_id is not None else None,
                )
                if asset.review_status in _EDIT_BLOCKED_REVIEW_STATUSES:
                    raise operation_not_allowed(
                        f"资产处于 {asset.review_status} 状态，不允许编辑业务字段，请先反审核",
                        reason="asset_edit_blocked_by_review_status",
                    )

                validation_service = get_enum_validation_service_async(self.db)
                update_data_raw = asset_in.model_dump(exclude_unset=True)
                expected_version = update_data_raw.pop("version", None)
                if (
                    expected_version is not None
                    and hasattr(asset, "version")
                    and asset.version != expected_version
                ):
                    raise conflict("资产版本冲突，请刷新后重试", resource_type="Asset")

                is_valid, enum_errors = await validation_service.validate_asset_data(
                    update_data_raw
                )
                if not is_valid:
                    raise validation_error(
                        f"枚举值验证失败: {'; '.join(enum_errors)}",
                        field_errors=enum_errors,
                    )

                update_data_raw = await self._resolve_ownership(
                    update_data_raw, current_asset=asset
                )

                new_name = update_data_raw.get("asset_name")
                if new_name and new_name != asset.asset_name:
                    existing = await asset_crud.get_by_name_async(
                        db=self.db, asset_name=new_name
                    )
                    if existing and existing.id != asset_id:
                        raise DuplicateResourceError("Asset", "asset_name", new_name)

                current_data = {
                    f: getattr(asset, f)
                    for f in (
                        "rentable_area",
                        "rented_area",
                        "annual_income",
                        "annual_expense",
                    )
                    if hasattr(asset, f)
                }
                merged_data = {**current_data, **update_data_raw}
                calculated_data = AssetCalculator.auto_calculate_fields(merged_data)

                area_errors = AssetCalculator.validate_area_consistency(calculated_data)
                if area_errors:
                    raise validation_error(
                        f"数据验证失败: {'; '.join(area_errors)}",
                        field_errors=area_errors,
                    )

                final_update = {
                    **update_data_raw,
                    **{
                        k: v
                        for k, v in calculated_data.items()
                        if k not in update_data_raw
                    },
                }

                if any(f in final_update for f in _ADDRESS_SUB_FIELDS):
                    composed = _compose_address(final_update, current_asset=asset)
                    if composed:
                        final_update["address"] = composed

                calculated_asset_in = AssetUpdate(**final_update)

                # REQ-AST-002: 经营方变更自动记录历史
                new_manager = normalize_optional_str(
                    final_update.get("manager_party_id")
                )
                old_manager = normalize_optional_str(
                    getattr(asset, "manager_party_id", None)
                )
                if new_manager and old_manager and new_manager != old_manager:
                    await asset_management_history_crud.close_active(
                        self.db,
                        asset_id=asset_id,
                        manager_party_id=old_manager,
                        commit=False,
                    )
                    await asset_management_history_crud.create(
                        self.db,
                        asset_id=asset_id,
                        manager_party_id=new_manager,
                        change_reason=f"经营方变更: {old_manager} → {new_manager}",
                        changed_by=str(operator) if operator is not None else None,
                        commit=False,
                    )

                return cast(
                    Asset,
                    await asset_crud.update_with_history_async(
                        db=self.db,
                        db_obj=asset,
                        obj_in=calculated_asset_in,
                        commit=False,
                        operator=str(operator) if operator is not None else None,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        session_id=session_id,
                    ),
                )
        except StaleDataError as exc:
            raise conflict(
                "资产已被其他人更新，请刷新后重试", resource_type="Asset"
            ) from exc

    async def delete_asset(
        self, asset_id: str, current_user: User | None = None
    ) -> None:
        try:
            async with self._transaction():
                user_id = getattr(current_user, "id", None)
                asset = await self.get_asset(
                    asset_id,
                    use_cache=False,
                    current_user_id=str(user_id) if user_id is not None else None,
                )
                if asset.review_status in _EDIT_BLOCKED_REVIEW_STATUSES:
                    raise operation_not_allowed(
                        f"资产处于 {asset.review_status} 状态，不允许删除，请先反审核",
                        reason="asset_delete_blocked_by_review_status",
                    )
                await self._ensure_asset_not_linked(asset_id)
                operator = (
                    getattr(current_user, "username", None)
                    or getattr(current_user, "id", None)
                    or "system"
                )
                history = AssetHistory()
                history.asset_id = asset.id
                history.operation_type = "DELETE"
                history.description = f"删除资产: {asset.asset_name}"
                history.operator = str(operator) if operator is not None else None
                self.db.add(history)
                asset.data_status = DataStatusValues.ASSET_DELETED
                asset.updated_by = str(operator) if operator is not None else None
                asset.updated_at = utcnow_naive()
                self.db.add(asset)
                await self.db.flush()
        except StaleDataError as exc:
            raise conflict(
                "资产已被其他人更新，请刷新后重试", resource_type="Asset"
            ) from exc

    async def restore_asset(
        self, asset_id: str, current_user: User | None = None
    ) -> Asset:
        try:
            async with self._transaction():
                asset_crud = self.asset_crud
                asset = cast(
                    Asset | None,
                    await asset_crud.get_async(
                        db=self.db, id=asset_id, include_deleted=True
                    ),
                )
                if not asset:
                    raise ResourceNotFoundError("Asset", asset_id)
                if asset.data_status != DataStatusValues.ASSET_DELETED:
                    raise operation_not_allowed(
                        "资产未处于已删除状态，无法恢复", reason="asset_not_deleted"
                    )
                operator = (
                    getattr(current_user, "username", None)
                    or getattr(current_user, "id", None)
                    or "system"
                )
                history = AssetHistory()
                history.asset_id = asset.id
                history.operation_type = "RESTORE"
                history.description = f"恢复资产: {asset.asset_name}"
                history.operator = str(operator) if operator is not None else None
                self.db.add(history)
                asset.data_status = DataStatusValues.ASSET_NORMAL
                asset.updated_by = str(operator) if operator is not None else None
                asset.updated_at = utcnow_naive()
                self.db.add(asset)
                await self.db.flush()
                return asset
        except StaleDataError as exc:
            raise conflict(
                "资产已被其他人更新，请刷新后重试", resource_type="Asset"
            ) from exc

    async def hard_delete_asset(
        self, asset_id: str, current_user: User | None = None
    ) -> None:
        try:
            async with self._transaction():
                asset_crud = self.asset_crud
                asset = cast(
                    Asset | None,
                    await asset_crud.get_async(
                        db=self.db, id=asset_id, include_deleted=True
                    ),
                )
                if not asset:
                    raise ResourceNotFoundError("Asset", asset_id)
                if asset.data_status != DataStatusValues.ASSET_DELETED:
                    raise operation_not_allowed(
                        "资产未处于已删除状态，无法彻底删除", reason="asset_not_deleted"
                    )
                await self._ensure_asset_not_linked(asset_id)
                await history_crud.remove_by_asset_id_async(
                    db=self.db, asset_id=asset.id, commit=False
                )
                await self.db.delete(asset)
                await self.db.flush()
        except StaleDataError as exc:
            raise conflict(
                "资产已被其他人更新，请刷新后重试", resource_type="Asset"
            ) from exc

    # --- 审核流转 ---

    async def _transition_review_status(
        self,
        asset_id: str,
        *,
        action: str,
        action_label: str,
        allowed_from: set[str],
        to_status: str,
        operator: str,
        reason: str | None = None,
        set_reviewer: bool = False,
        clear_reviewer: bool = False,
        log_context: dict[str, Any] | None = None,
    ) -> Asset:
        """审核流转统一入口 — 所有审核方法委托到此。"""
        try:
            async with self._transaction():
                asset = await self.get_asset(asset_id, use_cache=False)
                self._ensure_allowed_review_status(
                    asset,
                    allowed_statuses=allowed_from,
                    action=action_label,
                )
                from_status = asset.review_status
                asset.review_status = to_status
                if set_reviewer:
                    asset.review_by = operator
                    asset.reviewed_at = utcnow_naive()
                    asset.review_reason = reason
                elif clear_reviewer:
                    asset.review_by = None
                    asset.reviewed_at = None
                    asset.review_reason = None
                asset.updated_by = operator
                asset.updated_at = utcnow_naive()
                self.db.add(asset)
                await self._append_asset_review_log(
                    asset_id=asset.id,
                    action=action,
                    from_status=from_status,
                    to_status=to_status,
                    operator=operator,
                    reason=reason,
                    context=log_context,
                )
                await self.db.flush()
                return asset
        except StaleDataError as exc:
            raise conflict(
                "资产已被其他人更新，请刷新后重试", resource_type="Asset"
            ) from exc

    async def submit_asset_review(self, asset_id: str, operator: str) -> Asset:
        return await self._transition_review_status(
            asset_id,
            action="submit",
            action_label="提审",
            allowed_from={AssetReviewStatus.DRAFT.value},
            to_status=AssetReviewStatus.PENDING.value,
            operator=operator,
            clear_reviewer=True,
        )

    async def approve_asset_review(self, asset_id: str, reviewer: str) -> Asset:
        return await self._transition_review_status(
            asset_id,
            action="approve",
            action_label="审核通过",
            allowed_from={AssetReviewStatus.PENDING.value},
            to_status=AssetReviewStatus.APPROVED.value,
            operator=reviewer,
            set_reviewer=True,
        )

    async def reject_asset_review(
        self, asset_id: str, reviewer: str, reason: str
    ) -> Asset:
        return await self._transition_review_status(
            asset_id,
            action="reject",
            action_label="驳回",
            allowed_from={AssetReviewStatus.PENDING.value},
            to_status=AssetReviewStatus.DRAFT.value,
            operator=reviewer,
            set_reviewer=True,
            reason=self._require_review_reason("驳回", reason),
        )

    async def reverse_asset_review(
        self, asset_id: str, reviewer: str, reason: str
    ) -> Asset:
        normalized_reason = self._require_review_reason("反审核", reason)
        # 反审核需要额外记录关联合同数量
        asset = await self.get_asset(asset_id, use_cache=False)
        count = await self._count_active_contracts_for_asset(asset.id)
        return await self._transition_review_status(
            asset_id,
            action="reverse",
            action_label="反审核",
            allowed_from={AssetReviewStatus.APPROVED.value},
            to_status=AssetReviewStatus.REVERSED.value,
            operator=reviewer,
            set_reviewer=True,
            reason=normalized_reason,
            log_context={"active_contract_count": count},
        )

    async def resubmit_asset_review(self, asset_id: str, operator: str) -> Asset:
        return await self._transition_review_status(
            asset_id,
            action="resubmit",
            action_label="重提审",
            allowed_from={AssetReviewStatus.REVERSED.value},
            to_status=AssetReviewStatus.PENDING.value,
            operator=operator,
            clear_reviewer=True,
        )


# 向后兼容别名
AsyncAssetService = AssetService
