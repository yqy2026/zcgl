"""
资产批量操作服务

提供事务管理的批量更新、删除和验证功能
"""

import logging
from typing import Any

from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from ...crud.asset import asset_crud
from ...crud.history import history_crud
from ...schemas.asset import AssetUpdate
from .validators import AssetBatchValidator

logger = logging.getLogger(__name__)


class BatchOperationResult(BaseModel):
    """批量操作结果 - Pydantic模型，带验证器确保数据一致性"""

    success_count: int = Field(default=0, ge=0, description="成功数量")
    failed_count: int = Field(default=0, ge=0, description="失败数量")
    total_count: int = Field(default=0, ge=0, description="总数量")
    errors: list[dict[str, Any]] = Field(
        default_factory=list[Any], description="错误列表"
    )
    updated_ids: list[str] = Field(
        default_factory=list[Any], description="已更新的资产ID"
    )

    model_config = {"frozen": False}

    @model_validator(mode="after")
    def validate_counts(self) -> "BatchOperationResult":
        """验证计数一致性：success + failed 不能超过 total"""
        if self.success_count + self.failed_count > self.total_count:
            raise ValueError(
                f"success_count({self.success_count}) + failed_count({self.failed_count}) "
                f"cannot exceed total_count({self.total_count})"
            )
        return self

    def to_dict(self) -> dict[str, Any]:
        """转换为字典（保持向后兼容）"""
        return {
            "success_count": self.success_count,
            "failed_count": self.failed_count,
            "total_count": self.total_count,
            "errors": self.errors,
            "updated_assets": self.updated_ids,
        }


