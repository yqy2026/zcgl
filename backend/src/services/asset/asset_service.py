from collections.abc import Generator
from contextlib import asynccontextmanager, contextmanager
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from ...core.exception_handler import (
    DuplicateResourceError,
    ResourceNotFoundError,
    conflict,
    validation_error,
)
from ...crud.asset import asset_crud
from ...crud.history import history_crud
from ...models.asset import Asset, AssetHistory
from ...models.auth import User
from ...schemas.asset import AssetCreate, AssetUpdate
from ...services.asset.asset_calculator import AssetCalculator
from ...services.enum_validation_service import (
    get_enum_validation_service,
    get_enum_validation_service_async,
)


class AssetService:
    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def build_filters(
        *,
        ownership_status: str | None = None,
        property_nature: str | None = None,
        usage_status: str | None = None,
        ownership_entity: str | None = None,
        management_entity: str | None = None,
        business_category: str | None = None,
        min_area: float | None = None,
        max_area: float | None = None,
        is_litigated: str | None = None,
    ) -> dict[str, Any] | None:
        filters: dict[str, Any] = {}
        if ownership_status is not None and ownership_status != "":
            filters["ownership_status"] = ownership_status
        if property_nature is not None and property_nature != "":
            filters["property_nature"] = property_nature
        if usage_status is not None and usage_status != "":
            filters["usage_status"] = usage_status
        if ownership_entity is not None and ownership_entity != "":
            filters["ownership_entity"] = ownership_entity
        if management_entity is not None and management_entity != "":
            filters["management_entity"] = management_entity
        if business_category is not None and business_category != "":
            filters["business_category"] = business_category
        if min_area is not None:
            filters["min_area"] = min_area
        if max_area is not None:
            filters["max_area"] = max_area
        if is_litigated is not None and is_litigated != "":
            filters["is_litigated"] = is_litigated
        return filters or None

    @contextmanager
    def _transaction(self) -> Generator[None, None, None]:
        if self.db.in_transaction():
            with self.db.begin_nested():
                yield
        else:
            with self.db.begin():
                yield

    def get_assets(
        self,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
        filters: dict[str, Any] | None = None,
        sort_field: str = "created_at",
        sort_order: str = "desc",
        include_relations: bool = False,
    ) -> tuple[list[Asset], int]:
        """
        获取资产列表，支持分页、搜索和筛选
        """
        result: tuple[list[Asset], int] = asset_crud.get_multi_with_search(
            self.db,
            skip=skip,
            limit=limit,
            search=search,
            filters=filters,
            sort_field=sort_field,
            sort_order=sort_order,
            include_relations=include_relations,
        )
        return result

    def get_asset(self, asset_id: str, *, use_cache: bool = True) -> Asset:
        asset = asset_crud.get(db=self.db, id=asset_id, use_cache=use_cache)
        if not asset:
            raise ResourceNotFoundError("Asset", asset_id)
        return asset

    def get_asset_history(self, asset_id: str) -> list[AssetHistory]:
        self.get_asset(asset_id)
        return history_crud.get_by_asset_id(db=self.db, asset_id=asset_id)

    def get_distinct_field_values(self, field_name: str) -> list[str]:
        values = asset_crud.get_distinct_field_values(self.db, field_name)
        return [str(value) for value in values]

    def create_asset(
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

        with self._transaction():
            validation_service = get_enum_validation_service(self.db)
            is_valid, errors = validation_service.validate_asset_data(
                asset_in.model_dump()
            )
            if not is_valid:
                raise validation_error(
                    f"枚举值验证失败: {'; '.join(errors)}", field_errors=errors
                )

            existing_asset = asset_crud.get_by_name(
                db=self.db, property_name=asset_in.property_name
            )
            if existing_asset:
                raise DuplicateResourceError(
                    "Asset", "property_name", asset_in.property_name
                )

            asset_data = asset_in.model_dump()
            calculated_fields = AssetCalculator.auto_calculate_fields(asset_data)
            final_data = {**asset_data, **calculated_fields}

            area_errors = AssetCalculator.validate_area_consistency(final_data)
            if area_errors:
                raise validation_error(
                    f"数据验证失败: {'; '.join(area_errors)}",
                    field_errors=area_errors,
                )

            calculated_asset_in = AssetCreate(**final_data)
            asset = asset_crud.create_with_history(
                db=self.db,
                obj_in=calculated_asset_in,
                commit=False,
                operator=str(operator) if operator is not None else None,
                ip_address=ip_address,
                user_agent=user_agent,
                session_id=session_id,
            )
            return asset

    def update_asset(
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
            with self._transaction():
                asset = self.get_asset(asset_id, use_cache=False)

                validation_service = get_enum_validation_service(self.db)
                update_data_raw = asset_in.model_dump(exclude_unset=True)
                expected_version = update_data_raw.pop("version", None)
                if (
                    expected_version is not None
                    and hasattr(asset, "version")
                    and asset.version != expected_version
                ):
                    raise conflict(
                        "资产版本冲突，请刷新后重试",
                        resource_type="Asset",
                    )

                is_valid, enum_errors = validation_service.validate_asset_data(
                    update_data_raw
                )
                if not is_valid:
                    raise validation_error(
                        f"枚举值验证失败: {'; '.join(enum_errors)}",
                        field_errors=enum_errors,
                    )

                new_name = update_data_raw.get("property_name")
                if new_name and new_name != asset.property_name:
                    existing_asset = asset_crud.get_by_name(
                        db=self.db, property_name=new_name
                    )
                    if existing_asset and existing_asset.id != asset_id:
                        raise DuplicateResourceError("Asset", "property_name", new_name)

                current_data = {}
                for field in [
                    "rentable_area",
                    "rented_area",
                    "annual_income",
                    "annual_expense",
                ]:
                    if hasattr(asset, field):
                        current_data[field] = getattr(asset, field)

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
                calculated_asset_in = AssetUpdate(**final_update)

                updated = asset_crud.update_with_history(
                    db=self.db,
                    db_obj=asset,
                    obj_in=calculated_asset_in,
                    commit=False,
                    operator=str(operator) if operator is not None else None,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    session_id=session_id,
                )
                return updated
        except StaleDataError as exc:
            raise conflict(
                "资产已被其他人更新，请刷新后重试",
                resource_type="Asset",
            ) from exc

    def delete_asset(self, asset_id: str, current_user: User | None = None) -> None:
        try:
            with self._transaction():
                asset = self.get_asset(asset_id, use_cache=False)
                operator = (
                    getattr(current_user, "username", None)
                    or getattr(current_user, "id", None)
                    or "system"
                )
                history_crud.create(
                    db=self.db,
                    asset_id=asset.id,
                    operation_type="DELETE",
                    description=f"删除资产: {asset.property_name}",
                    operator=str(operator) if operator is not None else None,
                    commit=False,
                )
                asset_crud.remove(db=self.db, id=asset_id, commit=False)
        except StaleDataError as exc:
            raise conflict(
                "资产已被其他人更新，请刷新后重试",
                resource_type="Asset",
            ) from exc


class AsyncAssetService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @asynccontextmanager
    async def _transaction(self) -> Any:
        if self.db.in_transaction():
            async with self.db.begin_nested():
                yield
        else:
            async with self.db.begin():
                yield

    async def get_assets(
        self,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
        filters: dict[str, Any] | None = None,
        sort_field: str = "created_at",
        sort_order: str = "desc",
        include_relations: bool = False,
    ) -> tuple[list[Asset], int]:
        result = await asset_crud.get_multi_with_search_async(
            self.db,
            skip=skip,
            limit=limit,
            search=search,
            filters=filters,
            sort_field=sort_field,
            sort_order=sort_order,
            include_relations=include_relations,
        )
        return result

    async def get_asset(self, asset_id: str, *, use_cache: bool = True) -> Asset:
        asset = await asset_crud.get_async(db=self.db, id=asset_id)
        if not asset:
            raise ResourceNotFoundError("Asset", asset_id)
        return asset

    async def create_asset(
        self,
        asset_in: AssetCreate,
        current_user: User | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        session_id: str | None = None,
    ) -> Asset:
        """
        创建新资产
        包含逻辑: 枚举验证, 名称查重, 自动计算, 面积一致性验证, 历史记录
        """
        operator = (
            getattr(current_user, "username", None)
            or getattr(current_user, "id", None)
            or "system"
        )

        async with self._transaction():
            # 1. 枚举值验证
            validation_service = get_enum_validation_service_async(self.db)
            is_valid, errors = await validation_service.validate_asset_data(
                asset_in.model_dump()
            )
            if not is_valid:
                raise validation_error(
                    f"枚举值验证失败: {'; '.join(errors)}", field_errors=errors
                )

            # 2. 名称查重
            existing_asset = await asset_crud.get_by_name_async(
                db=self.db, property_name=asset_in.property_name
            )
            if existing_asset:
                raise DuplicateResourceError(
                    "Asset", "property_name", asset_in.property_name
                )

            # 3. 自动计算与一致性验证
            asset_data = asset_in.model_dump()
            calculated_fields = AssetCalculator.auto_calculate_fields(asset_data)
            final_data = {**asset_data, **calculated_fields}

            area_errors = AssetCalculator.validate_area_consistency(final_data)
            if area_errors:
                raise validation_error(
                    f"数据验证失败: {'; '.join(area_errors)}",
                    field_errors=area_errors,
                )

            calculated_asset_in = AssetCreate(**final_data)
            asset = await asset_crud.create_with_history_async(
                db=self.db,
                obj_in=calculated_asset_in,
                commit=False,
                operator=str(operator) if operator is not None else None,
                ip_address=ip_address,
                user_agent=user_agent,
                session_id=session_id,
            )
            return asset

    async def update_asset(
        self,
        asset_id: str,
        asset_in: AssetUpdate,
        current_user: User | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        session_id: str | None = None,
    ) -> Asset:
        """
        更新资产
        包含逻辑: 存在性检查枚举验证, 名称查重, 自动计算, 面积一致性验证, 历史记录
        """
        operator = (
            getattr(current_user, "username", None)
            or getattr(current_user, "id", None)
            or "system"
        )

        try:
            async with self._transaction():
                # 1. 存在性检查
                asset = await self.get_asset(asset_id, use_cache=False)

                # 2. 枚举值验证 (如果提供了更新数据)
                validation_service = get_enum_validation_service_async(self.db)
                # only validate fields that are present
                update_data_raw = asset_in.model_dump(exclude_unset=True)
                expected_version = update_data_raw.pop("version", None)
                if (
                    expected_version is not None
                    and hasattr(asset, "version")
                    and asset.version != expected_version
                ):
                    raise conflict(
                        "资产版本冲突，请刷新后重试",
                        resource_type="Asset",
                    )

                is_valid, enum_errors = await validation_service.validate_asset_data(
                    update_data_raw
                )
                if not is_valid:
                    raise validation_error(
                        f"枚举值验证失败: {'; '.join(enum_errors)}",
                        field_errors=enum_errors,
                    )

                # 3. 名称查重 (如果修改了名称)
                new_name = update_data_raw.get("property_name")
                if new_name and new_name != asset.property_name:
                    existing_asset = await asset_crud.get_by_name_async(
                        db=self.db, property_name=new_name
                    )
                    if existing_asset and existing_asset.id != asset_id:
                        raise DuplicateResourceError("Asset", "property_name", new_name)

                # 4. 自动计算与一致性验证
                # 需要合并当前数据和更新数据
                current_data = {}
                # 提取关键计算字段
                for field in [
                    "rentable_area",
                    "rented_area",
                    "annual_income",
                    "annual_expense",
                ]:
                    if hasattr(asset, field):
                        current_data[field] = getattr(asset, field)

                merged_data = {**current_data, **update_data_raw}
                calculated_data = AssetCalculator.auto_calculate_fields(merged_data)

                area_errors = AssetCalculator.validate_area_consistency(calculated_data)
                if area_errors:
                    raise validation_error(
                        f"数据验证失败: {'; '.join(area_errors)}",
                        field_errors=area_errors,
                    )

                # 合并计算字段到更新数据
                final_update = {
                    **update_data_raw,
                    **{
                        k: v
                        for k, v in calculated_data.items()
                        if k not in update_data_raw
                    },
                }
                calculated_asset_in = AssetUpdate(**final_update)

                updated = await asset_crud.update_with_history_async(
                    db=self.db,
                    db_obj=asset,
                    obj_in=calculated_asset_in,
                    commit=False,
                    operator=str(operator) if operator is not None else None,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    session_id=session_id,
                )
                return updated
        except StaleDataError as exc:
            raise conflict(
                "资产已被其他人更新，请刷新后重试",
                resource_type="Asset",
            ) from exc

    async def delete_asset(
        self, asset_id: str, current_user: User | None = None
    ) -> None:
        # 1. 存在性检查
        try:
            async with self._transaction():
                asset = await self.get_asset(asset_id, use_cache=False)
                operator = (
                    getattr(current_user, "username", None)
                    or getattr(current_user, "id", None)
                    or "system"
                )
                history = AssetHistory()
                history.asset_id = asset.id
                history.operation_type = "DELETE"
                history.description = f"删除资产: {asset.property_name}"
                history.operator = str(operator) if operator is not None else None
                self.db.add(history)
                await asset_crud.remove_async(db=self.db, id=asset_id, commit=False)
        except StaleDataError as exc:
            raise conflict(
                "资产已被其他人更新，请刷新后重试",
                resource_type="Asset",
            ) from exc
