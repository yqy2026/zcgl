from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ...core.exception_handler import DuplicateResourceError, ResourceNotFoundError
from ...crud.asset import asset_crud
from ...models.asset import Asset
from ...models.auth import User
from ...schemas.asset import AssetCreate, AssetUpdate
from ...services.asset.asset_calculator import AssetCalculator
from ...services.enum_validation_service import get_enum_validation_service


class AssetService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_assets(
        self,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
        filters: dict[str, Any] | None = None,
        sort_field: str = "created_at",
        sort_order: str = "desc",
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
        )
        return result

    def get_asset(self, asset_id: str) -> Asset:
        """
        获取单个资产详情
        """
        asset = asset_crud.get(db=self.db, id=asset_id)
        if not asset:
            raise ResourceNotFoundError("Asset", asset_id)
        return asset

    def create_asset(
        self, asset_in: AssetCreate, current_user: User | None = None
    ) -> Asset:
        """
        创建新资产
        包含逻辑: 枚举验证, 名称查重, 自动计算, 面积一致性验证, 历史记录
        """
        # 1. 枚举值验证
        validation_service = get_enum_validation_service(self.db)
        is_valid, errors = validation_service.validate_asset_data(asset_in.model_dump())
        if not is_valid:
            raise HTTPException(
                status_code=422, detail=f"枚举值验证失败: {'; '.join(errors)}"
            )

        # 2. 名称查重
        existing_asset = asset_crud.get_by_name(
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

        errors = AssetCalculator.validate_area_consistency(final_data)
        if errors:
            raise HTTPException(
                status_code=422, detail=f"数据验证失败: {'; '.join(errors)}"
            )

        enhanced_asset_in = AssetCreate(**final_data)

        # 4. 创建并记录历史
        # 注意: create_with_history 内部目前记录 operator="system"
        # 理想情况下应该传递 user_id，但 crud.create_with_history 需要修改以支持 operator 参数
        # 暂时保持现状，后续优化 CRUD
        return asset_crud.create_with_history(db=self.db, obj_in=enhanced_asset_in)

    def update_asset(
        self, asset_id: str, asset_in: AssetUpdate, current_user: User | None = None
    ) -> Asset:
        """
        更新资产
        包含逻辑: 存在性检查枚举验证, 名称查重, 自动计算, 面积一致性验证, 历史记录
        """
        # 1. 存在性检查
        asset = self.get_asset(asset_id)

        # 2. 枚举值验证 (如果提供了更新数据)
        validation_service = get_enum_validation_service(self.db)
        # only validate fields that are present
        update_data_raw = asset_in.model_dump(exclude_unset=True)
        is_valid, errors = validation_service.validate_asset_data(update_data_raw)
        if not is_valid:
            raise HTTPException(
                status_code=422, detail=f"枚举值验证失败: {'; '.join(errors)}"
            )

        # 3. 名称查重 (如果修改了名称)
        if asset_in.property_name and asset_in.property_name != asset.property_name:
            existing_asset = asset_crud.get_by_name(
                db=self.db, property_name=asset_in.property_name
            )
            if existing_asset and existing_asset.id != asset_id:
                raise DuplicateResourceError(
                    "Asset", "property_name", asset_in.property_name
                )

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

        errors = AssetCalculator.validate_area_consistency(calculated_data)
        if errors:
            raise HTTPException(
                status_code=422, detail=f"数据验证失败: {'; '.join(errors)}"
            )

        # 合并计算字段到更新数据
        final_update = {
            **update_data_raw,
            **{k: v for k, v in calculated_data.items() if k not in update_data_raw},
        }
        enhanced_asset_in = AssetUpdate(**final_update)

        # 5. 更新并记录历史
        return asset_crud.update_with_history(
            db=self.db, db_obj=asset, obj_in=enhanced_asset_in
        )

    def delete_asset(self, asset_id: str, current_user: User | None = None) -> None:
        """
        删除资产
        """
        # 1. 存在性检查
        self.get_asset(asset_id)

        # 2. 删除
        asset_crud.remove(db=self.db, id=asset_id)

    def get_distinct_field_values(self, field_name: str) -> list[str]:
        """
        获取指定字段的所有唯一值

        常用于搜索筛选下拉框，如权属方、业态类别等
        """
        return asset_crud.get_distinct_field_values(self.db, field_name)
