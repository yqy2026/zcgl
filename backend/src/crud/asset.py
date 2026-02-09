from typing import Any

"""
资产CRUD操作 - 优化版本

注意: 此层为纯数据访问层，不包含业务逻辑。
资产计算逻辑（AssetCalculator）应在 API 或 Service 层调用。
"""

from sqlalchemy import Select, delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from ..constants.business_constants import DateTimeFields
from ..core.encryption import EncryptionKeyManager, FieldEncryptor
from ..core.exception_handler import ResourceNotFoundError
from ..core.search_index import (
    SEARCH_INDEX_FIELDS,
    build_asset_id_subquery,
    build_search_index_entries,
)
from ..models.asset import Asset
from ..models.asset_history import AssetHistory
from ..models.asset_search_index import AssetSearchIndex
from ..models.ownership import Ownership
from ..models.project import Project
from ..models.project_relations import ProjectOwnershipRelation
from ..schemas.asset import AssetCreate, AssetUpdate
from .base import CRUDBase


class SensitiveDataHandler:
    """
    敏感数据处理器 - PII字段加密

    支持两种加密模式：
    - 确定性加密 (AES-256-CBC with derived IV): 用于可搜索字段（手机号等）
    - 标准加密 (AES-256-GCM): 用于非搜索字段

    使用方法：
    # 在子类中定义敏感字段
    class MySensitiveDataHandler(SensitiveDataHandler):
        SEARCHABLE_FIELDS = {"phone", "id_card"}
        NON_SEARCHABLE_FIELDS = {"note"}
    """

    # 默认无敏感字段（子类应覆盖）
    SEARCHABLE_FIELDS: set[str] = set()
    NON_SEARCHABLE_FIELDS: set[str] = set()
    ALL_PII_FIELDS = SEARCHABLE_FIELDS | NON_SEARCHABLE_FIELDS

    def __init__(
        self,
        searchable_fields: set[str] | None = None,
        non_searchable_fields: set[str] | None = None,
    ) -> None:
        """
        初始化敏感数据处理器

        Args:
            searchable_fields: 需要加密且可搜索的字段（如手机号）
            non_searchable_fields: 需要加密但不需要搜索的字段（如备注）
        """
        # 如果提供了参数，使用参数；否则使用类属性
        if searchable_fields is not None:
            self.SEARCHABLE_FIELDS = searchable_fields
        if non_searchable_fields is not None:
            self.NON_SEARCHABLE_FIELDS = non_searchable_fields
        self.ALL_PII_FIELDS = self.SEARCHABLE_FIELDS | self.NON_SEARCHABLE_FIELDS

        key_manager = EncryptionKeyManager()
        self.encryptor = FieldEncryptor(key_manager)
        self.encryption_enabled = key_manager.is_available()

        if not self.encryption_enabled:
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(
                "Encryption disabled: DATA_ENCRYPTION_KEY not set or invalid. "
                "PII data will be stored in plaintext."
            )

    def encrypt_field(self, field_name: str, value: Any) -> Any:
        """
        加密单个字段

        Args:
            field_name: 字段名称
            value: 字段值

        Returns:
            加密后的值，如果不是PII字段或加密失败则返回原值
        """
        if not self.encryption_enabled or value is None:
            return value

        # 使用确定性加密（可搜索）
        if field_name in self.SEARCHABLE_FIELDS:
            encrypted = self.encryptor.encrypt_deterministic(str(value))
            return value if encrypted is None else encrypted

        # 使用标准加密（不可搜索）
        if field_name in self.NON_SEARCHABLE_FIELDS:
            encrypted = self.encryptor.encrypt_standard(str(value))
            return value if encrypted is None else encrypted

        # 非PII字段，返回原值
        return value

    def decrypt_field(self, field_name: str, value: Any) -> Any:
        """
        解密单个字段

        Args:
            field_name: 字段名称
            value: 字段值（可能已加密）

        Returns:
            解密后的值，如果不是加密格式则返回原值
            注意：真正的解密错误（如密钥错误）会返回 None
        """
        if not self.encryption_enabled or value is None:
            return value

        # 使用确定性解密
        if field_name in self.SEARCHABLE_FIELDS:
            return self.encryptor.decrypt_deterministic(str(value))

        # 使用标准解密
        if field_name in self.NON_SEARCHABLE_FIELDS:
            return self.encryptor.decrypt_standard(str(value))

        # 非PII字段，返回原值
        return value

    def encrypt_data(self, data: dict[str, Any] | list[dict[str, Any]]) -> Any:
        """
        批量加密数据中的PII字段

        Args:
            data: 字典或字典列表

        Returns:
            加密后的数据（原地修改）
        """
        if isinstance(data, dict):
            for field_name in self.ALL_PII_FIELDS:
                if field_name in data:
                    data[field_name] = self.encrypt_field(field_name, data[field_name])
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    for field_name in self.ALL_PII_FIELDS:
                        if field_name in item:
                            item[field_name] = self.encrypt_field(
                                field_name, item[field_name]
                            )
        return data

    def decrypt_data(self, data: dict[str, Any] | list[dict[str, Any]]) -> Any:
        """
        批量解密数据中的PII字段

        Args:
            data: 字典或字典列表

        Returns:
            解密后的数据（原地修改）
        """
        if isinstance(data, dict):
            for field_name in self.ALL_PII_FIELDS:
                if field_name in data and data[field_name] is not None:
                    data[field_name] = self.decrypt_field(field_name, data[field_name])
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    for field_name in self.ALL_PII_FIELDS:
                        if field_name in item and item[field_name] is not None:
                            item[field_name] = self.decrypt_field(
                                field_name, item[field_name]
                            )
        return data


