"""
枚举值动态验证服务

提供从数据库动态获取枚举值并进行验证的功能，
使枚举字段管理功能能够实际生效于资产等模块的验证。
"""

import logging
import time
from collections import defaultdict
from datetime import datetime
from typing import Any
from weakref import WeakKeyDictionary

from sqlalchemy.ext.asyncio import AsyncSession

from ..constants.message_constants import EMPTY_STRING
from ..crud.enum_field import EnumFieldTypeCRUD, EnumFieldValueCRUD

logger = logging.getLogger(__name__)

_type_crud = EnumFieldTypeCRUD()
_value_crud = EnumFieldValueCRUD()


class AsyncEnumValidationService:
    CACHE_TTL = 300

    def __init__(self, db: AsyncSession):
        self.db = db
        self._cache: dict[str, list[str]] = {}
        self._cache_timestamps: dict[str, float] = {}
        self._validation_stats: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "total_validations": 0,
                "failures": 0,
                "last_failure_time": None,
                "last_failure_value": None,
                "last_failure_context": None,
            }
        )

    def _is_cache_valid(self, enum_type_code: str) -> bool:
        if enum_type_code not in self._cache_timestamps:
            return False
        age = time.time() - self._cache_timestamps[enum_type_code]
        return age < self.CACHE_TTL

    def _update_cache(self, enum_type_code: str, values: list[str]) -> None:
        self._cache[enum_type_code] = values
        self._cache_timestamps[enum_type_code] = time.time()

    async def get_valid_values(self, enum_type_code: str) -> list[str]:
        if self._is_cache_valid(enum_type_code):
            logger.debug(f"从缓存获取枚举类型 '{enum_type_code}' 的值")
            return self._cache[enum_type_code]

        try:
            enum_type = await _type_crud.get_by_code_async(self.db, enum_type_code)

            if not enum_type:
                logger.warning(f"枚举类型 '{enum_type_code}' 未找到或未激活")
                return []

            # get_by_code_async 已过滤 is_deleted，但需额外检查 status
            if getattr(enum_type, "status", None) != "active":
                logger.warning(f"枚举类型 '{enum_type_code}' 未激活")
                return []

            values = await _value_crud.get_all_by_type_async(
                self.db, str(enum_type.id), is_active=True
            )
            result: list[str] = []
            for value_obj in values:
                raw_value = getattr(value_obj, "value", value_obj)
                if raw_value is None:
                    continue
                result.append(str(raw_value))

            self._update_cache(enum_type_code, result)

            logger.debug(
                f"从数据库获取枚举类型 '{enum_type_code}' 的值: {len(result)} 个"
            )

            return result

        except Exception as e:
            logger.error(f"获取枚举值失败: {e}")
            return []

    async def validate_value(
        self,
        enum_type_code: str,
        value: str,
        allow_empty: bool = True,
        context: dict[str, Any] | None = None,
    ) -> tuple[bool, str | None]:
        stats = self._validation_stats[enum_type_code]
        stats["total_validations"] += 1

        if not value or value.strip() == EMPTY_STRING:
            if allow_empty:
                logger.debug(
                    f"枚举字段 '{enum_type_code}' 空值验证通过（allow_empty=True）"
                )
                return True, None
            else:
                logger.warning(
                    f"枚举字段 '{enum_type_code}' 空值验证失败（allow_empty=False）"
                )
                stats["failures"] += 1
                stats["last_failure_time"] = datetime.now()
                stats["last_failure_value"] = ""
                stats["last_failure_context"] = context
                return False, f"字段 {enum_type_code} 不能为空"

        valid_values = await self.get_valid_values(enum_type_code)

        if not valid_values:
            error_msg = f"枚举类型 '{enum_type_code}' 未配置或未激活，请联系管理员"
            logger.error(
                f"枚举验证失败 - 类型: {enum_type_code}, "
                f"错误: 未配置有效值, 上下文: {context}"
            )
            stats["failures"] += 1
            stats["last_failure_time"] = datetime.now()
            stats["last_failure_value"] = value
            stats["last_failure_context"] = context
            return False, error_msg

        if value in valid_values:
            logger.debug(
                f"枚举验证成功 - 类型: {enum_type_code}, 值: {value}, "
                f"允许值数量: {len(valid_values)}"
            )
            return True, None
        else:
            error_msg = (
                f"'{value}' 不是 {enum_type_code} 的有效值，允许值: {valid_values}"
            )
            logger.warning(
                f"枚举验证失败 - 类型: {enum_type_code}, "
                f"无效值: '{value}', "
                f"允许值: {valid_values}, "
                f"上下文: {context}"
            )
            stats["failures"] += 1
            stats["last_failure_time"] = datetime.now()
            stats["last_failure_value"] = value
            stats["last_failure_context"] = context
            return False, error_msg

    async def validate_asset_data(self, data: dict[str, Any]) -> tuple[bool, list[str]]:
        errors = []
        asset_enum_fields = {
            "ownership_status": ("ownership_status", False),
            "usage_status": ("usage_status", False),
            "property_nature": ("property_nature", False),
            "revenue_mode": ("revenue_mode", True),
            "operation_status": ("operation_status", True),
            "tenant_type": ("tenant_type", True),
            "data_status": ("data_status", True),
        }

        for field_name, (enum_type_code, allow_empty) in asset_enum_fields.items():
            if field_name in data and data[field_name] is not None:
                is_valid, error = await self.validate_value(
                    enum_type_code, str(data[field_name]), allow_empty
                )
                if not is_valid:
                    errors.append(f"{field_name}: {error}")

        return len(errors) == 0, errors

    def get_validation_stats(
        self, enum_type_code: str | None = None
    ) -> dict[str, dict[str, Any]]:
        """获取枚举验证统计信息。"""
        if enum_type_code:
            if enum_type_code not in self._validation_stats:
                return {}
            return {enum_type_code: dict(self._validation_stats[enum_type_code])}
        return {
            enum_code: dict(stat)
            for enum_code, stat in self._validation_stats.items()
        }


_ASYNC_SERVICE_CACHE: WeakKeyDictionary[AsyncSession, AsyncEnumValidationService] = (
    WeakKeyDictionary()
)


def get_enum_validation_service_async(
    db: AsyncSession,
) -> AsyncEnumValidationService:
    cached = _ASYNC_SERVICE_CACHE.get(db)
    if cached:
        return cached
    service = AsyncEnumValidationService(db)
    _ASYNC_SERVICE_CACHE[db] = service
    return service

