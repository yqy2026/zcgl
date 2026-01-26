"""
统一字典服务层
封装字典相关的所有业务逻辑，API 层只负责路由转发
"""

from typing import Any

from sqlalchemy.orm import Session

from ..core.exception_handler import conflict, not_found
from ..crud.enum_field import get_enum_field_type_crud, get_enum_field_value_crud
from ..models.asset import SystemDictionary
from ..schemas.dictionary import (
    DictionaryOptionResponse,
    DictionaryValueCreate,
    SimpleDictionaryCreate,
)
from ..schemas.enum_field import EnumFieldTypeCreate, EnumFieldValueCreate


class CommonDictionaryService:
    """统一字典服务"""

    def get_combined_options(
        self, db: Session, dict_type: str, is_active: bool | None = True
    ) -> list[DictionaryOptionResponse]:
        """
        获取字典选项（组合逻辑）
        优先从枚举字段获取，兜底使用系统字典（向后兼容）

        Args:
            db: 数据库会话
            dict_type: 字典类型编码
            is_active: 是否只返回启用的选项

        Returns:
            字典选项列表
        """
        # 优先从枚举字段获取
        enum_type_crud = get_enum_field_type_crud(db)
        enum_type = enum_type_crud.get_by_code(dict_type)

        if enum_type:
            # 从枚举字段获取
            enum_value_crud = get_enum_field_value_crud(db)
            enum_type_id_str = str(enum_type.id)
            enum_values = enum_value_crud.get_by_type(
                enum_type_id_str, is_active=is_active if is_active is not None else None
            )

            return [
                DictionaryOptionResponse(
                    label=str(value.label),
                    value=str(value.value),
                    code=str(value.code) if value.code is not None else None,
                    sort_order=int(value.sort_order or 0),
                    color=str(value.color) if value.color is not None else None,
                    icon=str(value.icon) if value.icon is not None else None,
                )
                for value in enum_values
            ]

        # 兜底：从系统字典获取（向后兼容）
        system_dicts_query = db.query(SystemDictionary).filter(
            SystemDictionary.dict_type == dict_type
        )

        if is_active is not None:
            system_dicts_query = system_dicts_query.filter(
                SystemDictionary.is_active == is_active
            )

        system_dicts = system_dicts_query.order_by(
            SystemDictionary.sort_order, SystemDictionary.created_at
        ).all()

        return [
            DictionaryOptionResponse(
                label=item.dict_label,
                value=item.dict_value,
                code=item.dict_code,
                sort_order=item.sort_order,
            )
            for item in system_dicts
        ]

    def quick_create_enum_dictionary(
        self,
        db: Session,
        dict_type: str,
        data: SimpleDictionaryCreate,
        operator: str,
    ) -> dict[str, Any]:
        """
        快速创建枚举字典（封装事务逻辑）

        Args:
            db: 数据库会话
            dict_type: 字典类型编码
            data: 字典创建数据
            operator: 操作人

        Returns:
            创建结果信息

        Raises:
            conflict: 字典类型已存在
        """
        enum_type_crud = get_enum_field_type_crud(db)

        # 检查是否已存在
        existing_type = enum_type_crud.get_by_code(dict_type)
        if existing_type:
            raise conflict(f"字典类型 {dict_type} 已存在", resource_type="dictionary")

        # 创建枚举类型
        enum_type_create = EnumFieldTypeCreate(
            name=dict_type.replace("_", " ").title(),
            code=dict_type,
            category="简单字典",
            description=data.description or f"{dict_type} 字典",
            is_system=False,
            is_hierarchical=False,
            is_multiple=False,
            created_by=operator,
            default_value=None,
            validation_rules=None,
            display_config=None,
        )

        enum_type = enum_type_crud.create(enum_type_create)

        # 批量创建枚举值
        enum_value_crud = get_enum_field_value_crud(db)
        created_values = []
        enum_type_id_str = str(enum_type.id)

        for i, option in enumerate(data.options):
            enum_value_create = EnumFieldValueCreate(
                enum_type_id=enum_type_id_str,
                label=option.label,
                value=option.value,
                code=option.code,
                description=option.description,
                sort_order=option.sort_order if option.sort_order > 0 else i + 1,
                color=option.color,
                icon=option.icon,
                is_active=option.is_active,
                created_by=operator,
                parent_id=None,
                extra_properties=None,
            )

            created_value = enum_value_crud.create(enum_value_create)
            created_values.append(created_value)

        return {
            "message": f"字典 {dict_type} 创建成功",
            "type_id": str(enum_type.id),
            "values_count": len(created_values),
        }

    def add_dictionary_value(
        self,
        db: Session,
        dict_type: str,
        value_data: DictionaryValueCreate,
        operator: str,
    ) -> dict[str, Any]:
        """
        为指定字典类型添加新的选项值

        Args:
            db: 数据库会话
            dict_type: 字典类型编码
            value_data: 值创建数据
            operator: 操作人

        Returns:
            创建结果信息

        Raises:
            not_found: 字典类型不存在
            conflict: 值已存在
        """
        enum_type_crud = get_enum_field_type_crud(db)
        enum_type = enum_type_crud.get_by_code(dict_type)

        if not enum_type:
            raise not_found(f"字典类型 {dict_type} 不存在", resource_type="dictionary")

        enum_value_crud = get_enum_field_value_crud(db)

        # 检查值是否已存在
        enum_type_id_str = str(enum_type.id)
        existing_value = enum_value_crud.get_by_type_and_value(
            enum_type_id_str, value_data.value
        )
        if existing_value:
            raise conflict(
                f"值 {value_data.value} 已存在", resource_type="dictionary_value"
            )

        enum_value_create = EnumFieldValueCreate(
            enum_type_id=enum_type_id_str,
            label=value_data.label,
            value=value_data.value,
            code=value_data.code,
            description=value_data.description,
            sort_order=value_data.sort_order,
            color=value_data.color,
            icon=value_data.icon,
            is_active=value_data.is_active,
            created_by=operator,
            parent_id=None,
            extra_properties=None,
        )

        created_value = enum_value_crud.create(enum_value_create)

        return {"message": "字典值添加成功", "value_id": str(created_value.id)}

    def delete_dictionary_type(
        self, db: Session, dict_type: str, operator: str
    ) -> dict[str, str]:
        """
        删除字典类型及其所有值

        Args:
            db: 数据库会话
            dict_type: 字典类型编码
            operator: 操作人

        Returns:
            删除结果信息

        Raises:
            not_found: 字典类型不存在
        """
        enum_type_crud = get_enum_field_type_crud(db)
        enum_type = enum_type_crud.get_by_code(dict_type)

        if not enum_type:
            raise not_found(f"字典类型 {dict_type} 不存在", resource_type="dictionary")

        # 软删除枚举类型（会级联删除枚举值）
        enum_type_id_str = str(enum_type.id)
        enum_type_crud.delete(enum_type_id_str, deleted_by=operator)

        return {"message": f"字典类型 {dict_type} 删除成功"}


# 单例服务实例
common_dictionary_service = CommonDictionaryService()