class AssetCRUD(CRUDBase[Asset, AssetCreate, AssetUpdate]):
    """资产CRUD操作类 - 优化版本"""

    SORT_FIELD_ALIASES = {
        "occupancy_rate": "cached_occupancy_rate",
    }
    FILTER_FIELD_ALIASES = {
        "min_occupancy_rate": "min_cached_occupancy_rate",
        "max_occupancy_rate": "max_cached_occupancy_rate",
        "occupancy_rate": "cached_occupancy_rate",
    }

    @staticmethod
    def _asset_projection_load_options(
        *,
        include_contract_projection: bool = True,
    ) -> tuple[Any, ...]:
        """资产投影字段所需的关系预加载选项。"""
        options: list[Any] = [joinedload(Asset.ownership)]
        if include_contract_projection:
            options.append(selectinload(Asset.rent_contracts))
        return tuple(options)

    def __init__(self) -> None:
        super().__init__(Asset)
        # Asset 模型的敏感字段（需要加密的PII字段）
        self.sensitive_data_handler = SensitiveDataHandler(
            # 可搜索字段（需要精确匹配查询）
            searchable_fields={
                "address",  # 地址
            },
            # 不可搜索字段（只需要保护）
            non_searchable_fields={
                "manager_name",  # 经理姓名
                "project_phone",  # 项目电话
            },
        )

    async def _refresh_search_index_entries(
        self, db: AsyncSession, *, asset_id: str, data: dict[str, Any]
    ) -> None:
        fields_to_refresh = [
            field_name for field_name in SEARCH_INDEX_FIELDS if field_name in data
        ]
        if not fields_to_refresh:
            return

        await db.execute(
            delete(AssetSearchIndex).where(
                AssetSearchIndex.asset_id == asset_id,
                AssetSearchIndex.field_name.in_(fields_to_refresh),
            )
        )

        key_manager = self.sensitive_data_handler.encryptor.key_manager
        entries = []
        for field_name in fields_to_refresh:
            entries.extend(
                build_search_index_entries(
                    asset_id=asset_id,
                    field_name=field_name,
                    value=data.get(field_name),
                    key_manager=key_manager,
                )
            )

        if not entries:
            return

        await db.execute(
            insert(AssetSearchIndex),
            [
                {
                    "asset_id": entry.asset_id,
                    "field_name": entry.field_name,
                    "token_hash": entry.token_hash,
                    "key_version": entry.key_version,
                }
                for entry in entries
            ],
        )

    def _asset_base_query_with_relations(
        self,
        *,
        include_contract_projection: bool = True,
    ) -> Select[Any]:
        """
        资产列表/批量查询的基础查询（预加载高频关系，避免 N+1）

        注意：集合关系使用 selectinload，避免 joinedload 导致的行膨胀。
        """
        return select(Asset).options(
            joinedload(Asset.project)
            .selectinload(Project.ownership_relations)
            .joinedload(ProjectOwnershipRelation.ownership),
            *self._asset_projection_load_options(
                include_contract_projection=include_contract_projection
            ),
        )

    def _normalize_sort_field(self, sort_field: str) -> str:
        return self.SORT_FIELD_ALIASES.get(sort_field, sort_field)

    def _normalize_filters(self, filters: dict[str, Any] | None) -> dict[str, Any]:
        qb_filters: dict[str, Any] = {}
        if not filters:
            return qb_filters

        for key, value in filters.items():
            normalized_key = self.FILTER_FIELD_ALIASES.get(key, key)
            if normalized_key == "is_litigated" and isinstance(value, str):
                normalized_bool = value.strip().lower()
                if normalized_bool in {"true", "1", "yes", "y", "是"}:
                    value = True
                elif normalized_bool in {"false", "0", "no", "n", "否"}:
                    value = False
            if normalized_key == "min_area":
                qb_filters["min_actual_property_area"] = value
            elif normalized_key == "max_area":
                qb_filters["max_actual_property_area"] = value
            elif normalized_key == "ids":
                qb_filters["id__in"] = value
            else:
                qb_filters[normalized_key] = value

        return qb_filters

    async def create_async(
        self,
        db: AsyncSession,
        *,
        obj_in: AssetCreate | dict[str, Any],
        commit: bool = True,
        **kwargs: Any,
    ) -> Asset:
        if isinstance(obj_in, dict):
            obj_in_data = obj_in
        else:
            obj_in_data = obj_in.model_dump()

        obj_in_data.update(kwargs)
        obj_in_data.pop("unrented_area", None)
        obj_in_data.pop("occupancy_rate", None)
        obj_in_data.pop("version", None)
        obj_in_data.pop("ownership_entity", None)
        obj_in_data.pop("tenant_name", None)
        obj_in_data.pop("lease_contract_number", None)
        obj_in_data.pop("contract_start_date", None)
        obj_in_data.pop("contract_end_date", None)
        obj_in_data.pop("monthly_rent", None)
        obj_in_data.pop("deposit", None)
        obj_in_data.pop("wuyang_project_name", None)
        obj_in_data.pop("description", None)

        encrypted_data = self.sensitive_data_handler.encrypt_data(obj_in_data.copy())
        db_obj = Asset(**encrypted_data)
        db.add(db_obj)
        await db.flush()

        await self._refresh_search_index_entries(
            db, asset_id=db_obj.id, data=obj_in_data
        )

        if commit:
            await db.commit()
        else:
            await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def get_async(
        self, db: AsyncSession, id: Any, use_cache: bool = False
    ) -> Asset | None:
        result = await db.execute(
            select(Asset).options(*self._asset_projection_load_options()).filter(
                getattr(self.model, "id") == id
            )
        )
        asset = result.scalars().first()
        if asset is not None:
            self._decrypt_asset_object(asset)
        return asset

    def _decrypt_asset_object(self, asset: Asset) -> None:
        """
        解密资产对象的PII字段（原地修改）

        Args:
            asset: SQLAlchemy模型对象
        """
        for field_name in self.sensitive_data_handler.ALL_PII_FIELDS:
            if hasattr(asset, field_name):
                value = getattr(asset, field_name)
                if value is not None:
                    decrypted_value = self.sensitive_data_handler.decrypt_field(
                        field_name, value
                    )
                    setattr(asset, field_name, decrypted_value)

    def _encrypt_update_data(self, update_data: dict[str, Any]) -> dict[str, Any]:
        """
        加密更新数据中的PII字段

        Args:
            update_data: 更新数据字典

        Returns:
            加密后的更新数据
        """
        encrypted_data = {}
        for field_name, value in update_data.items():
            if field_name in self.sensitive_data_handler.ALL_PII_FIELDS:
                encrypted_data[field_name] = self.sensitive_data_handler.encrypt_field(
                    field_name, value
                )
            else:
                encrypted_data[field_name] = value
        return encrypted_data

    async def get_by_name_async(
        self, db: AsyncSession, property_name: str
    ) -> Asset | None:
        result = await db.execute(
            select(Asset).options(*self._asset_projection_load_options()).filter(
                Asset.property_name == property_name,
                Asset.data_status != "已删除",
            )
        )
        asset = result.scalars().first()
        if asset is not None:
            self._decrypt_asset_object(asset)
        return asset

    async def get_multi_with_search_async(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
        filters: dict[str, Any] | None = None,
        sort_field: str = DateTimeFields.CREATED_AT,
        sort_order: str = "desc",
        include_relations: bool = True,
        include_contract_projection: bool = True,
    ) -> tuple[list[Asset], int]:
        qb_filters = self._normalize_filters(filters)
        normalized_sort_field = self._normalize_sort_field(sort_field)

        non_pii_search_fields = ["property_name", "business_category"]
        pii_search_fields = ["address"]
        search_conditions: list[Any] | None = None
        if search:
            search_conditions = []
            for field in non_pii_search_fields:
                if self.query_builder.whitelist.can_search(field) and hasattr(
                    Asset, field
                ):
                    search_conditions.append(getattr(Asset, field).ilike(f"%{search}%"))

            for field in pii_search_fields:
                if self.query_builder.whitelist.can_search(field) and hasattr(
                    Asset, field
                ):
                    if self.sensitive_data_handler.encryption_enabled:
                        subquery = build_asset_id_subquery(
                            field_name=field,
                            search_text=search,
                            key_manager=self.sensitive_data_handler.encryptor.key_manager,
                        )
                        if subquery is not None:
                            search_conditions.append(Asset.id.in_(subquery))
                        else:
                            encrypted = self.sensitive_data_handler.encrypt_field(
                                field, search
                            )
                            if encrypted is not None:
                                search_conditions.append(
                                    getattr(Asset, field) == encrypted
                                )
                    else:
                        search_conditions.append(
                            getattr(Asset, field).ilike(f"%{search}%")
                        )

            search_conditions.append(Ownership.name.ilike(f"%{search}%"))

            if not search_conditions:
                search_conditions = None

        base_query = (
            self._asset_base_query_with_relations(
                include_contract_projection=include_contract_projection
            )
            if include_relations
            else select(Asset).options(
                *self._asset_projection_load_options(
                    include_contract_projection=include_contract_projection
                )
            )
        )
        if search_conditions:
            base_query = base_query.join(
                Ownership, Asset.ownership_id == Ownership.id, isouter=True
            )
        query: Select[Any] = self.query_builder.build_query(
            filters=qb_filters,
            search_conditions=search_conditions,
            sort_by=normalized_sort_field,
            sort_desc=(sort_order.lower() == "desc"),
            skip=skip,
            limit=limit,
            base_query=base_query,
        )
        result = await db.execute(query)
        assets = list(result.scalars().all())

        count_base_query: Select[Any] = select(Asset.id)
        if search_conditions:
            count_base_query = count_base_query.join(
                Ownership, Asset.ownership_id == Ownership.id, isouter=True
            )

        cnt_query = self.query_builder.build_count_query(
            filters=qb_filters,
            search_conditions=search_conditions,
            base_query=count_base_query,
            distinct_column=Asset.id,
        )
        total_result = await db.execute(cnt_query)
        total = total_result.scalar() or 0

        for asset in assets:
            self._decrypt_asset_object(asset)

        return assets, total

    async def create_with_history_async(
        self,
        db: AsyncSession,
        obj_in: AssetCreate,
        commit: bool = True,
        operator: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        session_id: str | None = None,
    ) -> Asset:
        obj_in_data = obj_in.model_dump()
        obj_in_data.pop("unrented_area", None)
        obj_in_data.pop("occupancy_rate", None)
        obj_in_data.pop("version", None)
        obj_in_data.pop("tenant_name", None)
        obj_in_data.pop("lease_contract_number", None)
        obj_in_data.pop("contract_start_date", None)
        obj_in_data.pop("contract_end_date", None)
        obj_in_data.pop("monthly_rent", None)
        obj_in_data.pop("deposit", None)
        obj_in_data.pop("wuyang_project_name", None)
        obj_in_data.pop("description", None)
        encrypted_data = self.sensitive_data_handler.encrypt_data(obj_in_data.copy())

        db_obj = Asset(**encrypted_data)
        db.add(db_obj)
        await db.flush()

        await self._refresh_search_index_entries(
            db, asset_id=db_obj.id, data=obj_in_data
        )

        history = AssetHistory()
        history.asset_id = db_obj.id
        history.operation_type = "CREATE"
        history.description = f"创建资产: {db_obj.property_name}"
        history.operator = operator
        history.ip_address = ip_address
        history.user_agent = user_agent
        history.session_id = session_id
        db.add(history)

        if commit:
            await db.commit()
        else:
            await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update_async(
        self,
        db: AsyncSession,
        *,
        db_obj: Asset,
        obj_in: AssetUpdate | dict[str, Any],
        commit: bool = True,
    ) -> Asset:
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        update_data.pop("unrented_area", None)
        update_data.pop("occupancy_rate", None)
        update_data.pop("version", None)
        update_data.pop("ownership_entity", None)
        update_data.pop("tenant_name", None)
        update_data.pop("lease_contract_number", None)
        update_data.pop("contract_start_date", None)
        update_data.pop("contract_end_date", None)
        update_data.pop("monthly_rent", None)
        update_data.pop("deposit", None)
        update_data.pop("wuyang_project_name", None)
        update_data.pop("description", None)

        encrypted_data = self._encrypt_update_data(update_data)
        result: Asset = await super().update(
            db=db, db_obj=db_obj, obj_in=encrypted_data, commit=False
        )

        await self._refresh_search_index_entries(
            db, asset_id=result.id, data=update_data
        )

        if commit:
            await db.commit()
        else:
            await db.flush()
        await db.refresh(result)
        return result

    async def update_with_history_async(
        self,
        db: AsyncSession,
        db_obj: Asset,
        obj_in: AssetUpdate,
        commit: bool = True,
        operator: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        session_id: str | None = None,
    ) -> Asset:
        update_data = obj_in.model_dump(exclude_unset=True)
        update_data.pop("version", None)
        update_data.pop("tenant_name", None)
        update_data.pop("lease_contract_number", None)
        update_data.pop("contract_start_date", None)
        update_data.pop("contract_end_date", None)
        update_data.pop("monthly_rent", None)
        update_data.pop("deposit", None)
        update_data.pop("wuyang_project_name", None)
        update_data.pop("description", None)

        for field, new_value in update_data.items():
            if hasattr(db_obj, field):
                old_value = getattr(db_obj, field)
                if old_value != new_value:
                    history = AssetHistory()
                    history.asset_id = db_obj.id
                    history.operation_type = "UPDATE"
                    history.field_name = field
                    history.old_value = (
                        str(old_value) if old_value is not None else None
                    )
                    history.new_value = (
                        str(new_value) if new_value is not None else None
                    )
                    history.description = (
                        f"更新字段 {field}: {old_value} -> {new_value}"
                    )
                    history.operator = operator
                    history.ip_address = ip_address
                    history.user_agent = user_agent
                    history.session_id = session_id
                    db.add(history)

        update_data.pop("unrented_area", None)
        update_data.pop("occupancy_rate", None)
        encrypted_data = self._encrypt_update_data(update_data)

        for field, value in encrypted_data.items():
            setattr(db_obj, field, value)

        db.add(db_obj)
        await self._refresh_search_index_entries(
            db, asset_id=db_obj.id, data=update_data
        )
        if commit:
            await db.commit()
        else:
            await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def remove_async(
        self, db: AsyncSession, *, id: Any, commit: bool = True
    ) -> Asset:
        obj = await db.get(self.model, id)
        if obj is None:
            raise ResourceNotFoundError(self.model.__name__, str(id))
        await db.delete(obj)
        if commit:
            await db.commit()
        else:
            await db.flush()
        return obj

    async def get_multi_by_ids_async(
        self, db: AsyncSession, ids: list[str], include_relations: bool = False
    ) -> list[Asset]:
        base_query = (
            self._asset_base_query_with_relations()
            if include_relations
            else select(Asset).options(*self._asset_projection_load_options())
        )
        assets = await self.get_with_filters(
            db,
            filters={"id__in": ids},
            limit=len(ids) if ids else 100,
            base_query=base_query,
        )
        for asset in assets:
            self._decrypt_asset_object(asset)
        return assets

    # remove is inherited
    # create is inherited (check notes about calculation)


# 创建全局实例
asset_crud = AssetCRUD()