class AssetBatchService:
    """
    资产批量操作服务

    提供带事务管理的批量更新、删除和验证功能
    """

    def __init__(self, db: Session):
        """
        初始化批量操作服务

        Args:
            db: 数据库会话
        """
        self.db = db
        self.validator = AssetBatchValidator()

    def batch_update(
        self,
        asset_ids: list[str] | None = None,
        updates: dict[str, Any] | None = None,
        update_all: bool = False,
        operator: str = "system",
    ) -> BatchOperationResult:
        """
        批量更新资产

        改进点:
        1. 添加事务管理
        2. 移除静默失败
        3. 详细错误记录
        4. 支持 SAVEPOINT 事务（容错模式）

        Args:
            asset_ids: 资产ID列表
            updates: 更新数据字典
            update_all: 是否更新所有资产
            operator: 操作人

        Returns:
            BatchOperationResult
        """
        # 如果更新所有资产，获取所有资产ID
        if update_all:
            all_assets, _ = asset_crud.get_multi_with_search(
                db=self.db, skip=0, limit=10000
            )
            asset_ids = [asset.id for asset in all_assets]

        if not asset_ids:
            return BatchOperationResult(total_count=0)

        result = BatchOperationResult(total_count=len(asset_ids))

        # 使用 SAVEPOINT 事务管理批量操作
        for asset_id in asset_ids:
            # 创建 SAVEPOINT（嵌套事务）
            savepoint = self.db.begin_nested()
            try:
                # 获取现有资产
                asset = asset_crud.get(db=self.db, id=asset_id)
                if not asset:
                    savepoint.rollback()
                    result.errors.append(
                        {
                            "asset_id": asset_id,
                            "error": "资产不存在",
                            "error_type": "NotFoundError",
                        }
                    )
                    result.failed_count += 1
                    continue

                # 更新资产
                if updates is None:
                    updates = {}
                update_schema = AssetUpdate(**updates)
                asset_crud.update(db=self.db, db_obj=asset, obj_in=update_schema)

                # 记录历史
                history_crud.create(
                    db=self.db,
                    asset_id=asset_id,
                    operation_type="批量更新",
                    description=f"批量更新字段: {', '.join(updates.keys())}",
                    operator=operator,
                )

                # 提交 SAVEPOINT
                savepoint.commit()
                result.success_count += 1
                result.updated_ids.append(asset_id)

            except Exception as e:
                # 回滚 SAVEPOINT（仅影响当前资产）
                savepoint.rollback()
                result.errors.append(
                    {
                        "asset_id": asset_id,
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "field_context": self._extract_field_from_error(str(e)),
                    }
                )
                result.failed_count += 1
                logger.warning(f"资产 {asset_id} 更新失败: {e}")

        # 如果有任何成功，提交整体事务
        if result.success_count > 0:
            self.db.commit()
            logger.info(
                f"批量更新完成: 成功={result.success_count}, 失败={result.failed_count}"
            )
        else:
            # 全部失败，回滚
            self.db.rollback()
            logger.error(f"批量更新全部失败，已回滚: {len(result.errors)} 个错误")

        return result

    def _extract_field_from_error(self, error_msg: str) -> str | None:
        """从错误消息中提取字段名"""
        import re

        # 匹配 Pydantic 验证错误格式
        match = re.search(r"(\w+)\n\s+Field required|(\w+)\n\s+Value error", error_msg)
        if match:
            return match.group(1) or match.group(2)
        return None

    def validate_asset_data(
        self,
        data: dict[str, Any],
        validate_rules: list[str] | None = None,
        enum_validation_service: Any = None,
    ) -> tuple[bool, list[dict[str, str]], list[dict[str, str]], list[str]]:
        """
        验证资产数据

        改进点:
        1. 使用模块化验证器
        2. 枚举验证集成

        Args:
            data: 待验证的资产数据
            validate_rules: 验证规则列表
            enum_validation_service: 枚举验证服务

        Returns:
            (is_valid, errors, warnings, validated_fields) 元组
        """
        # 基础验证
        is_valid, errors, warnings, validated_fields = self.validator.validate_all(
            data, validate_rules
        )

        # 枚举验证（如果提供服务）
        if "ownership_status" in data and enum_validation_service:
            enum_service = enum_validation_service

            # 构建验证上下文
            validation_context = {
                "service": "AssetBatchService",
                "action": "validate_asset_data",
            }

            is_enum_valid, error_msg = enum_service.validate_value(
                "ownership_status",
                data["ownership_status"],
                allow_empty=False,
                context=validation_context,
            )
            if not is_enum_valid:
                errors.append(
                    {
                        "field": "ownership_status",
                        "error": error_msg,
                    }
                )
            else:
                if "ownership_status" not in validated_fields:
                    validated_fields.append("ownership_status")

        is_valid = len(errors) == 0
        return is_valid, errors, warnings, validated_fields

    def batch_delete(
        self,
        asset_ids: list[str],
        operator: str = "system",
    ) -> BatchOperationResult:
        """
        批量删除资产

        改进点:
        1. 添加事务管理
        2. 移除静默失败
        3. 详细错误记录

        Args:
            asset_ids: 资产ID列表
            operator: 操作人

        Returns:
            BatchOperationResult
        """
        if not asset_ids:
            return BatchOperationResult(total_count=0)

        result = BatchOperationResult(total_count=len(asset_ids))

        # 使用事务管理批量操作
        try:
            for asset_id in asset_ids:
                try:
                    asset = asset_crud.get(db=self.db, id=asset_id)
                    if not asset:
                        result.errors.append(
                            {"asset_id": asset_id, "error": "资产不存在"}
                        )
                        result.failed_count += 1
                        continue

                    asset_crud.remove(db=self.db, id=asset_id)
                    result.success_count += 1

                except Exception as e:
                    # 不再静默失败
                    result.errors.append(
                        {
                            "asset_id": asset_id,
                            "error": str(e),
                            "error_type": type(e).__name__,
                        }
                    )
                    result.failed_count += 1
                    # 抛出异常，触发事务回滚
                    raise

            # 提交事务
            self.db.commit()
            logger.info(
                f"批量删除完成: 成功={result.success_count}, 失败={result.failed_count}"
            )
            return result

        except Exception as e:
            # 回滚事务
            self.db.rollback()
            logger.error(f"批量删除失败，已回滚: {str(e)}")
            raise
