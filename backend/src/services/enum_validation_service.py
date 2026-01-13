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

from sqlalchemy import and_, not_
from sqlalchemy.orm import Session

from ..models.enum_field import EnumFieldType, EnumFieldValue

logger = logging.getLogger(__name__)


class EnumValidationService:
    """枚举值动态验证服务"""

    # 缓存有效期（秒）
    CACHE_TTL = 300  # 5分钟

    def __init__(self, db: Session):
        self.db = db
        self._cache: dict[str, list[str]] = {}
        self._cache_timestamps: dict[str, float] = {}

        # 验证统计信息
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
        """检查缓存是否有效"""
        if enum_type_code not in self._cache_timestamps:
            return False
        age = time.time() - self._cache_timestamps[enum_type_code]
        return age < self.CACHE_TTL

    def _update_cache(self, enum_type_code: str, values: list[str]) -> None:
        """更新缓存"""
        self._cache[enum_type_code] = values
        self._cache_timestamps[enum_type_code] = time.time()

    def invalidate_cache(self, enum_type_code: str | None = None) -> None:
        """
        清除缓存

        Args:
            enum_type_code: 指定枚举类型编码，None表示清除所有缓存
        """
        if enum_type_code is None:
            self._cache.clear()
            self._cache_timestamps.clear()
            logger.info("已清除所有枚举缓存")
        else:
            self._cache.pop(enum_type_code, None)
            self._cache_timestamps.pop(enum_type_code, None)
            logger.info(f"已清除枚举类型 '{enum_type_code}' 的缓存")

    def get_valid_values(self, enum_type_code: str) -> list[str]:
        """
        获取指定枚举类型的所有有效值（带缓存）

        Args:
            enum_type_code: 枚举类型编码，如 'ownership_status', 'usage_status'

        Returns:
            有效值列表
        """
        # 检查缓存
        if self._is_cache_valid(enum_type_code):
            logger.debug(f"从缓存获取枚举类型 '{enum_type_code}' 的值")
            return self._cache[enum_type_code]

        try:
            # 查询枚举类型
            enum_type = (
                self.db.query(EnumFieldType)
                .filter(
                    and_(
                        EnumFieldType.code == enum_type_code,
                        not_(EnumFieldType.is_deleted),
                        EnumFieldType.status == "active",
                    )
                )
                .first()
            )

            if not enum_type:
                logger.warning(f"枚举类型 '{enum_type_code}' 未找到或未激活")
                return []

            # 查询该类型下所有启用的枚举值
            values = (
                self.db.query(EnumFieldValue.value)
                .filter(
                    and_(
                        EnumFieldValue.enum_type_id == enum_type.id,
                        not_(EnumFieldValue.is_deleted),
                        EnumFieldValue.is_active,
                    )
                )
                .order_by(EnumFieldValue.sort_order)
                .all()
            )

            result = [v[0] for v in values]

            # 更新缓存
            self._update_cache(enum_type_code, result)

            logger.debug(
                f"从数据库获取枚举类型 '{enum_type_code}' 的值: {len(result)} 个"
            )

            return result

        except Exception as e:
            logger.error(f"获取枚举值失败: {e}")
            return []

    def validate_value(
        self,
        enum_type_code: str,
        value: str,
        allow_empty: bool = True,
        context: dict[str, Any] | None = None,
    ) -> tuple[bool, str | None]:
        """
        验证枚举值是否有效（增强版，带日志记录）

        Args:
            enum_type_code: 枚举类型编码
            value: 待验证的值
            allow_empty: 是否允许空值
            context: 额外的上下文信息（如API端点、用户ID等）

        Returns:
            (是否有效, 错误信息)
        """
        stats = self._validation_stats[enum_type_code]
        stats["total_validations"] += 1

        # 空值处理
        if not value or value.strip() == "":
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

        valid_values = self.get_valid_values(enum_type_code)

        # 枚举值验证：必须配置有效枚举值
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

    def get_validation_stats(
        self, enum_type_code: str | None = None
    ) -> dict[str, Any]:
        """
        获取验证统计信息

        Args:
            enum_type_code: 指定枚举类型编码，None表示获取所有类型的统计

        Returns:
            统计信息字典
        """
        if enum_type_code:
            return dict(self._validation_stats[enum_type_code])
        else:
            return {k: dict(v) for k, v in self._validation_stats.items()}

    def reset_validation_stats(self, enum_type_code: str | None = None) -> None:
        """
        重置验证统计信息

        Args:
            enum_type_code: 指定枚举类型编码，None表示重置所有统计
        """
        if enum_type_code:
            if enum_type_code in self._validation_stats:
                self._validation_stats[enum_type_code] = {
                    "total_validations": 0,
                    "failures": 0,
                    "last_failure_time": None,
                    "last_failure_value": None,
                    "last_failure_context": None,
                }
                logger.info(f"已重置枚举类型 '{enum_type_code}' 的验证统计")
        else:
            self._validation_stats.clear()
            logger.info("已重置所有枚举类型的验证统计")

    def validate_asset_data(self, data: dict[str, Any]) -> tuple[bool, list[str]]:
        """
        验证资产数据中的所有枚举字段

        Args:
            data: 资产数据字典

        Returns:
            (是否全部有效, 错误信息列表)
        """
        errors = []

        # 资产相关的枚举字段映射
        asset_enum_fields = {
            "ownership_status": (
                "ownership_status",
                False,
            ),  # (枚举类型编码, 是否允许空)
            "usage_status": ("usage_status", False),
            "property_nature": ("property_nature", False),
            "business_model": ("business_model", True),
            "operation_status": ("operation_status", True),
            "tenant_type": ("tenant_type", True),
            "data_status": ("data_status", True),
        }

        for field_name, (enum_type_code, allow_empty) in asset_enum_fields.items():
            if field_name in data and data[field_name] is not None:
                is_valid, error = self.validate_value(
                    enum_type_code, str(data[field_name]), allow_empty
                )
                if not is_valid:
                    errors.append(f"{field_name}: {error}")

        return len(errors) == 0, errors


def get_enum_validation_service(db: Session) -> EnumValidationService:
    """获取枚举验证服务实例"""
    return EnumValidationService(db)


# ==================== 便捷函数 ====================


def get_valid_enum_values(db: Session, enum_type_code: str) -> list[str]:
    """
    便捷函数：获取指定枚举类型的所有有效值

    用于前端下拉框选项获取等场景
    """
    service = EnumValidationService(db)
    return service.get_valid_values(enum_type_code)


def validate_enum_value(
    db: Session,
    enum_type_code: str,
    value: str,
    allow_empty: bool = True,
    context: dict[str, Any] | None = None,
) -> tuple[bool, str | None]:
    """
    便捷函数：验证单个枚举值（增强版，支持上下文）

    Args:
        db: 数据库会话
        enum_type_code: 枚举类型编码
        value: 待验证的值
        allow_empty: 是否允许空值
        context: 额外的上下文信息（如API端点、用户ID等）

    Returns:
        (是否有效, 错误信息)
    """
    service = EnumValidationService(db)
    return service.validate_value(enum_type_code, value, allow_empty, context)


def get_enum_validation_stats(
    db: Session, enum_type_code: str | None = None
) -> dict[str, Any]:
    """
    便捷函数：获取验证统计信息

    Args:
        db: 数据库会话
        enum_type_code: 指定枚举类型编码，None表示获取所有统计

    Returns:
        统计信息字典
    """
    service = EnumValidationService(db)
    return service.get_validation_stats(enum_type_code)
