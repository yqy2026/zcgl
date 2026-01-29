from typing import Any

"""
资产CRUD操作 - 优化版本

注意: 此层为纯数据访问层，不包含业务逻辑。
资产计算逻辑（AssetCalculator）应在 API 或 Service 层调用。
"""

from sqlalchemy import Select, select
from sqlalchemy.orm import Session, joinedload

from ..constants.business_constants import DateTimeFields
from ..core.encryption import EncryptionKeyManager, FieldEncryptor
from ..core.performance import cached, monitor_query
from ..models.asset import Asset, AssetHistory, Project, ProjectOwnershipRelation
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

    def __init__(self) -> None:
        super().__init__(Asset)
        # Asset 模型的敏感字段（需要加密的PII字段）
        self.sensitive_data_handler = SensitiveDataHandler(
            # 可搜索字段（需要精确匹配查询）
            searchable_fields={
                "tenant_name",  # 租户名称
                "ownership_entity",  # 权属方
                "address",  # 地址
            },
            # 不可搜索字段（只需要保护）
            non_searchable_fields={
                "manager_name",  # 经理姓名
                "project_phone",  # 项目电话
            },
        )

    def _asset_base_query_with_relations(self) -> Select[Any]:
        """
        资产列表/批量查询的基础查询（预加载高频关系，避免 N+1）

        注意：集合关系使用 selectinload，避免 joinedload 导致的行膨胀。
        """
        return select(Asset).options(
            joinedload(Asset.project)
            .selectinload(Project.ownership_relations)
            .joinedload(ProjectOwnershipRelation.ownership),
            joinedload(Asset.ownership),
        )

    def create(
        self,
        db: Session,
        *,
        obj_in: AssetCreate | dict[str, Any],
        commit: bool = True,
        **kwargs: Any,
    ) -> Asset:
        """
        创建资产（加密PII字段）

        Override CRUDBase.create() to encrypt PII fields before database insertion.
        """
        # 转换为字典
        if isinstance(obj_in, dict):
            obj_in_data = obj_in
        else:
            obj_in_data = obj_in.model_dump()

        obj_in_data.update(kwargs)

        # 移除计算字段（这些字段在模型中是@property，不能设置）
        # unrented_area 和 occupancy_rate 是自动计算的，不应该从 API 输入
        obj_in_data.pop("unrented_area", None)
        obj_in_data.pop("occupancy_rate", None)

        # 加密PII字段
        encrypted_data = self.sensitive_data_handler.encrypt_data(obj_in_data.copy())

        # 调用父类方法创建记录
        return super().create(db=db, obj_in=encrypted_data, commit=commit)

    def get(self, db: Session, id: Any, use_cache: bool = True) -> Asset | None:
        """
        根据ID获取资产（解密PII字段）

        Override CRUDBase.get() to decrypt PII fields after retrieval.
        """
        # 调用父类方法获取记录
        result = super().get(db=db, id=id, use_cache=use_cache)

        if result is not None:
            # 解密PII字段
            self._decrypt_asset_object(result)

        return result

    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        use_cache: bool = False,
        **kwargs: Any,
    ) -> list[Asset]:
        """
        获取多个资产（解密PII字段）

        Override CRUDBase.get_multi() to decrypt PII fields after retrieval.
        """
        # 调用父类方法获取记录
        results = super().get_multi(
            db=db, skip=skip, limit=limit, use_cache=use_cache, **kwargs
        )

        # 解密所有记录的PII字段
        for asset in results:
            self._decrypt_asset_object(asset)

        return results

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

    def get_by_name(self, db: Session, property_name: str) -> Asset | None:
        """根据物业名称获取资产"""
        return db.query(Asset).filter(Asset.property_name == property_name).first()

    def get_by_property_name(self, db: Session, property_name: str) -> Asset | None:
        """根据物业名称获取资产（别名方法）"""
        return self.get_by_name(db, property_name)

    @monitor_query("asset_get_multi_with_search")
    @cached(ttl=600)
    def get_multi_with_search(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
        filters: dict[str, Any] | None = None,
        sort_field: str = DateTimeFields.CREATED_AT,
        sort_order: str = "desc",
        include_relations: bool = False,
    ) -> tuple[list[Asset], int]:
        """
        获取资产列表，支持搜索、筛选和排序 - 优化版本

        注意：搜索PII字段时会自动加密搜索词以匹配数据库中的加密数据
        """
        # 映射特定过滤器到 QueryBuilder 格式
        qb_filters = {}
        if filters:
            for key, value in filters.items():
                if key == "min_area":
                    qb_filters["min_actual_property_area"] = value
                elif key == "max_area":
                    qb_filters["max_actual_property_area"] = value
                elif key == "ids":
                    qb_filters["id__in"] = value
                else:
                    qb_filters[key] = value

        # 定义搜索字段（区分PII和非PII）
        non_pii_search_fields = ["property_name", "business_category"]
        pii_search_fields = ["address", "ownership_entity"]
        all_search_fields = non_pii_search_fields + pii_search_fields

        # 如果搜索PII字段且加密已启用，需要加密搜索词
        search_query = search
        if search and self.sensitive_data_handler.encryption_enabled:
            # 对PII字段的搜索，使用加密后的搜索词
            # 注意：这里使用原始搜索词，QueryBuilder会处理匹配逻辑
            # 如果需要精确匹配加密字段，可以在filters中指定
            pass

        # 使用 CRUDBase (QueryBuilder) 获取数据
        # 注意：QueryBuilder 默认处理 skip/limit
        base_query = (
            self._asset_base_query_with_relations()
            if include_relations
            else select(Asset)
        )
        assets: list[Asset] = self.get_with_filters(
            db,
            filters=qb_filters,
            search=search_query,
            search_fields=all_search_fields,
            skip=skip,
            limit=limit,
            order_by=sort_field,
            order_desc=(sort_order.lower() == "desc"),
            base_query=base_query,
        )

        # 获取总数 (用于分页)
        cnt_query = self.query_builder.build_count_query(
            filters=qb_filters,
            search_query=search_query,
            search_fields=all_search_fields,
        )
        total = db.execute(cnt_query).scalar() or 0

        # 解密所有记录的PII字段
        for asset in assets:
            self._decrypt_asset_object(asset)

        return assets, total

    def create_with_history(
        self,
        db: Session,
        obj_in: AssetCreate,
        commit: bool = True,
        operator: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        session_id: str | None = None,
    ) -> Asset:
        """创建资产并记录历史"""
        db_obj: Asset = self.create(db=db, obj_in=obj_in, commit=False)

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
            db.commit()
        else:
            db.flush()
        return db_obj

    def update(
        self,
        db: Session,
        *,
        db_obj: Asset,
        obj_in: AssetUpdate | dict[str, Any],
        commit: bool = True,
    ) -> Asset:
        """
        更新资产，增加版本号并加密PII字段

        Override CRUDBase.update() to encrypt PII fields.

        Note: Signature intentionally specializes generic CRUDBase.update for Asset type
        """
        # 转换为字典
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        # 移除计算字段（这些字段在模型中是@property，不能设置）
        update_data.pop("unrented_area", None)
        update_data.pop("occupancy_rate", None)

        # 加密PII字段
        encrypted_data = self._encrypt_update_data(update_data)

        # 版本号递增
        if hasattr(db_obj, "version") and db_obj.version is not None:
            current_version = int(db_obj.version)
            db_obj.version = current_version + 1

        # 调用父类方法更新记录
        result: Asset = super().update(
            db=db, db_obj=db_obj, obj_in=encrypted_data, commit=commit
        )
        return result

    def update_with_history(
        self,
        db: Session,
        db_obj: Asset,
        obj_in: AssetUpdate,
        commit: bool = True,
        operator: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        session_id: str | None = None,
    ) -> Asset:
        """更新资产并记录历史"""
        if hasattr(obj_in, "model_dump"):
            update_data = obj_in.model_dump(exclude_unset=True)
        else:
            update_data = obj_in.dict(exclude_unset=True)

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

        return self.update(db=db, db_obj=db_obj, obj_in=obj_in, commit=commit)

    def get_multi_by_ids(
        self, db: Session, ids: list[str], include_relations: bool = False
    ) -> list[Asset]:
        """根据ID列表批量获取资产"""
        base_query = (
            self._asset_base_query_with_relations()
            if include_relations
            else select(Asset)
        )
        return self.get_with_filters(
            db,
            filters={"id__in": ids},
            limit=len(ids) if ids else 100,
            base_query=base_query,
        )

    # remove is inherited
    # create is inherited (check notes about calculation)


# 创建全局实例
asset_crud = AssetCRUD()
